"""Run optimizer with LLM approval enabled."""
import os
import sys

# Set LLM config directly (avoid shell env export issues)
os.environ["OPTIMIZER_LLM_API_KEY"] = "REMOVED_KEY"
os.environ["OPTIMIZER_LLM_BASE_URL"] = "https://opencode.ai/zen/go/v1"
os.environ["OPTIMIZER_LLM_MODEL"] = "deepseek-v4-flash"

# Verify key length
key = os.environ["OPTIMIZER_LLM_API_KEY"]
print(f"API key length: {len(key)} (expect 67)")

# Now run the optimizer
from ticketpilot.optimizer.engine import OptimizationEngine

engine = OptimizationEngine(max_rounds=5)
sys.exit(0 if engine.run() else 1)
