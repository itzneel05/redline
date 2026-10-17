"""A tiny local web UI.

No framework, no build step: one page, three static files, and a single JSON
endpoint. The server binds to 127.0.0.1 only, so a confidential contract is
never exposed to the network.
"""

from __future__ import annotations

import argparse
import json
import os
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import analyze
from .llm import DEFAULT_MODEL, ModelError, OllamaModel

STATIC_DIR = Path(__file__).parent / "static"
_MAX_BODY = 2_000_000  # 2 MB of contract text is plenty

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}


def make_handler(model_factory: Callable[[], object]):
    """Build a request handler bound to a model factory (injected for tests)."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "Redline"

        def log_message(self, *args: object) -> None:  # noqa: D102 - quiet console
            pass

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: dict) -> None:
            self._send(
                status,
                json.dumps(payload).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def _static(self, name: str) -> None:
            root = STATIC_DIR.resolve()
            path = (root / name).resolve()
            if root not in path.parents:
                self._send(403, b"forbidden", "text/plain; charset=utf-8")
                return
            if not path.is_file():
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            content_type = _CONTENT_TYPES.get(path.suffix, "application/octet-stream")
            self._send(200, path.read_bytes(), content_type)

        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            route = self.path.split("?", 1)[0]
            if route in ("/", "/index.html"):
                self._static("index.html")
            elif route.startswith("/static/"):
                self._static(route[len("/static/") :])
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802 - stdlib naming
            if self.path.split("?", 1)[0] != "/api/analyze":
                self._send_json(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > _MAX_BODY:
                self._send_json(413, {"error": "contract too large or empty"})
                return
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._send_json(400, {"error": "invalid JSON body"})
                return
            contract = (body or {}).get("text", "")
            if not isinstance(contract, str) or not contract.strip():
                self._send_json(400, {"error": "no contract text provided"})
                return

            try:
                model = model_factory()
            except Exception:  # noqa: BLE001 - degrade to built-in checks
                model = None

            report = analyze.analyze(contract, model=model)
            payload = report.to_dict()
            if body.get("email") and model is not None:
                try:
                    payload["email"] = analyze.draft_email(report, model)
                except ModelError as exc:
                    payload.setdefault("warnings", []).append(str(exc))
            self._send_json(200, payload)

    return Handler


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    model_factory: Callable[[], object] | None = None,
) -> ThreadingHTTPServer:
    """Create (but do not start) the local HTTP server."""
    if model_factory is None:
        model_factory = OllamaModel
    return ThreadingHTTPServer((host, port), make_handler(model_factory))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="redline-web", description="Local web UI for Redline.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--model",
        default=os.environ.get("REDLINE_MODEL", DEFAULT_MODEL),
        help=f"Ollama model to use (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser.")
    args = parser.parse_args(argv)

    httpd = serve(
        host=args.host,
        port=args.port,
        model_factory=lambda: OllamaModel(model=args.model),
    )
    url = f"http://{args.host}:{httpd.server_address[1]}/"
    print(f"Redline is listening on {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
