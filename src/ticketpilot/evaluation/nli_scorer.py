"""NLI-based faithfulness and relevancy scorer.

Improves on keyword overlap by using:
- Chinese sentence segmentation (。！？)
- Stop word filtering
- Synonym expansion
- Negation detection (polarity flip)
- Full 0.0-1.0 score range (no artificial floor)
"""

from __future__ import annotations

import re
from typing import Final

# Common Chinese stop words to filter out
_STOP_WORDS: Final[frozenset[str]] = frozenset(
    {
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "他",
        "她",
        "它",
        "们",
        "那",
        "些",
        "吗",
        "吧",
        "呢",
        "啊",
        "哦",
        "嗯",
        "呀",
        "嘛",
        "哈",
        "啦",
        "可以",
        "能",
        "可能",
        "应该",
        "需要",
        "已经",
        "正在",
        "将",
        "把",
        "被",
        "从",
        "对",
        "与",
        "及",
        "或",
        "但",
        "而",
        "如果",
        "因为",
        "所以",
        "虽然",
        "但是",
        "然后",
        "因此",
        "不过",
        "只是",
        "而是",
        "这个",
        "那个",
        "什么",
        "怎么",
        "为什么",
        "哪里",
        "哪个",
        "多少",
        "请",
        "您",
        "您好",
        "谢谢",
        "感谢",
        "请问",
        "关于",
        "中",
        "为",
        "以",
        "于",
        "等",
        "之",
        "其",
        "更",
        "又",
        "再",
        "还",
        "才",
        "只",
        "已",
        "曾",
        "每",
        "各",
        "某",
        "此",
    }
)

# Synonym groups — any word in a group matches any other in the same group
_SYNONYM_GROUPS: Final[list[frozenset[str]]] = [
    frozenset({"退款", "退货", "退钱", "退回", "退还", "返款", "返还"}),
    frozenset({"发货", "寄出", "寄送", "配送", "运送", "发运"}),
    frozenset({"快递", "物流", "包裹", "运单", "快递单"}),
    frozenset({"订单", "购买记录", "交易", "下单"}),
    frozenset({"质量", "品质", "做工", "材质"}),
    frozenset({"破损", "损坏", "坏了", "破了", "碎了", "损伤"}),
    frozenset({"延迟", "晚了", "慢了", "推迟", "延期", "迟了"}),
    frozenset({"投诉", "举报", "申诉", "差评"}),
    frozenset({"赔偿", "补偿", "赔付", "赔款"}),
    frozenset({"客服", "售后", "工作人员", "客服人员"}),
    {"收到", "签收", "取件"},
    frozenset({"换货", "换一个", "更换", "调换"}),
    frozenset({"优惠", "折扣", "打折", "减价", "促销"}),
    frozenset({"地址", "收货地址", "送货地址", "邮寄地址"}),
    frozenset({"付款", "支付", "付钱", "结账", "买单"}),
    frozenset({"取消", "撤销", "撤回", "作废"}),
    frozenset({"确认", "核实", "查验", "验证"}),
    frozenset({"尽快", "立即", "马上", "赶紧", "加急"}),
]

# Build reverse lookup: word → group id
_SYNONYM_MAP: dict[str, int] = {}
for _i, _group in enumerate(_SYNONYM_GROUPS):
    for _word in _group:
        _SYNONYM_MAP[_word] = _i

# Negation words that flip polarity
_NEGATION_WORDS: Final[frozenset[str]] = frozenset(
    {
        "不",
        "没",
        "没有",
        "未",
        "无",
        "非",
        "别",
        "莫",
        "勿",
        "否",
    }
)


def _segment_sentences(text: str) -> list[str]:
    """Split Chinese text into sentences by 。！？ and other punctuation."""
    # Split on sentence-ending punctuation, keep non-empty segments
    parts = re.split(r"[。！？!?\n]+", text)
    return [s.strip() for s in parts if s.strip()]


def _build_tokenizer_dict() -> frozenset[str]:
    """Build dictionary of known multi-character words for longest-match tokenization."""
    words: set[str] = set()
    words |= _STOP_WORDS
    for group in _SYNONYM_GROUPS:
        words |= group
    words |= _NEGATION_WORDS
    # Add common words that appear in the domain
    words |= {"订单", "页面", "按钮", "流程", "服务", "政策", "信息", "申请", "处理"}
    return frozenset(w for w in words if len(w) >= 2)


_TOKENIZER_DICT: Final[frozenset[str]] = _build_tokenizer_dict()


