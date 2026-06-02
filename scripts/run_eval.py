"""TicketPilot evaluation using DeepEval."""
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))


def _read_env():
    env_path = project_root / ".env.local"
    key, base = "", "https://api.deepseek.com"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                s = line.strip()
                if s.startswith("TICKETPILOT_LLM_API_KEY="):
                    key = s.split("=", 1)[1]
                elif s.startswith("TICKETPILOT_LLM_BASE_URL="):
                    base = s.split("=", 1)[1]
    return key, base


_api_key, _api_base = _read_env()
os.environ["OPENAI_API_KEY"] = _api_key


def run_evaluation():
    from deepeval import evaluate
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.models.llms.openai_model import GPTModel
    from deepeval.test_case import LLMTestCase

    eval_path = project_root / "data/knowledge/external/deepeval_generated.json"
    with open(eval_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} items", flush=True)

    import random
    random.seed(42)
    sample = random.sample(data, min(30, len(data)))

    test_cases = []
    for item in sample:
        tc = LLMTestCase(
            input=item["instruction"],
            actual_output=item["response"],
            expected_output=item["response"],
            retrieval_context=[item["response"]],
        )
        test_cases.append(tc)
    print(f"Created {len(test_cases)} test cases", flush=True)

    judge = GPTModel(model="deepseek-chat", base_url=_api_base, api_key=_api_key)
    metrics = [
        FaithfulnessMetric(threshold=0.7, model=judge),
        AnswerRelevancyMetric(threshold=0.7, model=judge),
    ]

    print("Running DeepEval...", flush=True)
    result = evaluate(test_cases=test_cases, metrics=metrics)

    os.makedirs(str(project_root / "reports/eval"), exist_ok=True)
    report_path = project_root / "reports/eval/deepeval_report.json"

    metric_scores = {}
    for tr in result.test_results:
        for mr in tr.metrics_data:
            name = mr.name
            if name not in metric_scores:
                metric_scores[name] = {"scores": [], "passed": 0, "total": 0}
            metric_scores[name]["scores"].append(mr.score)
            metric_scores[name]["total"] += 1
            if mr.success:
                metric_scores[name]["passed"] += 1

    report = {"total_test_cases": len(test_cases), "metrics": {}}
    for name, info in metric_scores.items():
        avg = sum(info["scores"]) / len(info["scores"])
        report["metrics"][name] = {
            "average_score": round(avg, 4),
            "pass_rate": f"{info['passed'] / info['total'] * 100:.1f}%",
            "total": info["total"],
        }

    with open(str(report_path), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report -> {report_path}", flush=True)
    print("Done!", flush=True)


if __name__ == "__main__":
    run_evaluation()
