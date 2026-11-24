"""Local demo server (stdlib only): serves demo/web/index.html and a small JSON API over demo/core.py.
    uv run python demo/server.py            → http://localhost:8502
"""
from __future__ import annotations

import base64
import csv
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core

DEMO = Path(__file__).resolve().parent
SAMPLES, WEB, LOG = DEMO / "samples", DEMO / "web", DEMO / "choices.csv"
FILES = sorted(p.name for p in SAMPLES.iterdir() if p.suffix in {".jpg", ".png"})
LOCK = threading.Lock()  # Grad-CAM hooks on one shared model: one analysis at a time
TYPES = {".html": "text/html; charset=utf-8", ".jpg": "image/jpeg", ".png": "image/png"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(json.dumps(obj).encode(), "application/json", code)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send((WEB / "index.html").read_bytes(), TYPES[".html"])
        if self.path == "/api/samples":
            return self._json([{"id": i, "file": f, "truth": f.split("__")[0], "truth_label": core.nice(f.split("__")[0])}
                               for i, f in enumerate(FILES)])
        if self.path.startswith("/samples/"):
            name = Path(self.path.removeprefix("/samples/")).name  # no directory traversal
            path = SAMPLES / name
            if path.is_file():
                return self._send(path.read_bytes(), TYPES.get(path.suffix, "application/octet-stream"))
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > 10_000_000:
            return self._json({"error": "too large"}, 413)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        if self.path == "/api/analyse":
            if "file" in body:
                name = Path(str(body["file"])).name
                crop = cv2.imread(str(SAMPLES / name)) if name in FILES else None
            else:
                raw = base64.b64decode(str(body.get("data", "")).split(",")[-1] or b"")
                crop = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) if raw else None
            if crop is None:
                return self._json({"error": "could not read the image"}, 400)
            with LOCK:
                result = core.analyse(crop)
            return self._json(result)
        if self.path == "/api/decide":
            new = not LOG.exists()
            with LOG.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["wall_time", "image", "model_top", "p_top", "choice", "gcode"])
                w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), body.get("image", ""), body.get("top", ""),
                            body.get("p_top", ""), body.get("choice", ""), body.get("gcode") or ""])
            return self._json({"ok": True, "time": time.strftime("%H:%M:%S")})
        self._json({"error": "not found"}, 404)

    def log_message(self, *_):  # keep the console quiet
        pass


if __name__ == "__main__":
    core.model_and_cfg()  # load + warm up before the first request
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8502
    print(f"demo on http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
