"""Webhook receiver for TicketPilot pipeline.

Allows triggering the pipeline via HTTP webhooks.

Usage:
    # Start webhook server
    python -m ticketpilot.triggers.webhook --port 8080

    # Send webhook
    curl -X POST http://localhost:8080/webhook/ticket \
        -H "Content-Type: application/json" \
        -d '{"text": "Customer complaint about late delivery"}'
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket


class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for webhook requests."""

    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/webhook/ticket":
            self._handle_ticket_webhook()
        elif self.path == "/webhook/health":
            self._handle_health()
        else:
            self._send_error(404, "Not found")

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        else:
            self._send_error(404, "Not found")

    def _handle_ticket_webhook(self):
        """Handle ticket processing webhook."""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_error(400, "Empty request body")
                return

            body = self.rfile.read(content_length)
            data = json.loads(body)

            # Validate required fields
            if "text" not in data:
                self._send_error(400, "Missing required field: text")
                return

            # Create RawTicket
            raw_ticket = RawTicket(
                original_text=data["text"],
                submitted_at=datetime.now(),
                customer_id=data.get("customer_id"),
            )

            # Run pipeline
            result = intake_risk_pipeline(raw_ticket)

            # Send response
            self._send_json(200, {
                "status": "success",
                "ticket_id": result.ticket_id,
                "result": result.model_dump(),
            })

        except json.JSONDecodeError as e:
            self._send_error(400, f"Invalid JSON: {e}")
        except Exception as e:
            self._send_error(500, f"Pipeline error: {e}")

    def _handle_health(self):
        """Handle health check."""
        self._send_json(200, {"status": "healthy"})

    def _send_json(self, status: int, data: dict[str, Any]):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _send_error(self, status: int, message: str):
        """Send error response."""
        self._send_json(status, {"status": "error", "message": message})

    def log_message(self, format, *args):
        """Override to reduce log noise."""
        pass


def run_server(port: int = 8080, host: str = "0.0.0.0"):
    """Start webhook server."""
    server = HTTPServer((host, port), WebhookHandler)
    print(f"Webhook server started on {host}:{port}")
    print(f"Endpoints:")
    print(f"  POST /webhook/ticket - Process ticket")
    print(f"  GET  /health        - Health check")
    print(f"  POST /webhook/health - Health check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="TicketPilot webhook server")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", "-H", default="0.0.0.0", help="Host to bind to")

    args = parser.parse_args()
    run_server(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
