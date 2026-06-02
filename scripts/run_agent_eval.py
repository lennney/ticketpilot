#!/usr/bin/env python3
"""
Run agent evaluation using the new evaluation framework.

Usage:
    python scripts/run_agent_eval.py
    python scripts/run_agent_eval.py --dataset data/eval/agent_eval_dataset.json
    python scripts/run_agent_eval.py --output reports/eval/
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ticketpilot.evaluation.agent_eval import (
    EvalDataset,
    EvalReport,
    run_evaluation,
)
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from ticketpilot.drafting.draft_agent import DraftAgent
from datetime import datetime


def agent_fn(input_text: str) -> tuple[str, str]:
    """Agent function for evaluation."""
    # Create raw ticket
    raw_ticket = RawTicket(
        original_text=input_text,
        submitted_at=datetime.utcnow(),
    )
    
    # Run pipeline
    ticket_output = intake_risk_pipeline(raw_ticket)
    
    # Generate draft
    agent = DraftAgent()
    draft = agent.generate_draft(
        normalized_text=ticket_output.normalized_ticket.text,
        issue_type=ticket_output.classification.intent.value,
        risk_flags=[f.value for f in ticket_output.risk_assessment.flags],
        severity=ticket_output.risk_assessment.severity.value,
        must_human_review=ticket_output.risk_assessment.must_human_review,
        evidence_candidates=ticket_output.evidence_candidates,
    )
    
    return draft.draft_text, ticket_output.classification.intent.value


def main():
    parser = argparse.ArgumentParser(description="Run agent evaluation")
    parser.add_argument("--dataset", default="data/eval/agent_eval_dataset.json",
                       help="Path to evaluation dataset")
    parser.add_argument("--output", default="reports/eval",
                       help="Output directory for reports")
    parser.add_argument("--threshold", type=float, default=0.7,
                       help="Pass threshold")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  TicketPilot Agent Evaluation")
    print("=" * 60)
    
    # Load dataset
    dataset = EvalDataset()
    dataset.load(args.dataset)
    print(f"\n加载 {len(dataset.cases)} 个评估用例")
    
    # Run evaluation
    print("\n运行评估...")
    report = run_evaluation(
        dataset=dataset,
        agent_fn=agent_fn,
        pass_threshold=args.threshold,
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("  评估结果")
    print("=" * 60)
    print(f"总用例: {report.total_cases}")
    print(f"通过: {report.passed_cases}")
    print(f"失败: {report.failed_cases}")
    print(f"通过率: {report.pass_rate:.1%}")
    print(f"意图准确率: {report.intent_accuracy:.1%}")
    print(f"平均忠实度: {report.avg_faithfulness:.3f}")
    print(f"平均相关性: {report.avg_relevancy:.3f}")
    print(f"平均耗时: {report.avg_duration_ms:.0f}ms")
    
    # Print individual results
    print("\n详细结果:")
    print("-" * 60)
    for r in report.results:
        status = "✓" if r.intent_correct else "✗"
        print(f"{status} {r.case_id}: intent={r.actual_intent}, "
              f"faith={r.faithfulness_score:.2f}, "
              f"rel={r.relevancy_score:.2f}, "
              f"citations={r.has_citations}")
    
    # Save report
    output_path = report.save(args.output)
    print(f"\n报告已保存: {output_path}")
    
    return report


if __name__ == "__main__":
    main()
