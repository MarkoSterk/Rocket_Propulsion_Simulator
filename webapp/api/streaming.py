"""Run a job in a worker thread and stream its progress to the browser as NDJSON.

Every line is one JSON object: {"type": "progress", "f": 0..1, "msg": ...}, then either
{"type": "result", "data": ...} or {"type": "error", "error": ...}.
"""
from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable

from flask import Response

from ..services.progress import Emit


def stream_job(job: Callable[[Emit], dict]) -> Response:
    messages: queue.Queue = queue.Queue()

    def emit(fraction: float, msg: str) -> None:
        messages.put({"type": "progress", "f": round(min(max(fraction, 0.0), 1.0), 4), "msg": msg})

    def worker() -> None:
        try:
            messages.put({"type": "result", "data": job(emit)})
        except Exception as exc:  # noqa: BLE001
            messages.put({"type": "error", "error": str(exc)})
        finally:
            messages.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def lines():
        while True:
            item = messages.get()
            if item is None:
                break
            yield json.dumps(item, separators=(",", ":"), default=float) + "\n"

    return Response(lines(), mimetype="application/x-ndjson",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
