"""Download Bitext dataset via HTTP (no datasets library needed)."""
import json
import os
import urllib.request
import csv
import io

URL = "https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/resolve/main/bitext-customer-support-llm-chatbot-training-dataset.csv"

# 意图映射
INTENT_MAP = {
    "cancel_order": "refund", "return_item": "refund",
    "get_refund": "refund", "check_refund_status": "refund",
    "track_order": "logistics", "set_up_shipping": "logistics",
    "change_shipping_address": "logistics", "delivery_options": "logistics",
    "place_order": "return_exchange", "change_order": "return_exchange",
    "create_account": "account_issue", "delete_account": "account_issue",
    "edit_account": "account_issue", "recover_password": "account_issue",
    "switch_account": "account_issue",
    "complaint": "complaint", "review": "complaint",
    "contact_support": "other", "contact_human_agent": "other",
}

print("下载Bitext数据集...")
req = urllib.request.Request(URL, headers={"User-Agent": "ticketpilot/0.1"})
with urllib.request.urlopen(req, timeout=60) as resp:
    raw = resp.read().decode("utf-8")
print(f"下载完成，{len(raw)}字节")

reader = csv.DictReader(io.StringIO(raw))
processed = []
counts = {}
for row in reader:
    intent = row.get("intent", "other")
    mapped = INTENT_MAP.get(intent, "other")
    if counts.get(mapped, 0) < 60:
        processed.append({
            "instruction": row.get("instruction", ""),
            "response": row.get("response", ""),
            "category": row.get("category", ""),
            "intent": intent,
            "mapped_intent": mapped,
        })
        counts[mapped] = counts.get(mapped, 0) + 1
    if len(processed) >= 500:
        break

os.makedirs("data/knowledge/external", exist_ok=True)
out = "data/knowledge/external/bitext_processed.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(processed, f, ensure_ascii=False, indent=2)

print(f"保存{len(processed)}条到 {out}")
print("\n意图分布:")
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}条")
