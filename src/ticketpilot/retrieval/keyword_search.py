"""Keyword search using PostgreSQL FTS and LIKE fallback."""

from typing import Optional

from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.retrieval.traces import KeywordResult

# Strong Chinese business terms that benefit from LIKE search
# These are terms where FTS with simple config may not capture exact matches
BUSINESS_TERMS_LIKE = [
    # 通用客服
    "退款", "投诉", "赔偿", "7天", "3个工作日", "订单号", "违约", "账号异常",
    # 跨境电商
    "关税", "清关", "海关", "保税", "直邮", "跨境", "海淘", "全球购",
    "退货", "换货", "物流", "丢件", "理赔", "签收", "快递",
    "税费", "增值税", "消费税", "限值", "额度",
    "假货", "正品", "质量", "食品安全", "过敏", "过期",
    "保修", "售后", "维修", "质保",
    "12315", "消费者", "维权", "投诉",
    # 账号安全
    "账号", "被盗", "盗号", "密码", "冻结", "异常登录", "异地",
    # 支付
    "支付", "汇率", "扣款", "退款中",
    # 禁运合规
    "禁运", "违禁", "检疫", "备案", "中文标签", "成分",
    # 食品安全
    "食品", "虫子", "过期", "过敏", "医院", "异物", "变质",
    # 通用
    "怎么办", "如何", "可以吗", "需要", "多久", "费用",
]

# Minimum FTS score threshold for considering results good
FTS_MIN_SCORE_THRESHOLD = 0.1


def _extract_search_terms(query: str) -> list[str]:
    """
    Extract search terms from query, handling Chinese and English.

    Args:
        query: Input query string

    Returns:
        List of cleaned search terms
    """
    # For Chinese, we search on characters/words
    # For English, split on whitespace
    terms = query.split()
    cleaned = [t.strip() for t in terms if t.strip()]
    return cleaned


def _check_business_terms(query: str) -> list[str]:
    """
    Check if query contains strong business terms that need LIKE fallback.

    Args:
        query: Input query string

    Returns:
        List of business terms found in query
    """
    found = []
    for term in BUSINESS_TERMS_LIKE:
        if term in query:
            found.append(term)
    return found


def _fts_search(
    query: str,
    top_k: int,
    doc_types: Optional[list[DocType]] = None,
) -> list[KeywordResult]:
    """
    Perform full-text search using PostgreSQL FTS with materialized tsvector.

    Uses pre-computed content_tsv column for faster search.
    Uses ts_rank_cd (cover density) for better scoring on short documents.

    Args:
        query: Search query
        top_k: Maximum number of results
        doc_types: Optional filter by document types

    Returns:
        List of KeywordResult sorted by rank
    """
    # Import using __import__ to bypass package __init__ which may have heavy dependencies
    get_db_connection = __import__(
        "ticketpilot.retrieval.db.connection",
        fromlist=["get_db_connection"]
    ).get_db_connection

    search_terms = _extract_search_terms(query)
    if not search_terms:
        return []

    # Build FTS query using to_tsquery with simple config
    # Each term is joined with OR (|)
    tsquery_parts = " | ".join(term for term in search_terms)
    tsquery = f"to_tsquery('simple', '{tsquery_parts}')"

    # Build doc_types filter if provided
    # NOTE: psycopg3 uses %s placeholders (not $1) in this environment
    doc_types_filter = ""
    params: list = []
    if doc_types:
        placeholders = ", ".join("%s" for _ in doc_types)
        doc_types_filter = f"AND k.doc_type IN ({placeholders})"
        params = [dt.value for dt in doc_types]

    # Use materialized content_tsv column for faster search
    # Use ts_rank_cd (cover density) which is better for short documents
    # Normalization: 32 = divide by (rank * number of unique words in document)
    sql = f"""
        SELECT
            k.id as chunk_id,
            k.doc_id,
            k.doc_type,
            k.content,
            -- BM25-style scoring: ts_rank_cd with normalization
            ts_rank_cd(
                k.content_tsv,
                {tsquery},
                32  -- Normalize by document length
            ) as score,
            ROW_NUMBER() OVER (ORDER BY ts_rank_cd(
                k.content_tsv,
                {tsquery},
                32
            ) DESC, k.id) as rank
        FROM knowledge_chunks k
        WHERE k.content_tsv @@ {tsquery}
        {doc_types_filter}
        ORDER BY score DESC, k.id
        LIMIT ${{param_count}}
    """

    # psycopg 3.x doesn't support placeholders for LIMIT - use literal
    sql = sql.replace("${param_count}", str(top_k))

    results = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for row in cur.fetchall():
                results.append(
                    KeywordResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        doc_type=DocType(row[2]),
                        content=row[3],
                        score=float(row[4]),
                        rank=int(row[5]),
                        search_method="fts",
                        fts_rank=int(row[5]),
                        like_rank=None,
                    )
                )

    return results


