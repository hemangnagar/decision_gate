from __future__ import annotations

import argparse
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .demo import DEMO_CONTEXT, DEMO_DECISION, DemoAdversary, DemoBuilder
from .providers import LiteLLMProvider
from .runner import run_review


class DecisionGateHandler(SimpleHTTPRequestHandler):
    web_dir: Path = Path(__file__).resolve().parents[2] / "web"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(self.web_dir), **kwargs)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/demo":
            self._json(200, {"decision": DEMO_DECISION, "context": DEMO_CONTEXT})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/review":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            mode = data.get("mode", "demo")
            decision = str(data.get("decision") or "")
            context = str(data.get("context") or "")
            max_rounds = max(1, min(int(data.get("max_rounds", 3)), 5))

            if mode == "demo":
                # The canned providers only make sense for the fixed example.
                decision, context = DEMO_DECISION, DEMO_CONTEXT
                builder, adversary = DemoBuilder(), DemoAdversary()
            else:
                builder_model = str(data.get("builder_model") or os.getenv("DECISION_GATE_BUILDER_MODEL", ""))
                adversary_model = str(data.get("adversary_model") or os.getenv("DECISION_GATE_ADVERSARY_MODEL", ""))
                if not builder_model or not adversary_model:
                    raise ValueError("builder_model and adversary_model are required in live mode")
                builder = LiteLLMProvider(builder_model)
                adversary = LiteLLMProvider(adversary_model)

            ledger = run_review(
                decision=decision,
                context=context,
                builder=builder,
                adversary=adversary,
                max_rounds=max_rounds,
            )
            ledger["mode"] = mode
            self._json(200, ledger)
        except Exception as exc:
            self._json(400, {"error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(prog="decision-gate-web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DecisionGateHandler)
    print(f"Decision Gate running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
