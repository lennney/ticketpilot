"""CLI trigger for TicketPilot pipeline.

Allows triggering the pipeline from command line with raw ticket text.

Usage:
    python -m ticketpilot.triggers.cli "Customer complaint about late delivery"
    python -m ticketpilot.triggers.cli --file ticket.txt
    echo "Refund request" | python -m ticketpilot.triggers.cli --stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Trigger TicketPilot pipeline from CLI",
        prog="ticketpilot-cli",
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "text",
        nargs="?",
        help="Raw ticket text",
    )
    input_group.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Read ticket text from file",
    )
    input_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read ticket text from stdin",
    )

    # Output options
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write output to file",
    )

    # Pipeline options
    parser.add_argument(
        "--customer-id",
        help="Customer ID",
    )

    return parser.parse_args(argv)


def get_ticket_text(args: argparse.Namespace) -> str:
    """Get ticket text from the specified source."""
    if args.text:
        return args.text
    elif args.file:
        return args.file.read_text(encoding="utf-8").strip()
    elif args.stdin:
        return sys.stdin.read().strip()
    else:
        raise ValueError("No input source specified")


def format_output(
    result: dict,
    as_json: bool = False,
    pretty: bool = False,
) -> str:
    """Format pipeline output for display."""
    if as_json:
        indent = 2 if pretty else None
        return json.dumps(result, indent=indent, ensure_ascii=False, default=str)

    # Human-readable format
    lines = [
        "=" * 60,
        "TicketPilot Pipeline Result",
        "=" * 60,
        f"Ticket ID: {result.get('ticket_id', 'N/A')}",
        f"Intent: {result.get('classification', {}).get('intent', 'N/A')}",
        f"Risk: {result.get('risk_assessment', {}).get('risk_level', 'N/A')}",
        "-" * 60,
        "Classification:",
        f"  Confidence: {result.get('classification', {}).get('confidence', 0):.2%}",
        f"  Reasoning: {result.get('classification', {}).get('reasoning', 'N/A')}",
        "-" * 60,
        "Evidence:",
        f"  Chunks found: {len(result.get('evidence', []))}",
    ]

    # Add evidence summary
    for i, ev in enumerate(result.get("evidence", [])[:3], 1):
        lines.append(
            f"  [{i}] {ev.get('doc_type', 'N/A')}: {ev.get('content', '')[:80]}..."
        )

    lines.extend(
        [
            "-" * 60,
            "Draft Reply:",
            f"  {result.get('draft', {}).get('text', 'N/A')[:200]}...",
            "-" * 60,
            "Confidence:",
            f"  Overall: {result.get('confidence', {}).get('overall', 0):.2%}",
            f"  Level: {result.get('confidence', {}).get('level', 'N/A')}",
            "-" * 60,
            "Degradation:",
            f"  Strategy: {result.get('degraded_response', {}).get('strategy', 'N/A')}",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)

    try:
        # Get ticket text
        text = get_ticket_text(args)
        if not text:
            print("Error: Empty ticket text", file=sys.stderr)
            return 1

        # Create RawTicket
        raw_ticket = RawTicket(
            original_text=text,
            submitted_at=datetime.now(),
            customer_id=args.customer_id,
        )

        # Run pipeline
        result = intake_risk_pipeline(raw_ticket)

        # Format output
        output = format_output(
            result.model_dump(),
            as_json=args.json,
            pretty=args.pretty,
        )

        # Write output
        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
