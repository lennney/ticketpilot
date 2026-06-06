"""RRF调参对比：测试不同k值和keyword/vector权重对Precision的影响。"""
import sys, json, os
sys.path.insert(0, os.path.expanduser("~/ticketpilot/src"))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/ticketpilot/.env"))
load_dotenv(os.path.expanduser("~/ticketpilot/.env.local"), override=True)

from ticketpilot.retrieval.keyword_search import keyword_search
from ticketpilot.retrieval.vector_search import vector_search
from ticketpilot.retrieval.providers import get_embedding_provider
from ticketpilot.retrieval.schema.knowledge import DocType

# ============ Weighted RRF ============
def weighted_rrf(keyword_results, vector_results, k=60, kw_weight=0.3, vec_weight=0.7):
    """加权RRF: keyword权重可调。"""
    all_chunks = {}
    
    for r in keyword_results:
        cid = r.chunk_id
        if cid not in all_chunks:
            all_chunks[cid] = {"kw_rank": None, "vec_rank": None, "content": r.content, "doc_type": r.doc_type}
        all_chunks[cid]["kw_rank"] = r.rank
    
    for r in vector_results:
        cid = r.chunk_id
        if cid not in all_chunks:
            all_chunks[cid] = {"kw_rank": None, "vec_rank": None, "content": r.content, "doc_type": r.doc_type}
        all_chunks[cid]["vec_rank"] = r.rank
    
    scored = []
    for cid, info in all_chunks.items():
        score = 0.0
        if info["kw_rank"] is not None:
            score += kw_weight / (k + info["kw_rank"])
        if info["vec_rank"] is not None:
            score += vec_weight / (k + info["vec_rank"])
        scored.append((cid, score, info))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ============ Test Cases ============
test_cases = [
    {"query": "产品有质量问题，想退款", "expected_keywords": ["质量", "退款", "退换", "退"]},
    {"query": "物流显示已签收但是我没有收到", "expected_keywords": ["签收", "未收到", "丢件", "物流"]},
    {"query": "支付失败但钱被扣了", "expected_keywords": ["支付", "扣款", "重复", "退回"]},
    {"query": "想退款但商家不同意", "expected_keywords": ["退款", "拒绝", "争议", "平台介入"]},
    {"query": "账户被冻结怎么办", "expected_keywords": ["冻结", "账户", "解冻", "申诉"]},
]

provider = get_embedding_provider()

# ============ Configs to test ============
configs = [
    {"name": "Baseline (k=60, 50/50)", "k": 60, "kw_w": 0.5, "vec_w": 0.5},
    {"name": "Vec-heavy (k=60, 30/70)", "k": 60, "kw_w": 0.3, "vec_w": 0.7},
    {"name": "Vec-heavy (k=40, 30/70)", "k": 40, "kw_w": 0.3, "vec_w": 0.7},
    {"name": "Vec-heavy (k=20, 20/80)", "k": 20, "kw_w": 0.2, "vec_w": 0.8},
    {"name": "Vec-only (k=20, 0/100)", "k": 20, "kw_w": 0.0, "vec_w": 1.0},
    {"name": "Vec-only (k=60, 0/100)", "k": 60, "kw_w": 0.0, "vec_w": 1.0},
]

results_by_config = {}

for cfg in configs:
    precisions = []
    print(f"\n{'='*60}")
    print(f"Config: {cfg['name']}")
    print('='*60)
    
    for tc in test_cases:
        query = tc["query"]
        expected = tc["expected_keywords"]
        
        # 获取结果
        kw_results, _ = keyword_search(query=query, top_k=20)
        vec_results, _ = vector_search(
            query_embedding=provider.embed(query),
            top_k=20,
            embedding_provider_name=provider.provider_name,
        )
        
        # 加权RRF
        fused = weighted_rrf(kw_results, vec_results, k=cfg["k"], kw_weight=cfg["kw_w"], vec_weight=cfg["vec_w"])
        
        # 计算top-5 Precision
        top5 = fused[:5]
        hits = 0
        for _, score, info in top5:
            content = info["content"]
            if any(kw in content for kw in expected):
                hits += 1
        precision = hits / 5
        precisions.append(precision)
        
        print(f"  {query[:20]:20s} → P@5={precision:.2f}  top1={'✓' if any(kw in top5[0][2]['content'] for kw in expected) else '✗'}")
    
    avg = sum(precisions) / len(precisions)
    results_by_config[cfg["name"]] = avg
    print(f"  → Average P@5: {avg:.3f}")

# ============ Summary ============
print(f"\n{'='*60}")
print("SUMMARY")
print('='*60)
for name, score in sorted(results_by_config.items(), key=lambda x: x[1], reverse=True):
    bar = "█" * int(score * 40)
    print(f"  {score:.3f} | {bar} | {name}")
