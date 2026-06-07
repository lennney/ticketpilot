"""Launch the TicketPilot Dashboard."""

import subprocess
import sys


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/ticketpilot/dashboard/app.py",
            "--server.port",
            "8501",
            "--server.headless",
            "true",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
