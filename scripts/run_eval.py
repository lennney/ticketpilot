#!/usr/bin/env python
"""Offline evaluation CLI runner for TicketPilot.

Loads tickets, golden expectations, and predictions from CSV files,
computes deterministic metrics, and writes JSON and Markdown reports.

This script does NOT call the real TicketPilot pipeline, database,
LLM provider, or embedding provider. All computation is deterministic
and operates on in-memory objects only.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from ticketpilot.evaluation.loaders import load_eval_dataset
from ticketpilot.evaluation.metrics import compute_evaluation_summary
from ticketpilot.evaluation.predictions import load_predictions
from ticketpilot.evaluation.reporting import (
    write_json_report,
    write_markdown_report,
)


def die(msg: str, exit_code: int = 1) -> NoReturn:
    """Print an error message to stderr and exit with the given code."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(exit_code)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run offline evaluation of predictions against golden expectations."
    )
    parser.add_argument(
        "--tickets",
        required=True,
        help="Path to tickets_eval.csv",
    )
    parser.add_argument(
        "--golden",
        required=True,
        help="Path to golden_expectations.csv",
    )
    parser.add_argument(
        "--predictions",
        required=False,
        help="Path to predictions CSV file (required when --prediction-mode csv)",
    )
    parser.add_argument(
        "--prediction-mode",
        choices=["csv", "pipeline"],
        default="csv",
        help="Prediction source: 'csv' (default) loads from --predictions file, "
        "'pipeline' runs the local TicketPilot pipeline for each ticket",
    )
    parser.add_argument(
        "--out-json",
        required=True,
        help="Path for output JSON report",
    )
    parser.add_argument(
        "--out-md",
        required=True,
        help="Path for output Markdown report",
    )
    return parser.parse_args(argv)


def _load_or_generate_predictions(
    args: argparse.Namespace,
    dataset,
) -> dict:
    """Load predictions from CSV or generate from pipeline depending on mode."""
    if args.prediction_mode == "pipeline":
        from ticketpilot.evaluation.pipeline_predictions import (
            predict_from_pipeline,
        )

        predictions: dict = {}
        sorted_ids = sorted(dataset.tickets.keys())
        for case_id in sorted_ids:
            ticket = dataset.tickets[case_id]
            prediction = predict_from_pipeline(ticket)
            predictions[case_id] = prediction
        return predictions

    # CSV mode
    if not args.predictions:
        die("--predictions is required when --prediction-mode is csv")
    try:
        return load_predictions(args.predictions)
    except (FileNotFoundError, ValueError) as exc:
        die(str(exc))


def _predictions_source_label(args: argparse.Namespace) -> str:
    """Return a human-readable label for where predictions came from."""
    if args.prediction_mode == "pipeline":
        return "pipeline (generated from local TicketPilot pipeline)"
    return args.predictions or "unknown"


def run_eval(args: argparse.Namespace) -> None:
    """Load data, compute metrics, write reports."""
    load_result = load_eval_dataset(args.tickets, args.golden)
    if not load_result.is_valid:
        errors = load_result.errors[:]
        if load_result.missing_golden_for_ticket:
            for cid in load_result.missing_golden_for_ticket:
                errors.append(f"Ticket {cid!r} has no matching golden expectation")
        if load_result.missing_ticket_for_golden:
            for cid in load_result.missing_ticket_for_golden:
                errors.append(f"Golden expectation {cid!r} has no matching ticket")
        die("; ".join(errors))

    dataset = load_result.dataset

    predictions = _load_or_generate_predictions(args, dataset)

    try:
        summary = compute_evaluation_summary(predictions, dataset.golden)
    except ValueError as exc:
        die(str(exc))

    predictions_label = _predictions_source_label(args)

    write_json_report(
        summary,
        args.out_json,
        tickets_path=args.tickets,
        golden_path=args.golden,
        predictions_path=args.predictions or predictions_label,
        prediction_mode=args.prediction_mode,
    )
    print(f"JSON report written to {args.out_json}")

    write_markdown_report(
        summary,
        args.out_md,
        tickets_path=args.tickets,
        golden_path=args.golden,
        predictions_path=args.predictions or predictions_label,
        prediction_mode=args.prediction_mode,
    )
    print(f"Markdown report written to {args.out_md}")


def main() -> None:
    """Entry point for the CLI."""
    args = parse_args()
    run_eval(args)


if __name__ == "__main__":
    main()