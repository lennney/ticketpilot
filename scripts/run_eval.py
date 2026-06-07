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
        predictions, out_json, out_md.
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
        required=True,
        help="Path to predictions CSV",
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
    return parser.parse_args(argv)


def run_eval(args: argparse.Namespace) -> None:
    """Execute the evaluation pipeline with the given parsed arguments.

    Validates inputs, loads data, computes metrics, writes reports.
    Exits with code != 0 on validation failure.

    Args:
        args: Parsed namespace from parse_args().
    """
    from ticketpilot.evaluation import loaders, metrics, predictions, reporting

    # Validate input files exist
    for label, path in [
        ("tickets", args.tickets),
        ("golden", args.golden),
        ("predictions", args.predictions),
    ]:
        if not Path(path).exists():
            print(f"Error: {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # Load dataset
    load_result = loaders.load_eval_dataset(args.tickets, args.golden)
    if not load_result.is_valid:
        for err in load_result.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    # Load predictions
    try:
        preds = predictions.load_predictions(args.predictions)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading predictions: {exc}", file=sys.stderr)
        sys.exit(1)

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
        predictions_path=args.predictions,
    )
    reporting.write_markdown_report(
        summary,
        args.out_md,
        tickets_path=args.tickets,
        golden_path=args.golden,
        predictions_path=args.predictions,
    )
    print(f"Reports written: {args.out_json}, {args.out_md}")


def main() -> None:
    """CLI entry-point."""
    args = parse_args()
    run_eval(args)


if __name__ == "__main__":
    main()
