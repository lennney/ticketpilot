"""CLI entry-point for offline evaluation.

Provides parse_args() for argument parsing and run_eval() for executing
the full evaluation pipeline: load tickets, golden expectations, and
predictions from CSV, compute metrics, and write JSON + Markdown reports.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project src is on the path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the evaluation runner.

    Args:
        argv: List of argument strings. Defaults to sys.argv[1:].

    Returns:
        Parsed argparse.Namespace with attributes: tickets, golden,
        predictions, out_json, out_md, prediction_mode.
    """
    parser = argparse.ArgumentParser(
        description="Run offline evaluation: compare predictions against golden expectations.",
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
        help="Path to predictions CSV (required when --prediction-mode=file)",
    )
    parser.add_argument(
        "--prediction-mode",
        choices=["file", "pipeline"],
        default="file",
        help="How to generate predictions: 'file' loads from --predictions CSV, 'pipeline' runs the live pipeline (default: file)",
    )
    parser.add_argument(
        "--out-json",
        required=True,
        help="Path to write the JSON report",
    )
    parser.add_argument(
        "--out-md",
        required=True,
        help="Path to write the Markdown report",
    )
    args = parser.parse_args(argv)

    # Validate: --predictions required when mode is 'file'
    if args.prediction_mode == "file" and not args.predictions:
        parser.error("--predictions is required when --prediction-mode=file")

    return args


def _generate_pipeline_predictions(tickets_path: str, golden_path: str) -> dict:
    """Generate predictions by running the live pipeline on eval tickets."""
    from ticketpilot.evaluation.loaders import load_eval_dataset
    from ticketpilot.evaluation.pipeline_predictions import predict_from_pipeline

    load_result = load_eval_dataset(tickets_path, golden_path)
    if not load_result.is_valid:
        print(f"Error loading eval dataset: {load_result.errors}", file=sys.stderr)
        sys.exit(1)

    predictions = {}
    for ticket in load_result.dataset.tickets.values():
        pred = predict_from_pipeline(ticket)
        predictions[pred.case_id] = pred

    return predictions


def run_eval(args: argparse.Namespace) -> None:
    """Execute the evaluation pipeline with the given parsed arguments.

    Validates inputs, loads data, computes metrics, writes reports.
    Exits with code != 0 on validation failure.

    Args:
        args: Parsed namespace from parse_args().
    """
    from ticketpilot.evaluation import loaders, metrics, predictions, reporting

    prediction_mode = getattr(args, "prediction_mode", "file")

    # Validate input files exist
    files_to_check = [("tickets", args.tickets), ("golden", args.golden)]
    if prediction_mode == "file":
        files_to_check.append(("predictions", args.predictions))

    for label, path in files_to_check:
        if not Path(path).exists():
            print(f"Error: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Load dataset
    load_result = loaders.load_eval_dataset(args.tickets, args.golden)
    if not load_result.is_valid:
        for err in load_result.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    # Load or generate predictions
    if prediction_mode == "pipeline":
        preds = _generate_pipeline_predictions(args.tickets, args.golden)
        predictions_path = "pipeline"
    else:
        try:
            preds = predictions.load_predictions(args.predictions)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error loading predictions: {exc}", file=sys.stderr)
            sys.exit(1)
        predictions_path = args.predictions

    # Validate predictions against golden
    try:
        summary = metrics.compute_evaluation_summary(
            preds, load_result.dataset.golden
        )
    except ValueError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Write reports
    reporting.write_json_report(
        summary,
        args.out_json,
        tickets_path=args.tickets,
        golden_path=args.golden,
        predictions_path=predictions_path,
        prediction_mode="csv" if prediction_mode == "file" else prediction_mode,
    )
    reporting.write_markdown_report(
        summary,
        args.out_md,
        tickets_path=args.tickets,
        golden_path=args.golden,
        predictions_path=predictions_path,
        prediction_mode="csv" if prediction_mode == "file" else prediction_mode,
    )
    print(f"Reports written: {args.out_json}, {args.out_md}")


def main() -> None:
    """CLI entry-point."""
    args = parse_args()
    run_eval(args)


if __name__ == "__main__":
    main()
