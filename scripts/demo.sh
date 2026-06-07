#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "==================================="
echo "  TicketPilot One-Click Demo"
echo "==================================="
echo ""

# 1. Check Docker
echo "[1/5] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker first."
    echo "  macOS: open -a Docker"
    echo "  Linux: sudo systemctl start docker"
    exit 1
fi
echo "  Docker is running."

# 2. Start PostgreSQL
echo ""
echo "[2/5] Starting PostgreSQL + pgvector..."
docker compose up -d
# Wait for DB to be ready
for i in {1..15}; do
    if docker compose exec -T db pg_isready -U ticketpilot > /dev/null 2>&1; then
        echo "  Database is ready."
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "  WARNING: Database may not be fully ready yet, continuing anyway..."
    fi
    sleep 1
done

# 3. Seed knowledge data
echo ""
echo "[3/5] Seeding knowledge base..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi
uv run python -c "
from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks
seed_knowledge_chunks(clear_existing=True)
print('  Knowledge chunks seeded successfully.')
" 2>&1 | tail -5

# 4. Run demo pipeline
echo ""
echo "[4/5] Running demo pipeline..."
uv run python -c "
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

tickets = [
    ('Refund request', '我要退款，订单号：123456，收到的商品有质量问题。', 'CUST_001'),
    ('Complaint + legal threat', '客服态度太差了，我要投诉！要求3倍赔偿，不然我就找律师起诉你们。', 'CUST_002'),
    ('Account security', '我的账号被冻结了，个人信息可能泄露了。', 'CUST_003'),
    ('Logistics query', '我的快递到哪里了？已经等了一周了。', 'CUST_004'),
    ('Short input', '退款。', 'CUST_005'),
]

print('')
print('  Results:')
print('  ' + '-' * 80)
for label, text, cid in tickets:
    ticket = RawTicket(original_text=text, submitted_at=datetime.utcnow(), customer_id=cid)
    result = intake_risk_pipeline(ticket)
    intent = result.classification.intent.value
    conf = f'{result.classification.confidence:.2f}'
    severity = result.risk_assessment.severity.value
    flags = [f.value for f in result.risk_assessment.flags] or ['none']
    human = 'YES' if result.risk_assessment.must_human_review else 'no'
    print(f'  {label}')
    print(f'    Intent: {intent}  |  Confidence: {conf}  |  Severity: {severity}  |  Human review: {human}')
    print(f'    Risk flags: {', '.join(flags)}')
    print('')

high_conf = sum(1 for _, t, c in tickets if intake_risk_pipeline(RawTicket(original_text=t, submitted_at=datetime.utcnow(), customer_id=c)).classification.confidence >= 0.6)
print(f'  SUMMARY: {len(tickets)} tickets processed, {high_conf} auto-sendable, {len(tickets) - high_conf} need human review')
" 2>&1

# 5. Optional dashboard
echo ""
echo "[5/5] Demo complete!"
echo ""
read -p "Launch Streamlit dashboard? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Launching dashboard..."
    uv run streamlit run src/ticketpilot/review/console.py --server.port 8501
fi
