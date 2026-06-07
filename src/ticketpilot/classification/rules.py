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
        keywords=["退款", "申请退款", "退款请求", "退钱", "退费", "退押金",
                  "保价", "降价", "差价退还"],
    ),
    IntentRule(
        intent=IntentClass.RETURN_EXCHANGE,
        keywords=["退货", "换货", "退换", "退货运费", "退货地址", "七天无理由",
                  "质量问题退", "发错货", "发错颜色", "保修期", "质保", "保修"],
    ),
    IntentRule(
        intent=IntentClass.ACCOUNT_ISSUE,
        keywords=["账号", "账户异常", "登录问题", "冻结", "被盗", "盗号",
                  "异地登录", "密码", "身份验证", "账号安全", "异常登录",
                  "手机号绑定", "绑定手机", "修改手机", "修改绑定",
                  "提现", "余额不足", "盗我的号", "陌生订单",
                  "注册", "注销账号", "解冻"],
    ),
    IntentRule(
        intent=IntentClass.TECHNICAL_ISSUE,
        keywords=["打不开", "系统错误", "bug", "故障", "无法使用", "支付失败",
                  "扣款", "页面崩溃", "加载失败", "闪退", "卡住",
                  "已扣款", "钱已扣", "支付显示失败", "付款失败", "重复扣款",
                  "加载不出来", "未支付", "显示未支付", "验证码",
                  "更新后", "用不了", "收不到验证码", "一直转",
                  "登录不了", "登录不上"],
    ),
    IntentRule(
        intent=IntentClass.PRODUCT_CONSULTING,
        keywords=["怎么用", "如何使用", "产品参数", "规格", "使用方法",
                  "怎么操作", "功能",
                  "有没有货", "有没有红色", "有没有蓝色", "颜色", "尺寸", "推荐"],
    ),
    IntentRule(
        intent=IntentClass.LOGISTICS,
        keywords=["物流", "快递", "发货", "收货", "配送", "包裹",
                  "海关", "清关", "扣关", "关税", "跨境", "直邮", "保税",
                  "签收", "丢件", "理赔", "运费", "物流信息", "快递单号",
                  "只收到", "少发", "少件", "没收到", "没到货",
                  "修改地址", "改地址", "转运", "退回"],
    ),
    IntentRule(
        intent=IntentClass.COMPLAINT,
        keywords=["投诉", "差评", "不满", "态度", "12315",
                  "消费者协会", "媒体曝光", "食品安全", "虫子", "过敏", "医院",
                  "过期", "变质", "异物", "假货", "假冒", "泄露", "骚扰",
                  "隐私", "维权", "举报", "包装破损", "包装损坏", "破了", "坏了", "破损", "损坏",
                  "律师函", "起诉", "法院传票", "法律诉讼", "仲裁", "法务"],
        strong_indicator="12315投诉",
    ),
    IntentRule(
        intent=IntentClass.OTHER,
        keywords=[],
        strong_indicator=None,
    ),
]
