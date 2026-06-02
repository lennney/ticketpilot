"""
Agent guardrails for safety and quality control.

Provides:
- PII detection (personally identifiable information)
- Hallucination detection
- Confidence thresholding
- Input/output validation
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    passed: bool
    check_name: str
    message: str
    severity: str = "info"  # info, warning, error
    metadata: dict[str, Any] | None = None


class PII:
    """PII detection patterns."""
    
    # Chinese phone numbers
    PHONE_PATTERNS = [
        r'1[3-9]\d{9}',  # Mobile
        r'0\d{2,3}-\d{7,8}',  # Landline
    ]
    
    # Chinese ID numbers
    ID_PATTERNS = [
        r'\d{17}[\dXx]',  # 18-digit ID
        r'\d{15}',  # 15-digit ID (old)
    ]
    
    # Email addresses
    EMAIL_PATTERNS = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ]
    
    # Bank card numbers
    BANK_CARD_PATTERNS = [
        r'\d{16,19}',  # 16-19 digit card number
    ]
    
    @classmethod
    def detect(cls, text: str) -> list[dict[str, Any]]:
        """
        Detect PII in text.
        
        Returns list of detected PII with type and position.
        """
        findings = []
        
        for pattern in cls.PHONE_PATTERNS:
            for match in re.finditer(pattern, text):
                findings.append({
                    "type": "phone",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })
        
        for pattern in cls.ID_PATTERNS:
            for match in re.finditer(pattern, text):
                # Validate ID number (basic check)
                value = match.group()
                if len(value) == 18 and cls._validate_id(value):
                    findings.append({
                        "type": "id_number",
                        "value": value,
                        "start": match.start(),
                        "end": match.end(),
                    })
        
        for pattern in cls.EMAIL_PATTERNS:
            for match in re.finditer(pattern, text):
                findings.append({
                    "type": "email",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })
        
        return findings
    
    @classmethod
    def _validate_id(cls, id_number: str) -> bool:
        """Basic ID number validation."""
        if len(id_number) != 18:
            return False
        
        # Check if all digits are valid
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = '10X98765432'
        
        try:
            total = sum(int(id_number[i]) * weights[i] for i in range(17))
            expected = check_codes[total % 11]
            return id_number[-1].upper() == expected
        except (ValueError, IndexError):
            return False


class HallucinationDetector:
    """Detect potential hallucinations in agent output."""
    
    # Common hallucination patterns
    HALLUCINATION_PATTERNS = [
        r'根据.*法律.*规定',  # Legal claims
        r'根据.*政策.*规定',  # Policy claims
        r'平台.*承诺',  # Platform promises
        r'保证.*解决',  # Guarantees
        r'一定.*会',  # Certainty claims
    ]
    
    # Safe hedging phrases
    HEDGING_PHRASES = [
        '建议', '可能', '通常', '一般', '请', '可以',
        '如有疑问', '具体情况', '以实际为准', '请联系',
    ]
    
    @classmethod
    def detect(cls, output: str, context: str | None = None) -> list[dict[str, Any]]:
        """
        Detect potential hallucinations.
        
        Args:
            output: Agent output text
            context: Optional context to verify against
        
        Returns list of potential hallucination issues.
        """
        issues = []
        
        # Check for strong claims without hedging
        for pattern in cls.HALLUCINATION_PATTERNS:
            if re.search(pattern, output):
                # Check if there's hedging nearby
                has_hedging = any(phrase in output for phrase in cls.HEDGING_PHRASES)
                if not has_hedging:
                    issues.append({
                        "type": "strong_claim",
                        "pattern": pattern,
                        "message": f"检测到强声明但缺少限定词: {pattern}",
                        "severity": "warning",
                    })
        
        # Check for specific numbers without context
        number_patterns = [
            r'\d+个工作日',  # X working days
            r'\d+小时内',  # X hours
            r'\d+天内',  # X days
            r'赔偿\d+倍',  # X times compensation
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, output):
                if context and not re.search(pattern, context):
                    issues.append({
                        "type": "unsupported_number",
                        "pattern": pattern,
                        "message": f"检测到具体数字但上下文中未找到: {pattern}",
                        "severity": "warning",
                    })
        
        return issues


class ConfidenceGuard:
    """Confidence-based guardrail."""
    
    # Thresholds
    HIGH_CONFIDENCE = 0.8
    MEDIUM_CONFIDENCE = 0.6
    LOW_CONFIDENCE = 0.4
    
    @classmethod
    def check(cls, confidence: float) -> GuardrailResult:
        """
        Check confidence level and return appropriate action.
        
        Args:
            confidence: Confidence score (0.0 to 1.0)
        
        Returns:
            GuardrailResult with action recommendation
        """
        if confidence >= cls.HIGH_CONFIDENCE:
            return GuardrailResult(
                passed=True,
                check_name="confidence",
                message=f"高置信度 ({confidence:.2f}): 可自主响应",
                severity="info",
                metadata={"action": "autonomous", "threshold": cls.HIGH_CONFIDENCE},
            )
        elif confidence >= cls.MEDIUM_CONFIDENCE:
            return GuardrailResult(
                passed=True,
                check_name="confidence",
                message=f"中置信度 ({confidence:.2f}): 建议人工审核",
                severity="warning",
                metadata={"action": "suggest_review", "threshold": cls.MEDIUM_CONFIDENCE},
            )
        else:
            return GuardrailResult(
                passed=False,
                check_name="confidence",
                message=f"低置信度 ({confidence:.2f}): 需要人工审核",
                severity="error",
                metadata={"action": "human_review", "threshold": cls.LOW_CONFIDENCE},
            )


class InputValidator:
    """Validate input before processing."""
    
    # Blocked patterns (injection attempts)
    BLOCKED_PATTERNS = [
        r'忽略.*之前.*指令',  # Ignore previous instructions
        r'ignore.*previous.*instructions',
        r'system.*prompt',  # System prompt references
        r'你是.*AI',  # Identity probing
    ]
    
    @classmethod
    def validate(cls, input_text: str) -> GuardrailResult:
        """
        Validate input text.
        
        Args:
            input_text: User input text
        
        Returns:
            GuardrailResult indicating if input is safe
        """
        # Check for injection attempts
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, input_text, re.IGNORECASE):
                return GuardrailResult(
                    passed=False,
                    check_name="input_validation",
                    message=f"检测到潜在的注入尝试: {pattern}",
                    severity="error",
                    metadata={"pattern": pattern},
                )
        
        # Check input length
        if len(input_text) > 10000:
            return GuardrailResult(
                passed=False,
                check_name="input_validation",
                message="输入过长 (>10000 字符)",
                severity="warning",
            )
        
        return GuardrailResult(
            passed=True,
            check_name="input_validation",
            message="输入验证通过",
            severity="info",
        )


def run_guardrails(
    input_text: str,
    output_text: str,
    confidence: float,
    context: str | None = None,
) -> list[GuardrailResult]:
    """
    Run all guardrails on input/output.
    
    Args:
        input_text: User input
        output_text: Agent output
        confidence: Confidence score
        context: Optional context for verification
    
    Returns:
        List of guardrail results
    """
    results = []
    
    # 1. Input validation
    results.append(InputValidator.validate(input_text))
    
    # 2. PII detection in output
    pii_findings = PII.detect(output_text)
    if pii_findings:
        results.append(GuardrailResult(
            passed=False,
            check_name="pii_detection",
            message=f"检测到 {len(pii_findings)} 个 PII 信息",
            severity="error",
            metadata={"findings": pii_findings},
        ))
    else:
        results.append(GuardrailResult(
            passed=True,
            check_name="pii_detection",
            message="未检测到 PII 信息",
            severity="info",
        ))
    
    # 3. Hallucination detection
    hallucination_issues = HallucinationDetector.detect(output_text, context)
    if hallucination_issues:
        results.append(GuardrailResult(
            passed=False,
            check_name="hallucination",
            message=f"检测到 {len(hallucination_issues)} 个潜在幻觉问题",
            severity="warning",
            metadata={"issues": hallucination_issues},
        ))
    else:
        results.append(GuardrailResult(
            passed=True,
            check_name="hallucination",
            message="未检测到幻觉问题",
            severity="info",
        ))
    
    # 4. Confidence check
    results.append(ConfidenceGuard.check(confidence))
    
    return results
