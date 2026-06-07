#!/usr/bin/env python3
"""Calibrate confidence scores using reflection data from Sprint 1.

Runs the pipeline on eval tickets, uses self-reflection to determine
whether drafts are correct, then trains an IsotonicCalibrator.

Outputs:
  - 校准器训练完成: XX 个数据点
  - 校准前 ECE: X.XX
  - 校准后 ECE: X.XX
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

EVAL_CSV = Path(__file__).resolve().parent.parent / "data" / "eval" / "tickets_eval.csv"
SKILL_LIBRARY_PATH = Path(__file__).resolve().parent.parent / "data" / "skills" / "library.json"
OUTPUT_MODEL = Path(__file__).resolve().parent.parent / "data" / "calibration" / "isotonic_model.json"


def load_tickets(csv_path: Path) -> list[dict]:
    """Load all tickets from eval CSV."""
    tickets: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickets.append(row)
    return tickets


def main() -> None:
    from ticketpilot.schema.ticket import RawTicket
    from ticketpilot.pipeline import intake_risk_pipeline
    from ticketpilot.drafting.generator import generate_draft
    from ticketpilot.skills.loader import load_skill_library, select_relevant_skills
    from ticketpilot.skills.reflector import reflect_on_draft
    from ticketpilot.skills.schema import SkillPattern
    from ticketpilot.feedback.calibrator import (
        IsotonicCalibrator,
        CalibrationCurve,
    )
    from ticketpilot.feedback.collector import FeedbackRecord

    # Load skill library
    library = load_skill_library(str(SKILL_LIBRARY_PATH))

    # Load tickets
    tickets_data = load_tickets(EVAL_CSV)
    print(f"Loaded {len(tickets_data)} tickets for calibration")

    # Default skill for intents without a matching skill
    default_skill = SkillPattern(
        skill_id="default",
        intent="other",
        name="default",
        description="Default skill",
        keywords=[],
        resolution_steps=[],
        risk_flags_to_acknowledge=[],
        tone="professional",
    )

    # Collect calibration data: (predicted_confidence, reflection_passed)
    calibration_points: list[tuple[float, bool]] = []

    for row in tickets_data:
        raw = RawTicket(
            original_text=row["original_text"],
            submitted_at=datetime.now(timezone.utc),
            customer_id=row.get("customer_id", ""),
        )

        # Pipeline
        ticket_output = intake_risk_pipeline(raw)
        draft_result = generate_draft(ticket_output)
        draft = draft_result.draft

        # Select skill
        intent = ticket_output.classification.intent.value
        risk_flag_strs = [f.value for f in ticket_output.risk_assessment.flags]
        skills = select_relevant_skills(library, intent, risk_flag_strs, top_k=1)
        skill = skills[0] if skills else default_skill

        # Reflect
        reflection = reflect_on_draft(draft.draft_text, skill, risk_flag_strs)

        # Confidence from draft
        confidence = draft.confidence
        passed = reflection.passed

        calibration_points.append((confidence, passed))

    print(f"Collected {len(calibration_points)} calibration data points")

    # Build FeedbackRecord list for CalibrationCurve (before calibration)
    feedback_records: list[FeedbackRecord] = []
    for conf, passed in calibration_points:
        feedback_records.append(
            FeedbackRecord(
                ticket_id="calibration",
                predicted_confidence=conf,
                confidence_level="high" if conf > 0.8 else "medium" if conf > 0.6 else "low",
                review_action="approve" if passed else "edit",
                was_correct=passed,
                original_draft="",
            )
        )

    # ECE before calibration
    curve_before = CalibrationCurve.build(feedback_records)
    ece_before = curve_before.ece()

    # Fit isotonic calibrator
    calibrator = IsotonicCalibrator()
    calibrator.fit(feedback_records)

    # Compute calibrated confidences and build new FeedbackRecords
    calibrated_records: list[FeedbackRecord] = []
    for conf, passed in calibration_points:
        calibrated_conf = calibrator.calibrate(conf)
        calibrated_records.append(
            FeedbackRecord(
                ticket_id="calibration",
                predicted_confidence=calibrated_conf,
                confidence_level="high" if calibrated_conf > 0.8 else "medium" if calibrated_conf > 0.6 else "low",
                review_action="approve" if passed else "edit",
                was_correct=passed,
                original_draft="",
            )
        )

    # ECE after calibration
    curve_after = CalibrationCurve.build(calibrated_records)
    ece_after = curve_after.ece()

    # Save model
    calibrator.save(str(OUTPUT_MODEL))

    # Output
    print(f"✅ 校准器训练完成: {len(calibration_points)} 个数据点")
    print(f"校准前 ECE: {ece_before:.4f}")
    print(f"校准后 ECE: {ece_after:.4f}")
    if ece_after <= ece_before:
        print("✅ 校准后 ECE <= 校准前 ECE")
    else:
        print("⚠️  校准后 ECE > 校准前 ECE (数据量不足或分布特殊)")

    # ASCII reliability diagram
    from ticketpilot.feedback.calibrator import ReliabilityDiagram

    diagram = ReliabilityDiagram.build(feedback_records)
    print()
    print(diagram.to_ascii())


if __name__ == "__main__":
    main()
