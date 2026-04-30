# intent-classification Specification

## Purpose
TBD - created by archiving change add-ticket-intake-risk-triage. Update Purpose after archive.
## Requirements
### Requirement: 8-class intent classification
The system SHALL classify ticket intent into exactly one of 8 classes: refund, return_exchange, account_issue, technical_issue, product_consulting, logistics, complaint, other.

#### Scenario: Classify refund intent
- **WHEN** ticket text contains "退款", "申请退款", "退款请求"
- **THEN** ClassificationResult.intent is "refund"

#### Scenario: Classify return_exchange intent
- **WHEN** ticket text contains "退货", "换货", "退换"
- **THEN** ClassificationResult.intent is "return_exchange"

#### Scenario: Classify account_issue intent
- **WHEN** ticket text contains "账号", "账户异常", "登录问题", "冻结"
- **THEN** ClassificationResult.intent is "account_issue"

#### Scenario: Classify technical_issue intent
- **WHEN** ticket text contains "打不开", "系统错误", "bug", "故障", "无法使用"
- **THEN** ClassificationResult.intent is "technical_issue"

#### Scenario: Classify product_consulting intent
- **WHEN** ticket text contains "怎么用", "如何使用", "产品参数", "规格"
- **THEN** ClassificationResult.intent is "product_consulting"

#### Scenario: Classify logistics intent
- **WHEN** ticket text contains "物流", "快递", "发货", "收货", "配送"
- **THEN** ClassificationResult.intent is "logistics"

#### Scenario: Classify complaint intent
- **WHEN** ticket text contains "投诉", "差评", "不满", "态度"
- **THEN** ClassificationResult.intent is "complaint"

#### Scenario: Classify other intent
- **WHEN** ticket text does not match any other category keywords
- **THEN** ClassificationResult.intent is "other"

### Requirement: Classification confidence score
The system SHALL provide a confidence score between 0.0 and 1.0 indicating classification certainty.

#### Scenario: High confidence on clear keyword match
- **WHEN** ticket text contains strong keyword match for a category
- **THEN** ClassificationResult.confidence >= 0.8

#### Scenario: Lower confidence on ambiguous text
- **WHEN** ticket text contains weak or multiple category signals
- **THEN** ClassificationResult.confidence < 0.8

