# Phase 12: LLM Provider Comparison Report

**Generated**: 2026-05-07T15:05:27.995049
**Scope**: Local demo / portfolio prototype - NOT a production benchmark

## Summary

| Provider | Cases | Success | Avg Confidence | Human Review | Guard Passed | Citation Valid | Safe Fallback |
|----------|-------|---------|----------------|--------------|--------------|----------------|---------------|
| FakeLLMProvider | 25 | 25 | 0.82 | 8 | 17 | 25 | 0 |
| OpenAICompatibleProvider | 25 | 25 | 0.70 | 25 | 1 | 3 | 1 |

## Citation Metrics

| Provider | Avg Cited | Avg Valid Citations | Avg Invalid Citations |
|----------|-----------|---------------------|-----------------------|
| FakeLLMProvider | 2.00 | 2.00 | 0.00| OpenAICompatibleProvider | 25 | 25 | 0.70 | 25 | 1 | 3 | 1 |

## Citation Metrics

| Provider | Avg Cited | Avg Valid Citations | Avg Invalid Citations |
|----------|-----------|---------------------|-----------------------|
| FakeLLMProvider | 2.00 | 2.00 | 0.00
| OpenAICompatibleProvider | 2.00 | 2.00 | 0.00 |

## Methodology

- Fixture set: 25 synthetic cases covering diverse scenarios
- Both providers receive same evidence (mock) and same case parameters
- Comparison focuses on: response quality, confidence, human review triggers
- Citation validation and claim guard applied to all results

## Boundary

This is a **local demo / portfolio prototype**. Results do not constitute:
- Production benchmark
- Comparative evaluation of commercial LLM services
- Guarantee of deployment readiness

## Detailed Results

### p12_001 (ordinary_product_consulting)
- Confidence: 0.82
- Human Review: False
- Has Citations: True
- Guard Passed: True
- Citation Validation: PASS
- Safe Fallback: False

### p12_002 (ordinary_product_consulting)
- Confidence: 0.82
- Human Review: False
- Has Citations: True
- Guard Passed: True
- Citation Validation: PASS
- Safe Fallback: False

### p12_003 (refund)
- Confidence: 0.82
- Human Review: False
- Has Citations: True
- Guard Passed: True
- Citation Validation: PASS
- Safe Fallback: False

### p12_004 (refund)
- Confidence: 0.82
- Human Review: False
- Has Citations: True
- Guard Passed: True
- Citation Validation: PASS
- Safe Fallback: False

### p12_005 (return_exchange)
- Confidence: 0.82
- Human Review: False
- Has Citations: True
- Guard Passed: True
- Citation Validation: PASS
- Safe Fallback: False

