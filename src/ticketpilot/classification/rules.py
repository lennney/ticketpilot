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
# Priority order matters (first-match-wins):
#   REFUND > RETURN_EXCHANGE > ACCOUNT > TECHNICAL > PRODUCT > LOGISTICS > COMPLAINT > OTHER
INTENT_RULES: list[IntentRule] = [
    IntentRule(
        intent=IntentClass.REFUND,
        keywords=["退款", "申请退款", "退款请求", "退钱", "退费", "退押金"],
    ),
    IntentRule(
        intent=IntentClass.RETURN_EXCHANGE,
        keywords=["退货", "换货", "退换", "退货运费", "退货地址", "七天无理由",
                  "质量问题退", "发错货"],
    ),
    IntentRule(
        intent=IntentClass.ACCOUNT_ISSUE,
        keywords=["账号", "账户异常", "登录问题", "冻结", "被盗", "盗号",
                  "异地登录", "密码", "身份验证", "账号安全", "异常登录"],
    ),
    IntentRule(
        intent=IntentClass.TECHNICAL_ISSUE,
        keywords=["打不开", "系统错误", "bug", "故障", "无法使用", "支付失败",
                  "扣款", "页面崩溃", "加载失败", "闪退", "卡住"],
    ),
    IntentRule(
        intent=IntentClass.PRODUCT_CONSULTING,
        keywords=["怎么用", "如何使用", "产品参数", "规格", "使用方法",
                  "保修期", "质保", "怎么操作", "功能"],
    ),
    IntentRule(
        intent=IntentClass.LOGISTICS,
        keywords=["物流", "快递", "发货", "收货", "配送", "包裹",
                  "海关", "清关", "扣关", "关税", "跨境", "直邮", "保税",
                  "签收", "丢件", "理赔", "运费", "物流信息", "快递单号"],
    ),
    IntentRule(
        intent=IntentClass.COMPLAINT,
        keywords=["投诉", "差评", "不满", "态度", "律师", "起诉", "12315",
                  "消费者协会", "媒体曝光", "食品安全", "虫子", "过敏", "医院",
                  "过期", "变质", "异物", "假货", "假冒", "泄露", "骚扰",
                  "隐私", "赔偿", "三倍赔偿", "维权", "举报"],
    ),
    IntentRule(
        intent=IntentClass.OTHER,
        keywords=[],
        strong_indicator=None,
    ),
]
