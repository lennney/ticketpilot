"""Generate customer service dataset using DeepSeek API (small batches)."""
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("TICKETPILOT_LLM_API_KEY", ""),
    base_url=os.environ.get("TICKETPILOT_LLM_BASE_URL", "https://api.deepseek.com"),
)

# 场景定义 - 每批生成20条
SCENARIOS = [
    {"intent": "refund", "batches": 4, "desc": "退款退货"},
    {"intent": "return_exchange", "batches": 3, "desc": "换货"},
    {"intent": "account_issue", "batches": 3, "desc": "账号问题"},
    {"intent": "logistics", "batches": 3, "desc": "物流"},
    {"intent": "complaint", "batches": 3, "desc": "投诉"},
    {"intent": "technical_issue", "batches": 3, "desc": "技术问题"},
    {"intent": "product_consulting", "batches": 3, "desc": "产品咨询"},
    {"intent": "other", "batches": 2, "desc": "其他"},
]

RISK_FLAGS = (
    "complaint_risk/compensation_risk/legal_risk/"
    "privacy_risk/account_security_risk/policy_conflict/"
    "insufficient_evidence/low_confidence"
)

all_data = []
total_batches = sum(s["batches"] for s in SCENARIOS)
batch_num = 0

for scenario in SCENARIOS:
    intent = scenario["intent"]
    desc = scenario["desc"]

    for batch_i in range(scenario["batches"]):
        batch_num += 1
        print(
            f"[{batch_num}/{total_batches}] {desc} batch{batch_i+1}...",
            flush=True,
        )

        prompt = (
            "Generate 20 Chinese customer service dialogues for: "
            + desc
            + ".\nFormat: JSON array, each item has "
            'instruction(customer question 10-50 chars), '
            'response(agent reply 50-150 chars), intent('
            + intent
            + "), risk_flags(from "
            + RISK_FLAGS
            + "), severity(LOW/MEDIUM/HIGH).\n"
            "Return JSON array only, no other text."
        )

        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
                temperature=0.8,
            )
            content = resp.choices[0].message.content
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                items = json.loads(content[start:end])
                for item in items:
                    item["mapped_intent"] = intent
                all_data.extend(items)
                print(f"  +{len(items)} (total {len(all_data)})", flush=True)
            else:
                print("  parse failed", flush=True)
        except Exception as e:
            print(f"  error: {e}", flush=True)

        time.sleep(0.5)

# 保存
os.makedirs("data/knowledge/external", exist_ok=True)
out = "data/knowledge/external/deepeval_generated.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"\nTotal {len(all_data)} -> {out}", flush=True)
from collections import Counter

for k, v in sorted(
    Counter(d.get("mapped_intent") for d in all_data).items(),
    key=lambda x: -x[1],
):
    print(f"  {k}: {v}", flush=True)
