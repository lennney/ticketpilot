"""Run optimizer with LLM approval enabled."""
import os
import sys

# LLM config from environment variables
os.environ.setdefault("OPTIMIZER_LLM_BASE_URL", "https://opencode.ai/zen/go/v1")
os.environ.setdefault("OPTIMIZER_LLM_MODEL", "deepseek-v4-flash")

key = os.environ.get("OPTIMIZER_LLM_API_KEY", "")
if not key:
    print("Error: OPTIMIZER_LLM_API_KEY environment variable is not set")
    sys.exit(1)

# Now run the optimizer
from ticketpilot.optimizer.engine import OptimizationEngine

engine = OptimizationEngine(max_rounds=5)
sys.exit(0 if engine.run() else 1)
