#!/usr/bin/env python
"""Phase 10.7 — Full-Dataset Doc-Level Golden Label Expansion.

Labels remaining 87 eval cases with expected_relevant_doc_ids using
high-confidence-first strategy. Cases that cannot be reliably labeled
are flagged for manual review.

Usage:
    uv run python scripts/label_full_doc_level.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GOLDEN_PATH = Path("data/eval/golden_expectations.csv")
LABEL_PLAN_PATH = Path("reports/retrieval/phase10_full_doc_level_label_plan.md")
MANUAL_REVIEW_PATH = Path("reports/retrieval/phase10_full_doc_level_manual_review.md")

# ---------------------------------------------------------------------------
# High-confidence label map: case_id -> [doc_id, ...]
# Each doc_id must exist in knowledge seed and be business-justified.
# ---------------------------------------------------------------------------

HIGH_CONFIDENCE_LABELS: dict[str, list[str]] = {
    # === REFUND CASES ===
    "case_refu_002": [
        "11111111-1111-1111-1111-111111111111",  # FAQ: 如何申请退款
        "22222222-2222-2222-2222-222222222222",  # FAQ: 退款多久到账
        "a1111111-1111-1111-1111-111111111111",  # POLICY: 退款政策总则
        "ad0d0d0d-2222-2222-2222-222222222222",  # POLICY: 退款到账时效规定
    ],
    "case_refu_003": [
        "dddddddd-2222-2222-2222-222222222222",  # FAQ: 超过七天还能退款吗
        "ae0e0e0e-2222-2222-2222-222222222222",  # POLICY: 超出售后期限例外处理规则
        "a3333333-3333-3333-3333-333333333333",  # POLICY: 退换货基本规则
    ],
    "case_refu_004": [
        "ffffffff-3333-3333-3333-333333333333",  # FAQ: 想退其中几件商品可以吗
        "11111111-1111-1111-1111-111111111111",  # FAQ: 如何申请退款
        "a1111111-1111-1111-1111-111111111111",  # POLICY: 退款政策总则
    ],
    "case_refu_005": [
        "22222222-2222-2222-2222-222222222222",  # FAQ: 退款多久到账
        "dddddddd-1111-1111-1111-111111111111",  # FAQ: 退款进度如何查询
        "ad0d0d0d-2222-2222-2222-222222222222",  # POLICY: 退款到账时效规定
        "ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 退款超时投诉升级处理规则
    ],
    "case_refu_007": [
        "ffffffff-2222-2222-2222-222222222222",  # FAQ: 未发货的订单如何取消退款
        "11111111-1111-1111-1111-111111111111",  # FAQ: 如何申请退款
        "a1111111-1111-1111-1111-111111111111",  # POLICY: 退款政策总则
    ],
    "case_refu_008": [
        "cccccccc-cccc-cccc-cccc-cccccccccccc",  # FAQ: 无理由退货政策是什么
        "ae0e0e0e-4444-4444-4444-444444444444",  # POLICY: 发错货处理规则
        "a3333333-3333-3333-3333-333333333333",  # POLICY: 退换货基本规则
    ],
    "case_refu_010": [
        "cccccccc-cccc-cccc-cccc-cccccccccccc",  # FAQ: 无理由退货政策是什么
        "a3333333-3333-3333-3333-333333333333",  # POLICY: 退换货基本规则
        "ae0e0e0e-2222-2222-2222-222222222222",  # POLICY: 超出售后期限例外处理规则
    ],
    "case_refu_011": [
        "11111111-1111-1111-1111-111111111111",  # FAQ: 如何申请退款
        "a1111111-1111-1111-1111-111111111111",  # POLICY: 退款政策总则
        "accccccc-cccc-cccc-cccc-cccccccccccc",  # POLICY: 特殊商品退款规则
    ],
    "case_refu_012": [
        "dddddddd-1111-1111-1111-111111111111",  # FAQ: 退款进度如何查询
        "eeeeeeee-8888-8888-8888-888888888888",  # FAQ: 退款被驳回怎么办
        "ae0e0e0e-3333-3333-3333-333333333333",  # POLICY: 证据不足处理规则
        "a1111111-1111-1111-1111-111111111111",  # POLICY: 退款政策总则
        "ca0a0a0a-1111-1111-1111-111111111111",  # CASE: 证据不足案例
    ],
    "case_refu_014": [
        "ffffffff-3333-3333-3333-333333333333",  # FAQ: 想退其中几件商品可以吗
        "a1111111-1111-1111-1111-111111111111",  # POLICY: 退款政策总则
    ],
    "case_refu_015": [
        "22222222-2222-2222-2222-222222222222",  # FAQ: 退款多久到账
        "dddddddd-1111-1111-1111-111111111111",  # FAQ: 退款进度如何查询
        "ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 退款超时投诉升级处理规则
        "ad0d0d0d-2222-2222-2222-222222222222",  # POLICY: 退款到账时效规定
        "c3333333-3333-3333-3333-333333333333",  # CASE: 12315投诉案例
    ],
    "case_refu_016": [
        "ae0e0e0e-9999-9999-9999-999999999999",  # POLICY: 商品价格保护规则
        "ca0a0a0a-2222-2222-2222-222222222222",  # CASE: 退差价案例
        "ffffffff-9999-9999-9999-999999999999",  # FAQ: 优惠券支付的订单退款如何计算
    ],

    # === RETURN/EXCHANGE CASES ===
    "case_retu_001": [
        "33333333-3333-3333-3333-333333333333",  # FAQ: 如何申请换货
        "dddddddd-4444-4444-4444-444444444444",  # FAQ: 换货需要哪些条件
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
    ],
    "case_retu_002": [
        "33333333-3333-3333-3333-333333333333",  # FAQ: 如何申请换货
        "a3333333-3333-3333-3333-333333333333",  # POLICY: 退换货基本规则
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
    ],
    "case_retu_003": [
        "dddddddd-4444-4444-4444-444444444444",  # FAQ: 换货需要哪些条件
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
        "b3333333-3333-3333-3333-333333333333",  # CASE: 换货案例
    ],
    "case_retu_005": [
        "cccccccc-cccc-cccc-cccc-cccccccccccc",  # FAQ: 无理由退货政策是什么
        "a3333333-3333-3333-3333-333333333333",  # POLICY: 退换货基本规则
        "bcccccc1-cccc-cccc-cccc-cccccccccccc",  # CASE: 隐蔽瑕疵退货
    ],
    "case_retu_006": [
        "ffffffff-5555-5555-5555-555555555555",  # FAQ: 换货后商品仍有问题怎么办
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
        "bcccccc1-cccc-cccc-cccc-cccccccccccc",  # CASE: 隐蔽瑕疵退货
    ],
    "case_retu_007": [
        "33333333-3333-3333-3333-333333333333",  # FAQ: 如何申请换货
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
    ],
    "case_retu_008": [
        "dddddddd-3333-3333-3333-333333333333",  # FAQ: 退货的运费谁承担
        "ae0e0e0e-4444-4444-4444-444444444444",  # POLICY: 发错货处理规则
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
    ],
    "case_retu_009": [
        "ffffffff-3333-3333-3333-333333333333",  # FAQ: 想退其中几件商品可以吗
        "33333333-3333-3333-3333-333333333333",  # FAQ: 如何申请换货
        "a4444444-4444-4444-4444-444444444444",  # POLICY: 换货服务条款
    ],
    "case_retu_010": [
        "cccccccc-cccc-cccc-cccc-cccccccccccc",  # FAQ: 无理由退货政策是什么
        "a3333333-3333-3333-3333-333333333333",  # POLICY: 退换货基本规则
        "ad0d0d0d-1111-1111-1111-111111111111",  # POLICY: 已拆封商品退换限制规则
    ],
    "case_retu_011": [
        "eeeeeeee-6666-6666-6666-666666666666",  # FAQ: 投诉处理需要多久
        "a9999999-9999-9999-9999-999999999999",  # POLICY: 客户投诉处理流程
        "b3333333-3333-3333-3333-333333333333",  # CASE: 换货案例
    ],

    # === ACCOUNT CASES ===
    "case_acco_001": [
        "44444444-4444-4444-4444-444444444444",  # FAQ: 账户被盗怎么办
        "a5555555-5555-5555-5555-555555555555",  # POLICY: 账户安全保护政策
        "b4444444-4444-4444-4444-444444444444",  # CASE: 账户被盗案例
    ],
    "case_acco_002": [
        "55555555-5555-5555-5555-555555555555",  # FAQ: 如何修改登录密码
        "eeeeeeee-2222-2222-2222-222222222222",  # FAQ: 如何更换绑定手机号
        "a5555555-5555-5555-5555-555555555555",  # POLICY: 账户安全保护政策
    ],
    "case_acco_004": [
        "44444444-4444-4444-4444-444444444444",  # FAQ: 账户被盗怎么办
        "a5555555-5555-5555-5555-555555555555",  # POLICY: 账户安全保护政策
        "ad0d0d0d-7777-7777-7777-777777777777",  # POLICY: 账号安全事件处理规则
        "c5555555-5555-5555-5555-555555555555",  # CASE: 异地登录案例
    ],
    "case_acco_005": [
        "55555555-5555-5555-5555-555555555555",  # FAQ: 如何修改登录密码
        "eeeeeeee-2222-2222-2222-222222222222",  # FAQ: 如何更换绑定手机号
        "b5555555-5555-5555-5555-555555555555",  # CASE: 忘记密码案例
    ],
    "case_acco_007": [
        "55555555-5555-5555-5555-555555555555",  # FAQ: 如何修改登录密码
        "a5555555-5555-5555-5555-555555555555",  # POLICY: 账户安全保护政策
    ],
    "case_acco_008": [
        "eeeeeeee-4444-4444-4444-444444444444",  # FAQ: 账号登录异常怎么办
        "ad0d0d0d-7777-7777-7777-777777777777",  # POLICY: 账号安全事件处理规则
        "c5555555-5555-5555-5555-555555555555",  # CASE: 异地登录案例
    ],
    "case_acco_009": [
        "a6666666-6666-6666-6666-666666666666",  # POLICY: 账户冻结与解冻规则
    ],
    "case_acco_010": [
        "ffffffff-6666-6666-6666-666666666666",  # FAQ: 如何注销账号
        "ae0e0e0e-7777-7777-7777-777777777777",  # POLICY: 个人信息更正与删除规则
    ],
    "case_acco_011": [
        "eeeeeeee-2222-2222-2222-222222222222",  # FAQ: 如何更换绑定手机号
        "a5555555-5555-5555-5555-555555555555",  # POLICY: 账户安全保护政策
    ],
    "case_acco_013": [
        "eeeeeeee-2222-2222-2222-222222222222",  # FAQ: 如何更换绑定手机号
        "ffffffff-6666-6666-6666-666666666666",  # FAQ: 如何注销账号
    ],
    "case_acco_014": [
        "eeeeeeee-3333-3333-3333-333333333333",  # FAQ: 如何修改实名认证信息
        "ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 个人信息泄露与身份盗用处理规则
        "ad0d0d0d-6666-6666-6666-666666666666",  # POLICY: 隐私泄露升级处理规则
        "ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # CASE: 信息泄露案例
    ],
    "case_acco_015": [
        "44444444-4444-4444-4444-444444444444",  # FAQ: 账户被盗怎么办
        "ad0d0d0d-7777-7777-7777-777777777777",  # POLICY: 账号安全事件处理规则
        "a5555555-5555-5555-5555-555555555555",  # POLICY: 账户安全保护政策
    ],

    # === TECHNICAL CASES ===
    "case_tech_001": [
        "66666666-6666-6666-6666-666666666666",  # FAQ: APP闪退如何解决
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 技术服务支持政策
        "b6666666-6666-6666-6666-666666666666",  # CASE: APP闪退案例
    ],
    "case_tech_002": [
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # FAQ: 支付失败如何处理
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 技术服务支持政策
    ],
    "case_tech_003": [
        "eeeeeeee-1111-1111-1111-111111111111",  # FAQ: 支付成功但订单显示未支付怎么办
        "ad0d0d0d-5555-5555-5555-555555555555",  # POLICY: 支付异常核验规则
        "ad0d0d0d-4444-4444-4444-444444444444",  # POLICY: 重复扣款处理规则
        "b7777777-7777-7777-7777-777777777777",  # CASE: 扣款案例
    ],
    "case_tech_004": [
        "f0f0f0f0-1111-1111-1111-111111111111",  # FAQ: 上传图片失败怎么办
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 技术服务支持政策
    ],
    "case_tech_005": [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 技术服务支持政策
    ],
    "case_tech_006": [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 技术服务支持政策
    ],
    "case_tech_007": [
        "66666666-6666-6666-6666-666666666666",  # FAQ: APP闪退如何解决
        "ca0a0a0a-3333-3333-3333-333333333333",  # CASE: 更新后订单记录丢失
    ],
    "case_tech_008": [
        "eeeeeeee-1111-1111-1111-111111111111",  # FAQ: 支付成功但订单显示未支付怎么办
        "ad0d0d0d-5555-5555-5555-555555555555",  # POLICY: 支付异常核验规则
        "b7777777-7777-7777-7777-777777777777",  # CASE: 扣款案例
    ],
    "case_tech_009": [
        "dddddddd-7777-7777-7777-777777777777",  # FAQ: 如何开具发票
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # POLICY: 技术服务支持政策
    ],

    # === PRODUCT CONSULTING CASES ===
    "case_prod_001": [
        "ffffffff-1111-1111-1111-111111111111",  # FAQ: 如何了解商品参数和功能
        "abbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 商品质量保证条款
    ],
    "case_prod_002": [
        "ffffffff-1111-1111-1111-111111111111",  # FAQ: 如何了解商品参数和功能
    ],
    "case_prod_004": [
        "ffffffff-1111-1111-1111-111111111111",  # FAQ: 如何了解商品参数和功能
        "abbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 商品质量保证条款
    ],
    "case_prod_005": [
        "ffffffff-1111-1111-1111-111111111111",  # FAQ: 如何了解商品参数和功能
    ],
    "case_prod_006": [
        "ffffffff-8888-8888-8888-888888888888",  # FAQ: 售后维修服务如何申请
        "abbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 商品质量保证条款
    ],
    "case_prod_007": [
        "ffffffff-1111-1111-1111-111111111111",  # FAQ: 如何了解商品参数和功能
    ],
    "case_prod_008": [
        "ffffffff-8888-8888-8888-888888888888",  # FAQ: 售后维修服务如何申请
        "abbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 商品质量保证条款
    ],

    # === LOGISTICS CASES ===
    "case_logi_001": [
        "dddddddd-5555-5555-5555-555555555555",  # FAQ: 物流长时间不更新怎么办
        "a7777777-7777-7777-7777-777777777777",  # POLICY: 物流配送政策
        "c8888888-8888-8888-8888-888888888888",  # CASE: 物流信息未更新案例
    ],
    "case_logi_002": [
        "99999999-9999-9999-9999-999999999999",  # FAQ: 快递丢失如何处理
        "a8888888-8888-8888-8888-888888888888",  # POLICY: 快递损失赔偿标准
        "b2222222-2222-2222-2222-222222222222",  # CASE: 未收到货案例
    ],
    "case_logi_003": [
        "88888888-8888-8888-8888-888888888888",  # FAQ: 如何修改收货地址
        "a7777777-7777-7777-7777-777777777777",  # POLICY: 物流配送政策
    ],
    "case_logi_004": [
        "a7777777-7777-7777-7777-777777777777",  # POLICY: 物流配送政策
    ],
    "case_logi_005": [
        "99999999-9999-9999-9999-999999999999",  # FAQ: 快递丢失如何处理
        "a8888888-8888-8888-8888-888888888888",  # POLICY: 快递损失赔偿标准
        "b8888888-8888-8888-8888-888888888888",  # CASE: 快递破损案例
    ],
    "case_logi_006": [
        "dddddddd-6666-6666-6666-666666666666",  # FAQ: 订单状态异常如何处理
        "a7777777-7777-7777-7777-777777777777",  # POLICY: 物流配送政策
    ],
    "case_logi_007": [
        "ffffffff-7777-7777-7777-777777777777",  # FAQ: 可以指定快递公司吗
        "a7777777-7777-7777-7777-777777777777",  # POLICY: 物流配送政策
    ],
    "case_logi_008": [
        "dddddddd-5555-5555-5555-555555555555",  # FAQ: 物流长时间不更新怎么办
        "ae0e0e0e-6666-6666-6666-666666666666",  # POLICY: 物流异常升级处理规则
        "c8888888-8888-8888-8888-888888888888",  # CASE: 物流信息未更新案例
    ],
    "case_logi_009": [
        "a7777777-7777-7777-7777-777777777777",  # POLICY: 物流配送政策
    ],
    "case_logi_010": [
        "99999999-9999-9999-9999-999999999999",  # FAQ: 快递丢失如何处理
        "a8888888-8888-8888-8888-888888888888",  # POLICY: 快递损失赔偿标准
        "b9999999-9999-9999-9999-999999999999",  # CASE: 冒名签收案例
    ],
    "case_logi_011": [
        "a8888888-8888-8888-8888-888888888888",  # POLICY: 快递损失赔偿标准
        "ae0e0e0e-6666-6666-6666-666666666666",  # POLICY: 物流异常升级处理规则
        "b8888888-8888-8888-8888-888888888888",  # CASE: 快递破损案例
    ],

    # === COMPLAINT CASES ===
    "case_comp_005": [
        "ad0d0d0d-6666-6666-6666-666666666666",  # POLICY: 隐私泄露升级处理规则
        "ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 个人信息泄露与身份盗用处理规则
        "ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # CASE: 信息泄露案例
        "c4444444-4444-4444-4444-444444444444",  # CASE: 个人信息泄露案例
    ],
    "case_comp_006": [
        "a9999999-9999-9999-9999-999999999999",  # POLICY: 客户投诉处理流程
        "ad0d0d0d-8888-8888-8888-888888888888",  # POLICY: 投诉升级规则
        "c3333333-3333-3333-3333-333333333333",  # CASE: 12315投诉案例
    ],
    "case_comp_007": [
        "eeeeeeee-9999-9999-9999-999999999999",  # FAQ: 商品与描述不符可以退款吗
        "a9999999-9999-9999-9999-999999999999",  # POLICY: 客户投诉处理流程
        "b1111111-1111-1111-1111-111111111111",  # CASE: 描述不符案例
    ],
    "case_comp_010": [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # FAQ: 对客服服务不满意怎么办
        "a9999999-9999-9999-9999-999999999999",  # POLICY: 客户投诉处理流程
    ],
    "case_comp_011": [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # FAQ: 对客服服务不满意怎么办
        "a9999999-9999-9999-9999-999999999999",  # POLICY: 客户投诉处理流程
    ],
    "case_comp_012": [
        "eeeeeeee-7777-7777-7777-777777777777",  # FAQ: 如何投诉商家或商品
        "a9999999-9999-9999-9999-999999999999",  # POLICY: 客户投诉处理流程
    ],
    "case_comp_013": [
        "ad0d0d0d-6666-6666-6666-666666666666",  # POLICY: 隐私泄露升级处理规则
        "ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb",  # POLICY: 个人信息泄露与身份盗用处理规则
        "ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # CASE: 信息泄露案例
        "c4444444-4444-4444-4444-444444444444",  # CASE: 个人信息泄露案例
    ],

    # === OTHER/BILLING/INVOICE CASES ===
    "case_othe_002": [
        "dddddddd-7777-7777-7777-777777777777",  # FAQ: 如何开具发票
        "ad0d0d0d-3333-3333-3333-333333333333",  # POLICY: 发票开具规则
        "c7777777-7777-7777-7777-777777777777",  # CASE: 发票争议案例
    ],
    "case_othe_003": [
        "dddddddd-8888-8888-8888-888888888888",  # FAQ: 发票抬头写错了能修改吗
        "ad0d0d0d-3333-3333-3333-333333333333",  # POLICY: 发票开具规则
    ],
    "case_othe_006": [
        "ffffffff-9999-9999-9999-999999999999",  # FAQ: 优惠券支付的订单退款如何计算
        "ca0a0a0a-7777-7777-7777-777777777777",  # CASE: 满减优惠未生效案例
    ],
    "case_othe_009": [
        "dddddddd-9999-9999-9999-999999999999",  # FAQ: 重复扣款了怎么办
        "ad0d0d0d-4444-4444-4444-444444444444",  # POLICY: 重复扣款处理规则
        "c6666666-6666-6666-6666-666666666666",  # CASE: 重复付款案例
    ],
    "case_othe_010": [
        "eeeeeeee-1111-1111-1111-111111111111",  # FAQ: 支付成功但订单显示未支付怎么办
        "ad0d0d0d-5555-5555-5555-555555555555",  # POLICY: 支付异常核验规则
        "b7777777-7777-7777-7777-777777777777",  # CASE: 扣款案例
    ],
    "case_othe_011": [
        "dddddddd-7777-7777-7777-777777777777",  # FAQ: 如何开具发票
        "ad0d0d0d-3333-3333-3333-333333333333",  # POLICY: 发票开具规则
        "c7777777-7777-7777-7777-777777777777",  # CASE: 发票争议案例
    ],
    "case_othe_012": [
        "dddddddd-8888-8888-8888-888888888888",  # FAQ: 发票抬头写错了能修改吗
        "ad0d0d0d-3333-3333-3333-333333333333",  # POLICY: 发票开具规则
        "c7777777-7777-7777-7777-777777777777",  # CASE: 发票争议案例
    ],
    "case_othe_013": [
        "dddddddd-7777-7777-7777-777777777777",  # FAQ: 如何开具发票
        "ad0d0d0d-3333-3333-3333-333333333333",  # POLICY: 发票开具规则
        "c7777777-7777-7777-7777-777777777777",  # CASE: 发票争议案例
    ],
}

# ---------------------------------------------------------------------------
# Manual review cases — cannot be reliably auto-labeled
# ---------------------------------------------------------------------------

MANUAL_REVIEW_CASES: dict[str, dict[str, Any]] = {
    "case_prod_003": {
        "reason": "No FAQ/Policy about membership benefits. Multiple plausible docs but no clear primary evidence.",
        "candidate_doc_ids": ["ffffffff-1111-1111-1111-111111111111"],  # FAQ: 商品参数 — weakest match
        "why_not_auto": "Membership program is not covered by existing knowledge seed. Product consulting FAQ covers general product info, not membership-specific content.",
        "suggested_decision": "Label with broadest FAQ or leave empty. Current knowledge seed lacks membership content.",
    },
    "case_othe_001": {
        "reason": "Job/inquiry question about part-time客服 positions. No knowledge record covers HR/job inquiries.",
        "candidate_doc_ids": [],
        "why_not_auto": "No FAQ, Policy, or Case record covers job applications or recruitment.",
        "suggested_decision": "Leave empty — this is outside the current knowledge domain.",
    },
    "case_othe_004": {
        "reason": "Customer asks if platform has physical stores. No knowledge record about store locations.",
        "candidate_doc_ids": [],
        "why_not_auto": "No FAQ covers offline store information.",
        "suggested_decision": "Leave empty — this is outside the current knowledge domain.",
    },
    "case_othe_005": {
        "reason": "Customer asks about points balance. No FAQ about points/loyalty program.",
        "candidate_doc_ids": [],
        "why_not_auto": "No FAQ covers points balance inquiry.",
        "suggested_decision": "Leave empty — this is outside the current knowledge domain.",
    },
    "case_othe_007": {
        "reason": "Customer asks about WeChat group. No knowledge record about customer communication groups.",
        "candidate_doc_ids": [],
        "why_not_auto": "No FAQ covers WeChat groups or community channels.",
        "suggested_decision": "Leave empty — this is outside the current knowledge domain.",
    },
    "case_othe_008": {
        "reason": "Follow-up on packaging improvement suggestion. Suggestion/complaint, not a standard issue.",
        "candidate_doc_ids": [],
        "why_not_auto": "No FAQ covers packaging suggestions. Too ambiguous.",
        "suggested_decision": "Leave empty — suggestion follow-up, not a standard retrieval scenario.",
    },
    "case_edge_001": {
        "reason": "Edge case: single-character text '退'. No meaningful retrieval possible.",
        "candidate_doc_ids": [],
        "why_not_auto": "Single character provides no semantic signal for doc_id mapping.",
        "suggested_decision": "Leave empty — edge case with insufficient semantic content.",
    },
    "case_edge_002": {
        "reason": "Edge case: very long mixed Chinese/English text. Complex multi-issue ticket (refund + complaint + technical).",
        "candidate_doc_ids": [],
        "why_not_auto": "Multiple overlapping issues make doc_id selection ambiguous. Requires human judgment to determine primary evidence.",
        "suggested_decision": "Leave empty or label after human review of which issue is primary.",
    },
    "case_edge_003": {
        "reason": "Edge case: special characters only. No semantic content.",
        "candidate_doc_ids": [],
        "why_not_auto": "Special characters provide no semantic signal for doc_id mapping.",
        "suggested_decision": "Leave empty — edge case with no semantic content.",
    },
    "case_edge_004": {
        "reason": "Edge case: Chinese with special characters only. No coherent semantic content.",
        "candidate_doc_ids": [],
        "why_not_auto": "Non-coherent text provides no signal for doc_id mapping.",
        "suggested_decision": "Leave empty — edge case with no coherent semantic content.",
    },
    "case_edge_005": {
        "reason": "Edge case: numbers and symbols only. No coherent semantic content.",
        "candidate_doc_ids": [],
        "why_not_auto": "Numbers and symbols provide no signal for doc_id mapping.",
        "suggested_decision": "Leave empty — edge case with no semantic content.",
    },
    "case_logi_004": {
        "reason": "Reschedule delivery — only POLICY match available, no FAQ specifically covers rescheduling.",
        "candidate_doc_ids": ["a7777777-7777-7777-7777-777777777777"],
        "why_not_auto": "Only POLICY a7777777 loosely covers delivery timing. No FAQ or CASE specifically about rescheduling. Low confidence.",
        "suggested_decision": "Label with POLICY only or leave for human to decide if a broader label is appropriate.",
    },
    "case_logi_009": {
        "reason": "International customs duties — only POLICY match available, no FAQ about international shipping.",
        "candidate_doc_ids": ["a7777777-7777-7777-7777-777777777777"],
        "why_not_auto": "Only POLICY broadly covers delivery. No FAQ about customs duties or international shipping. Low confidence.",
        "suggested_decision": "Label with POLICY only or leave empty. Knowledge gap about international shipping.",
    },
    "case_tech_005": {
        "reason": "Slow website loading — only POLICY match, no specific FAQ about website speed.",
        "candidate_doc_ids": ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
        "why_not_auto": "POLICY covers general tech support but no FAQ specifically addresses website speed. Single-doc label is weak.",
        "suggested_decision": "Label with POLICY only. Adequate but not ideal.",
    },
    "case_tech_006": {
        "reason": "Can't select address during checkout — only POLICY match, no specific FAQ.",
        "candidate_doc_ids": ["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
        "why_not_auto": "POLICY covers general tech support. No FAQ about address selection bug. Low confidence.",
        "suggested_decision": "Label with POLICY only. Adequate but not ideal.",
    },
}


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def _load_knowledge_doc_ids() -> set[str]:
    """Load all doc_ids from knowledge seed files to validate labels."""
    doc_ids: set[str] = set()
    for seed_file in [
        "data/knowledge/faq_seed.json",
        "data/knowledge/policy_seed.json",
        "data/knowledge/case_seed.json",
    ]:
        with open(seed_file, encoding="utf-8") as f:
            records = json.load(f)
            for r in records:
                doc_ids.add(r["id"])
    return doc_ids


def _load_existing_golden(path: Path) -> list[dict[str, str]]:
    """Load current golden_expectations.csv rows."""
    rows: list[dict[str, str]] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    return rows, fieldnames


def _validate_all_doc_ids_exist(
    labels: dict[str, list[str]],
    valid_ids: set[str],
) -> list[str]:
    """Check that all referenced doc_ids exist in knowledge seeds."""
    errors: list[str] = []
    for case_id, doc_ids in labels.items():
        for doc_id in doc_ids:
            if doc_id not in valid_ids:
                errors.append(f"{case_id}: doc_id {doc_id} not found in knowledge seeds")
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load valid doc_ids from knowledge seeds
    valid_ids = _load_knowledge_doc_ids()
    print(f"Loaded {len(valid_ids)} valid doc_ids from knowledge seeds")

    # Validate all labels
    errors = _validate_all_doc_ids_exist(HIGH_CONFIDENCE_LABELS, valid_ids)
    if errors:
        print("ERRORS: Invalid doc_ids found:")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)
    print("All doc_ids validated against knowledge seeds: OK")

    # Load existing CSV
    rows, fieldnames = _load_existing_golden(GOLDEN_PATH)
    print(f"Loaded {len(rows)} rows from golden_expectations.csv")

    # Count existing labels
    existing_labeled = sum(1 for r in rows if (r.get("expected_relevant_doc_ids") or "").strip())
    print(f"Existing labeled cases: {existing_labeled}")

    # Track stats
    new_labeled = 0
    already_labeled = 0
    kept_empty = 0
    manual_review_flagged = 0
    updated_rows = []

    for row in rows:
        case_id = row["case_id"]
        current_val = (row.get("expected_relevant_doc_ids") or "").strip()

        if current_val:
            # Already has labels — keep as-is
            already_labeled += 1
            updated_rows.append(row)
            continue

        if case_id in MANUAL_REVIEW_CASES:
            # Flagged for manual review — keep empty
            manual_review_flagged += 1
            kept_empty += 1
            updated_rows.append(row)
            continue

        if case_id in HIGH_CONFIDENCE_LABELS:
            doc_ids = HIGH_CONFIDENCE_LABELS[case_id]
            row["expected_relevant_doc_ids"] = ";".join(doc_ids)
            new_labeled += 1
            updated_rows.append(row)
            continue

        # No label defined — keep empty
        kept_empty += 1
        updated_rows.append(row)

    # Write updated CSV
    with open(GOLDEN_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print("\nResults:")
    print(f"  Already labeled (kept): {already_labeled}")
    print(f"  Newly labeled:          {new_labeled}")
    print(f"  Manual review (empty):  {manual_review_flagged}")
    print(f"  Kept empty (no match):  {kept_empty}")
    print(f"  Total:                  {already_labeled + new_labeled + kept_empty}")

    # Verify
    rows_after, _ = _load_existing_golden(GOLDEN_PATH)
    final_labeled = sum(1 for r in rows_after if (r.get("expected_relevant_doc_ids") or "").strip())
    print(f"\nFinal labeled count: {final_labeled}")
    print(f"Unlabeled count: {len(rows_after) - final_labeled}")

    # Write manual review report
    write_manual_review_report()

    print("\nDone — golden_expectations.csv updated")


def write_manual_review_report() -> None:
    """Generate manual review report."""
    lines = [
        "# Phase 10.7 — Full-Dataset Doc-Level Manual Review Report",
        "",
        "*Generated at 2026-05-06 UTC*",
        "*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*",
        "",
        "## Purpose",
        "",
        "Cases that could not be reliably auto-labeled with `expected_relevant_doc_ids`",
        "due to insufficient knowledge coverage, ambiguous semantics, or edge-case status.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        "| Total eval cases | 101 |",
        f"| Auto-labeled with high confidence | {101 - len(MANUAL_REVIEW_CASES) - 14} |",  # approximate
        f"| Sent to manual review | {len(MANUAL_REVIEW_CASES)} |",
        "| Already labeled (P0) | 14 |",
        "",
        "## Manual Review Cases",
        "",
        "| Case ID | Reason | Candidate Doc IDs | Why Not Auto-labeled | Suggested Human Decision |",
        "|---|---|---|---|---|",
    ]

    for case_id in sorted(MANUAL_REVIEW_CASES.keys()):
        info = MANUAL_REVIEW_CASES[case_id]
        candidate_str = "; ".join(info["candidate_doc_ids"]) if info["candidate_doc_ids"] else "(none)"
        lines.append(
            f"| {case_id} | {info['reason']} | {candidate_str} | "
            f"{info['why_not_auto']} | {info['suggested_decision']} |"
        )

    lines.extend([
        "",
        "## Categories of Manual Review Cases",
        "",
        "### Edge Cases (5)",
        "case_edge_001 through case_edge_005 — Single chars, special chars, numbers-only text.",
        "No semantic content for doc_id mapping.",
        "",
        "### Knowledge Gap Cases (4)",
        "- **case_othe_001**: Job inquiries (no HR knowledge)",
        "- **case_othe_004**: Physical store locations (no offline store knowledge)",
        "- **case_othe_005**: Points balance (no loyalty program knowledge)",
        "- **case_othe_007**: WeChat group inquiries (no community channel knowledge)",
        "",
        "### Ambiguous Cases (4)",
        "- **case_othe_008**: Packaging suggestion follow-up — not a standard retrieval issue",
        "- **case_edge_002**: Multi-issue ticket (refund + complaint + technical) — ambiguous primary evidence",
        "- **case_prod_003**: Membership benefits — knowledge seed has no membership content",
        "- **case_logi_004**: Reschedule delivery — only weak POLICY match, no FAQ",
        "- **case_logi_009**: International customs duties — only weak POLICY match",
        "",
        "### Low-Confidence Auto-Label (2)",
        "- **case_tech_005**: Slow website — labeled with POLICY only, but weak match",
        "- **case_tech_006**: Address selection — labeled with POLICY only, but weak match",
        "",
        "## Impact on Evaluation",
        "",
        "Manual review cases will remain unlabeled (`expected_relevant_doc_ids` empty).",
        "The doc-level evaluation will skip these cases (backward compatible behavior).",
        "",
        "**Recommendation**: Add knowledge seed records for the 4 knowledge gap cases",
        "if full coverage is needed. Edge cases can remain unlabeled permanently.",
    ])

    MANUAL_REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANUAL_REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Manual review report: {MANUAL_REVIEW_PATH}")


if __name__ == "__main__":
    main()
