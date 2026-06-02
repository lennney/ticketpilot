"""Process CLINC150 dataset into TicketPilot format."""
import json
import os
import random
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent

# Customer service related intents from CLINC150
CS_INTENTS = {
    "balance": "account_issue",
    "bill_balance": "account_issue",
    "bill_due": "account_issue",
    "credit_limit": "account_issue",
    "credit_limit_change": "account_issue",
    "credit_score": "account_issue",
    "freeze_account": "account_issue",
    "improve_credit_score": "account_issue",
    "insurance": "product_consulting",
    "insurance_change": "product_consulting",
    "interest_rate": "product_consulting",
    "international_fees": "complaint",
    "min_payment": "account_issue",
    "pay_bill": "refund",
    "pin_change": "account_issue",
    "report_fraud": "complaint",
    "report_lost_card": "complaint",
    "rewards_balance": "account_issue",
    "spending_history": "account_issue",
    "transactions": "account_issue",
    "transfer": "refund",
    "account_blocked": "account_issue",
    "pto_balance": "account_issue",
    "shopping_list": "product_consulting",
    "shopping_list_update": "product_consulting",
}

# Risk flags by intent category
RISK_MAP = {
    "account_issue": ["account_security_risk"],
    "complaint": ["complaint_risk", "legal_risk"],
    "refund": ["compensation_risk"],
    "product_consulting": [],
    "logistics": [],
    "technical_issue": [],
    "return_exchange": ["policy_conflict"],
    "other": ["low_confidence"],
}

print("Loading CLINC150 dataset...", flush=True)
with open("/tmp/clinc.json") as f:
    raw = json.load(f)

# Combine train + val
all_items = raw["train"] + raw["val"]
print(f"Total raw items: {len(all_items)}", flush=True)

# Filter for CS intents and process
processed = []
for item in all_items:
    text, intent = item[0], item[1]
    if intent in CS_INTENTS:
        mapped = CS_INTENTS[intent]
        processed.append({
            "instruction": text,
            "response": "",  # No response in CLINC150
            "intent": intent,
            "mapped_intent": mapped,
            "risk_flags": RISK_MAP.get(mapped, []),
            "severity": "LOW",
            "source": "clinc150",
        })

random.seed(42)
random.shuffle(processed)
processed = processed[:500]  # Cap at 500

print(f"Processed {len(processed)} CS items", flush=True)

# Stats
from collections import Counter
intents = Counter(d["mapped_intent"] for d in processed)
print("\nIntent distribution:")
for k, v in sorted(intents.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

# Merge with existing generated data
gen_path = project_root / "data/knowledge/external/deepeval_generated.json"
existing = []
if gen_path.exists():
    with open(gen_path, encoding="utf-8") as f:
        existing = json.load(f)
    print(f"\nExisting generated data: {len(existing)} items")

# Save CLINC150 data
os.makedirs(str(project_root / "data/knowledge/external"), exist_ok=True)
clinc_path = project_root / "data/knowledge/external/clinc150_processed.json"
with open(clinc_path, "w", encoding="utf-8") as f:
    json.dump(processed, f, ensure_ascii=False, indent=2)
print(f"Saved -> {clinc_path}")

# Save combined dataset
combined = existing + processed
combined_path = project_root / "data/knowledge/external/combined_dataset.json"
with open(combined_path, "w", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)
print(f"Combined ({len(combined)} items) -> {combined_path}")