def _like_search(
    terms: list[str],
    top_k: int,
    doc_types: Optional[list[DocType]] = None,
) -> list[KeywordResult]:
    """
    Perform LIKE search for business terms.

    Used as fallback/supplement to FTS for strong business terms.

    Args:
        terms: List of search terms (business terms)
        top_k: Maximum number of results
        doc_types: Optional filter by document types

    Returns:
        List of KeywordResult sorted by rank
    """
    # Lazy import to avoid dependency at module load
    from ticketpilot.retrieval.db.connection import get_db_connection

    if not terms:
        return []

    # Build LIKE conditions - each term gets its own placeholder
    # NOTE: psycopg3 uses %s placeholders (not $1) in this environment
    like_conditions = " OR ".join("k.content LIKE %s" for i in range(len(terms)))
    doc_types_filter = ""
    doc_type_params: list = []
    if doc_types:
        placeholders = ", ".join("%s" for _ in doc_types)
        doc_types_filter = f"AND k.doc_type IN ({placeholders})"
        doc_type_params = [dt.value for dt in doc_types]

    # Add LIKE wildcards to terms
    # Each term is used multiple times: WHERE, SELECT score, ORDER BY score
    # So we need to duplicate the params for each occurrence
    like_terms = [f"%{term}%" for term in terms]
    num_occurrences = 3  # WHERE clause, SELECT score, ORDER BY score
    like_term_params = like_terms * num_occurrences

    # Build individual LIKE conditions for scoring
    # Each term's LIKE is repeated num_occurrences times
    score_terms_parts = []
    for i in range(len(terms)):
        score_terms_parts.append(
            "CASE WHEN k.content LIKE %s THEN 1 ELSE 0 END"
        )
    score_terms = " + ".join(score_terms_parts)

    # Combine params: like_term_params (duplicated) + doc_type_params
    params = like_term_params + doc_type_params

    sql = f"""
        SELECT
            k.id as chunk_id,
            k.doc_id,
            k.doc_type,
            k.content,
            ({score_terms}) / NULLIF(length(k.content), 0) as score,
            ROW_NUMBER() OVER (
                ORDER BY ({score_terms}) DESC, k.id
            ) as rank
        FROM knowledge_chunks k
        WHERE {like_conditions}
        {doc_types_filter}
        ORDER BY rank
        LIMIT {top_k}
    """

    results = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for row in cur.fetchall():
                results.append(
                    KeywordResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        doc_type=DocType(row[2]),
                        content=row[3],
                        score=float(row[4]) if row[4] is not None else 0.0,
                        rank=int(row[5]),
                        search_method="like",
                        fts_rank=None,
                        like_rank=int(row[5]),
                    )
                )

    return results


def keyword_search(
    query: str,
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
) -> tuple[list[KeywordResult], str]:
    """
    Keyword search using FTS with LIKE fallback for business terms.

    Algorithm:
    1. Try FTS with simple config
    2. If FTS returns low scores (< FTS_MIN_SCORE_THRESHOLD),
       supplement with LIKE for strong business terms
    3. Merge and deduplicate results

    Args:
        query: Search query string
        top_k: Maximum number of results to return
        doc_types: Optional filter by document types

    Returns:
        Tuple of (list of KeywordResult, search_method used)
    """
    # First try FTS
    fts_results = _fts_search(query, top_k, doc_types)
    search_method = "fts"

    # Check if FTS results are good enough or empty
    fts_good = fts_results and fts_results[0].score >= FTS_MIN_SCORE_THRESHOLD
    if not fts_good:
        # FTS scores are low, check for business terms
        business_terms = _check_business_terms(query)
        if business_terms:
            # Supplement with LIKE search
            like_results = _like_search(business_terms, top_k, doc_types)
            if like_results:
                search_method = "fts+like"
                # Merge results, avoiding duplicates
                seen_ids = {r.chunk_id for r in fts_results}
                for result in like_results:
                    if result.chunk_id not in seen_ids:
                        fts_results.append(result)

                # Re-rank combined results
                for i, result in enumerate(sorted(fts_results, key=lambda x: x.score, reverse=True), 1):
                    result.rank = i

    # Sort by rank and limit
    fts_results.sort(key=lambda x: x.score, reverse=True)
    fts_results = fts_results[:top_k]
    for i, result in enumerate(fts_results, 1):
        result.rank = i

    return fts_results, search_method


def keyword_search_for_testing(
    query: str,
    top_k: int = 10,
    doc_types: Optional[list[DocType]] = None,
) -> list[KeywordResult]:
    """
    Keyword search wrapper for testing (returns results only).

    Args:
        query: Search query string
        top_k: Maximum number of results
        doc_types: Optional filter by document types

    Returns:
        List of KeywordResult
    """
    results, _ = keyword_search(query, top_k, doc_types)
    return results