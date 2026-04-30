"""Intent classification rules with Chinese keyword matching."""

from dataclasses import dataclass

from ticketpilot.schema.ticket import IntentClass


@dataclass
class IntentRule:
    """Rule for intent classification."""

    intent: IntentClass
    keywords: list[str]
    strong_indicator: str | None = None  # Keyword that gives high confidence


# Intent classification rules
# Keywords per spec: 8-class intent classification
INTENT_RULES: list[IntentRule] = [
    IntentRule(
        intent=IntentClass.REFUND,
        keywords=["退款", "申请退款", "退款请求"],
    ),
    IntentRule(
        intent=IntentClass.RETURN_EXCHANGE,
        keywords=["退货", "换货", "退换"],
    ),
    IntentRule(
        intent=IntentClass.ACCOUNT_ISSUE,
        keywords=["账号", "账户异常", "登录问题", "冻结"],
    ),
    IntentRule(
        intent=IntentClass.TECHNICAL_ISSUE,
        keywords=["打不开", "系统错误", "bug", "故障", "无法使用"],
    ),
    IntentRule(
        intent=IntentClass.PRODUCT_CONSULTING,
        keywords=["怎么用", "如何使用", "产品参数", "规格"],
    ),
    IntentRule(
        intent=IntentClass.LOGISTICS,
        keywords=["物流", "快递", "发货", "收货", "配送"],
    ),
    IntentRule(
        intent=IntentClass.COMPLAINT,
        keywords=["投诉", "差评", "不满", "态度"],
    ),
    IntentRule(
        intent=IntentClass.OTHER,
        keywords=[],
        strong_indicator="赔偿",
    ),
]
