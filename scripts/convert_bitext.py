#!/usr/bin/env python3
"""Convert Bitext to TicketPilot knowledge base - single translation per call."""
import json
import uuid
import time
from pathlib import Path

import requests
from datasets import load_dataset

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"
LLM_URL = "https://api.deepseek.com"

llm_key = ""
with open(Path(__file__).resolve().parent.parent / ".env.local") as f:
    for line in f:
        s = line.strip()
        if s.startswith("TICKETPILOT_LLM_API_KEY"):
            llm_key = s.split("=", 1)[1]


def translate(text, max_retries=3):
    """Translate single English CS response to Chinese."""
    prompt = f"""将以下英文客服回复翻译成自然、专业的中文。适配中国电商场景（credit card→银行卡，shipping address→收货地址，order number→订单号等）。
只输出翻译结果，不要加任何前缀或解释。

{text}"""

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{LLM_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
                timeout=60,
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                print(f"    Translation failed: {e}")
                return text


def main():
    print("Loading Bitext dataset...")
    ds = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset", split="train")
    print(f"Loaded {len(ds)} records")

    domain_map = {
        "REFUND": "refund",
        "ORDER": "order",
        "DELIVERY": "shipping",
        "SHIPPING": "shipping",
        "ACCOUNT": "account",
        "PAYMENT": "payment",
        "CANCEL": "order",
        "INVOICE": "payment",
    }

    # Group by (category, intent), pick top 2 longest responses
    from collections import defaultdict
    by_intent = defaultdict(list)
    for row in ds:
        cat = row["category"]
        if cat not in domain_map:
            continue
        by_intent[(cat, row["intent"])].append(row)

    selected = []
    for (cat, intent), items in by_intent.items():
        sorted_items = sorted(items, key=lambda r: len(r["response"]), reverse=True)
        for item in sorted_items[:2]:  # Top 2 per intent
            selected.append({
                "category": cat,
                "intent": intent,
                "instruction": item["instruction"],
                "response": item["response"],
                "domain": domain_map[cat],
            })

    print(f"Selected {len(selected)} items, translating one by one...")

    faq_entries = []
    policy_entries = []
    case_entries = []

    for i, item in enumerate(selected):
        domain = item["domain"]
        intent = item["intent"]
        instruction = item["instruction"]
        response = item["response"]

        # Translate instruction (question)
        q_cn = translate(instruction)
        time.sleep(0.5)

        # Translate response (answer)
        a_cn = translate(response)
        time.sleep(0.5)

        # Clean up {{placeholders}}
        for ph in ["{{Order Number}}", "{{Delivery Country}}", "{{Account Category}}"]:
            q_cn = q_cn.replace(ph, "订单号")
            a_cn = a_cn.replace(ph, "订单号")

        # Create FAQ
        faq_entries.append({
            "id": str(uuid.uuid4()),
            "doc_type": "FAQ",
            "business_domain": domain,
            "title": q_cn[:80],
            "content": a_cn[:500],
            "intent_tags": [intent, domain],
        })

        # Create Policy (for longer responses)
        if len(a_cn) > 200:
            policy_entries.append({
                "id": str(uuid.uuid4()),
                "doc_type": "POLICY",
                "business_domain": domain,
                "policy_code": f"BT-{domain[:3].upper()}-{len(policy_entries)+1:03d}",
                "title": q_cn[:60],
                "content": a_cn,
                "effective_date": "2024-01-01",
            })

        # Create Case
        case_entries.append({
            "id": str(uuid.uuid4()),
            "doc_type": "CASE",
            "business_domain": domain,
            "case_id": f"BT-{domain[:3].upper()}-{len(case_entries)+1:04d}",
            "issue_summary": q_cn[:200],
            "resolution": a_cn[:300],
            "risk_level": "low",
            "compensation_amount": 0.0,
        })

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(selected)} translated")

    # Save
    for name, data in [("bitext_faq.json", faq_entries), ("bitext_policy.json", policy_entries), ("bitext_case.json", case_entries)]:
        with open(DATA_DIR / name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{name}: {len(data)} items")

    print(f"\nTotal: {len(faq_entries)} FAQ + {len(policy_entries)} Policy + {len(case_entries)} Case")


if __name__ == "__main__":
    main()