def _tokenize_chinese(text: str) -> list[str]:
    """Tokenize Chinese text using longest-match against known dictionary.

    Falls back to individual characters for unknown sequences.
    """
    tokens: list[str] = []
    i = 0
    while i < len(text):
        # Skip punctuation and whitespace
        if re.match(
            r"[，,、。！？!?\s；;：:（）()\[\]【】\"\"''\"'a-zA-Z0-9]", text[i]
        ):
            i += 1
            continue

        # Try longest match (up to 6 chars)
        best_match = ""
        for length in range(min(6, len(text) - i), 1, -1):
            candidate = text[i : i + length]
            if candidate in _TOKENIZER_DICT:
                best_match = candidate
                break

        if best_match:
            tokens.append(best_match)
            i += len(best_match)
        else:
            # Single character token
            tokens.append(text[i])
            i += 1

    return tokens


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from Chinese text, filtering stop words."""
    tokens = _tokenize_chinese(text)
    return {t for t in tokens if t and t not in _STOP_WORDS}


def _expand_synonyms(words: set[str]) -> set[str]:
    """Expand a word set with synonyms from the synonym dictionary."""
    expanded = set(words)
    for word in words:
        if word in _SYNONYM_MAP:
            group_id = _SYNONYM_MAP[word]
            group = _SYNONYM_GROUPS[group_id]
            expanded |= group
    return expanded


def _detect_negation(text: str) -> bool:
    """Detect if text contains negation that flips meaning."""
    return any(neg in text for neg in _NEGATION_WORDS)


def _count_synonym_group_matches(source_kw: set[str], target_kw: set[str]) -> int:
    """Count how many source keywords have a synonym in the target.

    Returns the number of source words that don't directly match but
    have a synonym group member in the target. Each source word is
    counted at most once (group-level, not word-level).
    """
    count = 0
    for word in source_kw:
        if word in target_kw:
            continue  # Direct match, not a synonym match
        if word in _SYNONYM_MAP:
            group = _SYNONYM_GROUPS[_SYNONYM_MAP[word]]
            if group & target_kw:
                count += 1
    return count


def _faithfulness_overlap(answer_kw: set[str], context_kw: set[str]) -> float:
    """Score what fraction of the answer is grounded in context.

    Denominator = answer keywords (are the answer's claims supported?).
    """
    if not answer_kw:
        return 0.0

    direct = len(answer_kw & context_kw)
    synonym_hits = _count_synonym_group_matches(answer_kw, context_kw)

    weighted = direct + 0.6 * synonym_hits
    return min(weighted / len(answer_kw), 1.0)


def _relevancy_overlap(question_kw: set[str], answer_kw: set[str]) -> float:
    """Score what fraction of the question is addressed by the answer.

    Denominator = question keywords (does the answer address the question?).
    """
    if not question_kw:
        return 0.0

    direct = len(question_kw & answer_kw)
    synonym_hits = _count_synonym_group_matches(question_kw, answer_kw)

    weighted = direct + 0.6 * synonym_hits
    return min(weighted / len(question_kw), 1.0)


class NLIScorer:
    """NLI-based scorer using entailment heuristics.

    No external model dependency — uses sentence decomposition,
    synonym expansion, and negation detection for improved
    faithfulness and relevancy scoring.
    """

    def score_faithfulness(self, answer: str, context: list[str]) -> float:
        """Score how faithful the answer is to the provided context.

        Decomposes the answer into sentences, checks each against context.
        Handles negation: if answer negates what context says, penalizes.

        Returns: 0.0 to 1.0
        """
        if not context or not answer:
            return 0.0

        all_context = " ".join(context)
        context_keywords = _extract_keywords(all_context)
        context_has_negation = _detect_negation(all_context)

        if not context_keywords:
            return 0.0

        # Decompose answer into sentences
        sentences = _segment_sentences(answer)
        if not sentences:
            # Fall back to treating whole answer as one unit
            sentences = [answer]

        sentence_scores = []
        for sentence in sentences:
            sentence_keywords = _extract_keywords(sentence)
            if not sentence_keywords:
                continue

            sentence_has_negation = _detect_negation(sentence)
            base_score = _faithfulness_overlap(sentence_keywords, context_keywords)

            # Negation penalty: if one has negation and the other doesn't,
            # the meaning likely flips — penalize heavily
            if sentence_has_negation != context_has_negation:
                base_score *= 0.3

            sentence_scores.append(base_score)

        if not sentence_scores:
            return 0.0

        # Average across sentences, weighted by coverage
        return sum(sentence_scores) / len(sentence_scores)

    def score_relevancy(self, question: str, answer: str) -> float:
        """Score how relevant the answer is to the question.

        Checks keyword overlap between question and answer,
        with synonym expansion and negation handling.

        Returns: 0.0 to 1.0
        """
        if not question or not answer:
            return 0.0

        question_keywords = _extract_keywords(question)
        answer_keywords = _extract_keywords(answer)

        if not question_keywords:
            return 0.0

        # Decompose answer into sentences for fine-grained matching
        sentences = _segment_sentences(answer)
        if not sentences:
            sentences = [answer]

        best_score = 0.0
        for sentence in sentences:
            sentence_keywords = _extract_keywords(sentence)
            if not sentence_keywords:
                continue

            # Check how well this sentence addresses the question
            overlap = _relevancy_overlap(question_keywords, sentence_keywords)

            # Negation check
            q_neg = _detect_negation(question)
            s_neg = _detect_negation(sentence)
            if q_neg != s_neg:
                overlap *= 0.5  # Less severe penalty for relevancy

            best_score = max(best_score, overlap)

        # Also check full answer for overall coverage
        full_score = _relevancy_overlap(question_keywords, answer_keywords)

        return max(best_score, full_score)
