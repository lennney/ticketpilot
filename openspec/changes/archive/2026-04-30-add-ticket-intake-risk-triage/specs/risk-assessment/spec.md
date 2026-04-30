## ADDED Requirements

### Requirement: 8-flag risk assessment
The system SHALL assess risk using exactly these 8 flags: complaint_risk, compensation_risk, legal_risk, privacy_risk, account_security_risk, policy_conflict, insufficient_evidence, low_confidence.

#### Scenario: Flag complaint_risk
- **WHEN** ticket text contains "投诉", "差评", "曝光", "媒体"
- **THEN** RiskAssessment.flags contains "complaint_risk"

#### Scenario: Flag compensation_risk
- **WHEN** ticket text contains "赔偿", "补偿", "3倍", "5倍", "惩罚性"
- **THEN** RiskAssessment.flags contains "compensation_risk"

#### Scenario: Flag legal_risk
- **WHEN** ticket text contains "律师", "法院", "起诉", "法律"
- **THEN** RiskAssessment.flags contains "legal_risk"

#### Scenario: Flag privacy_risk
- **WHEN** ticket text contains "泄露", "隐私", "个人信息"
- **THEN** RiskAssessment.flags contains "privacy_risk"

#### Scenario: Flag account_security_risk
- **WHEN** ticket text contains "盗号", "盗刷", "异常登录", "冻结"
- **THEN** RiskAssessment.flags contains "account_security_risk"

#### Scenario: Flag policy_conflict
- **WHEN** ticket text contains "违反", "违规", "政策", "条款"
- **THEN** RiskAssessment.flags contains "policy_conflict"

#### Scenario: Flag insufficient_evidence
- **WHEN** ticket has no order number, no product info, or vague description
- **THEN** RiskAssessment.flags contains "insufficient_evidence"

#### Scenario: Flag low_confidence
- **WHEN** ClassificationResult.confidence < 0.6
- **THEN** RiskAssessment.flags contains "low_confidence"

### Requirement: Risk severity calculation
The system SHALL calculate overall risk severity as sum of flag weights.

#### Scenario: High severity with multiple risk flags
- **WHEN** ticket triggers 3 or more risk flags
- **THEN** RiskAssessment.severity is "high"

#### Scenario: Medium severity with 2 risk flags
- **WHEN** ticket triggers exactly 2 risk flags
- **THEN** RiskAssessment.severity is "medium"

#### Scenario: Low severity with 0-1 risk flags
- **WHEN** ticket triggers 0 or 1 risk flags
- **THEN** RiskAssessment.severity is "low"
