"""Entry point: python -m ticketpilot.optimizer"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TicketPilot Auto-Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python -m ticketpilot.optimizer              # Run 20 rounds
  python -m ticketpilot.optimizer --rounds 5   # Run 5 rounds
  python -m ticketpilot.optimizer --diagnose-only  # Diagnose only
  python -m ticketpilot.optimizer --dry-run    # Simulate only
  python -m ticketpilot.optimizer --continue   # Resume from last run
  python -m ticketpilot.optimizer --history    # Show past runs
""",
    )
    parser.add_argument("--rounds", type=int, default=20, help="Max optimization rounds (default: 20)")
    parser.add_argument("--diagnose-only", action="store_true", help="Run diagnosis only, no fixes")
    parser.add_argument("--continue", dest="continue_run", action="store_true", help="Resume from last iteration")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without modifying files")
    parser.add_argument("--history", action="store_true", help="Show optimization history")
    args = parser.parse_args()

    # Lazy import to avoid loading heavy deps on --help
    from ticketpilot.optimizer.engine import OptimizationEngine

    engine = OptimizationEngine(
        max_rounds=args.rounds,
        diagnose_only=args.diagnose_only,
        dry_run=args.dry_run,
        resume=args.continue_run,
    )

    if args.history:
        engine.show_history()
        return

    sys.exit(0 if engine.run() else 1)


if __name__ == "__main__":
    main()
