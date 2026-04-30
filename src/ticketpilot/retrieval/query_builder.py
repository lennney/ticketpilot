"""Constructs retrieval queries from ticket state."""

from ticketpilot.schema.ticket import IntentClass, RiskFlag


_INTENT_TERMS: dict[IntentClass, list[str]] = {
    IntentClass.REFUND: ["退款", "退货", "退款政策"],
    IntentClass.RETURN_EXCHANGE: ["退货", "换货", "退换流程"],
    IntentClass.ACCOUNT_ISSUE: ["账号", "登录", "密码", "安全"],
    IntentClass.TECHNICAL_ISSUE: ["技术", "错误", "故障"],
    IntentClass.PRODUCT_CONSULTING: ["产品", "咨询", "规格", "功能"],
    IntentClass.LOGISTICS: ["物流", "配送", "发货"],
    IntentClass.COMPLAINT: ["投诉", "维权", "赔偿", "解决"],
    IntentClass.OTHER: [],
}

_RISK_TERMS: dict[RiskFlag, list[str]] = {
    RiskFlag.COMPENSATION_RISK: ["赔偿", "赔付", "金额"],
    RiskFlag.LEGAL_RISK: ["法律", "法规", "合规", "监管"],
    RiskFlag.PRIVACY_RISK: ["隐私", "数据", "保护", "信息"],
    RiskFlag.ACCOUNT_SECURITY_RISK: ["账号安全", "欺诈", "验证", "冻结"],
    RiskFlag.POLICY_CONFLICT: ["政策", "条款", "规则", "冲突"],
}

_META_FLAGS: set[RiskFlag] = {RiskFlag.LOW_CONFIDENCE, RiskFlag.INSUFFICIENT_EVIDENCE}


def build_retrieval_query(
    normalized_text: str,
    intent: IntentClass,
    risk_flags: set[RiskFlag],
) -> str:
    """Build a Chinese retrieval query from ticket state.

    Combines normalized text with Chinese business terms derived from
    intent classification and active risk flags. Terms are deduplicated
    while preserving order.
    """
    parts: list[str] = []

    text = normalized_text.strip()
    if text:
        parts.append(text)

    intent_terms = _INTENT_TERMS.get(intent, [])
    parts.extend(intent_terms)

    for flag in sorted(risk_flags, key=lambda f: f.value):
        if flag in _META_FLAGS:
            continue
        terms = _RISK_TERMS.get(flag, [])
        parts.extend(terms)

    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            ordered.append(part)

    return " ".join(ordered)
