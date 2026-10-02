"""Maps the progress inside each step of a job onto one overall fraction 0..1."""
from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

Emit = Callable[[float, str], None]


class Stages:
    def __init__(self, emit: Emit, weights: list[tuple[str, float]]):
        self.emit = emit
        self.weights = weights
        self.total = float(sum(w for _, w in weights)) or 1.0
        self.base = 0.0
        self.span = 0.0
        self.msg = ""

    def start(self, i: int, msg: str) -> None:
        self.msg = msg
        self.base = sum(w for _, w in self.weights[:i]) / self.total
        self.span = self.weights[i][1] / self.total
        self.emit(self.base, msg)

    def inner(self, f: float) -> None:
        self.emit(self.base + self.span * min(max(f, 0.0), 1.0), self.msg)

    def timed(self, fn: Callable, est_s: float):
        """Run fn() for a step that cannot report progress; estimate it from the elapsed time."""
        done = threading.Event()

        def tick():
            t0 = time.perf_counter()
            while not done.wait(0.1):
                self.inner(0.95 * (1.0 - math.exp(-(time.perf_counter() - t0) / est_s)))

        threading.Thread(target=tick, daemon=True).start()
        try:
            return fn()
        finally:
            done.set()
