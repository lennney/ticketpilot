"""Risk assessment rules with Chinese keyword matching."""

from dataclasses import dataclass

from ticketpilot.schema.ticket import RiskFlag


@dataclass
class RiskRule:
    """Rule for risk flag detection."""

    flag: RiskFlag
    keywords: list[str]


# Risk assessment rules
# Keywords per spec: 8-flag risk assessment
RISK_RULES: list[RiskRule] = [
    RiskRule(
        flag=RiskFlag.COMPLAINT_RISK,
        keywords=["投诉", "差评", "曝光", "媒体", "媒体曝光"],
    ),
    RiskRule(
        flag=RiskFlag.COMPENSATION_RISK,
        keywords=["赔偿", "补偿", "3倍", "5倍", "惩罚性", "12315", "消费者协会", "消费者权益", "食品安全", "虫子", "医院", "过敏", "我要", "退款", "要退", "我要退", "了我"],
    ),
    RiskRule(
        flag=RiskFlag.LEGAL_RISK,
        keywords=["律师", "法院", "起诉", "法律"],
    ),
    RiskRule(
        flag=RiskFlag.PRIVACY_RISK,
        keywords=["身份证", "证件号", "实名信息", "手机号", "地址信息", "泄露", "隐私", "个人信息"],
    ),
    RiskRule(
        flag=RiskFlag.ACCOUNT_SECURITY_RISK,
        keywords=["盗号", "盗刷", "异常登录", "冻结"],
    ),
    RiskRule(
        flag=RiskFlag.POLICY_CONFLICT,
        keywords=["违反", "违规", "政策", "条款", "违约"],
    ),
]
