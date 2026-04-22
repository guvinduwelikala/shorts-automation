from __future__ import annotations

import json
import threading
import traceback
import uuid
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent
HTML_FILE = BASE_DIR / "ui.html"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
PORT_SCAN_LIMIT = 20


@dataclass
class JobState:
    status: str = "running"
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None

    def append(self, text: str) -> None:
        if not text:
            return
        self.logs.append(text)

    def render_logs(self) -> str:
        return "".join(self.logs)


class JobStream:
    def __init__(self, job: JobState) -> None:
        self.job = job
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        if "\n" in self._buffer:
            chunks = self._buffer.split("\n")
            self._buffer = chunks.pop()
            for chunk in chunks:
                self.job.append(chunk + "\n")
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self.job.append(self._buffer)
            self._buffer = ""


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "ShortsAutomationUI/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    @property
    def jobs(self) -> dict[str, JobState]:
        return self.server.jobs  # type: ignore[attr-defined]

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, html: str, status: int = 200) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON body") from exc

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            html = HTML_FILE.read_text(encoding="utf-8")
            self._send_html(html)
            return

        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self._send_cors_headers()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if parsed.path == "/api/health":
            self._send_json({"ok": True, "status": "ready"})
            return

        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = self.jobs.get(job_id)
            if job is None:
                self._send_json({"error": "Job not found"}, status=404)
                return

            self._send_json(
                {
                    "job_id": job_id,
                    "status": job.status,
                    "logs": job.render_logs(),
                    "result": job.result,
                    "error": job.error,
                }
            )
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            topic = str(payload.get("topic", "")).strip()
            privacy = str(payload.get("privacy", "public")).strip()
            if not topic:
                self._send_json({"error": "Topic is required"}, status=400)
                return
            if privacy not in {"public", "private", "unlisted"}:
                self._send_json({"error": "Invalid privacy setting"}, status=400)
                return

            job_id = uuid.uuid4().hex[:8]
            job = JobState()
            job.append("Starting Shorts pipeline...\n")
            job.append(f"Topic: {topic}\n")
            job.append(f"Privacy: {privacy}\n\n")
            self.jobs[job_id] = job

            thread = threading.Thread(
                target=self.server.run_pipeline,  # type: ignore[attr-defined]
                args=(job_id, topic, privacy),
                daemon=True,
            )
            thread.start()
            self._send_json({"job_id": job_id})
            return

        self._send_json({"error": "Not found"}, status=404)


class UIService(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], RequestHandlerClass: type[RequestHandler]):
        super().__init__(server_address, RequestHandlerClass)
        self.jobs: dict[str, JobState] = {}

    def run_pipeline(self, job_id: str, topic: str, privacy: str) -> None:
        job = self.jobs[job_id]
        stream = JobStream(job)

        try:
            from contextlib import redirect_stderr, redirect_stdout

            from run import run as run_pipeline

            with redirect_stdout(stream), redirect_stderr(stream):
                run_pipeline(topic=topic, privacy=privacy)
                stream.flush()

            job.status = "completed"
            job.append("\nPipeline complete.\n")
            job.result = {"message": "Pipeline completed successfully"}
        except Exception:
            stream.flush()
            job.status = "error"
            job.error = traceback.format_exc()
            job.append("\nPipeline failed.\n")
            job.append(job.error + "\n")


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server, selected_port = _create_server(host, port)
    url = f"http://{host}:{selected_port}/"
    print(f"Starting web UI at {url}")
    if selected_port != port:
        print(f"Port {port} was busy. Switched to port {selected_port}.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("Press Ctrl+C to stop the server.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()


def _create_server(host: str, preferred_port: int) -> tuple[UIService, int]:
    for candidate_port in range(preferred_port, preferred_port + PORT_SCAN_LIMIT):
        try:
            return UIService((host, candidate_port), RequestHandler), candidate_port
        except OSError as exc:
            # Address-in-use signatures across platforms.
            is_addr_in_use = (
                getattr(exc, "errno", None) in {98, 48}
                or getattr(exc, "winerror", None) == 10048
                or "address already in use" in str(exc).lower()
                or "only one usage of each socket address" in str(exc).lower()
            )
            if not is_addr_in_use:
                raise

    end_port = preferred_port + PORT_SCAN_LIMIT - 1
    raise RuntimeError(
        f"Unable to start UI server. Ports {preferred_port}-{end_port} are unavailable."
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Launch the Shorts automation web UI")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    main(host=args.host, port=args.port)
