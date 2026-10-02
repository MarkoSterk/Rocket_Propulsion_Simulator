"""Thread-safe LRU cache of grain cross-sections (numerical canals take about a second to build)."""
from __future__ import annotations

import json
import threading
from collections import OrderedDict

from srmsim import Grain, grain_from_dict

SEGMENT_KEYS = ("segments", "burning_faces", "segment_gap_mm")


class GrainCache:
    def __init__(self, max_size: int = 32, resolution: int = 501):
        self._max_size = max_size
        self._resolution = resolution
        self._items: OrderedDict[str, Grain] = OrderedDict()
        self._lock = threading.Lock()

    def key(self, grain_form: dict) -> str:
        """Cache key of the cross-section of one segment; stacking segments is cheap and done later."""
        data = {k: v for k, v in grain_form.items() if k not in SEGMENT_KEYS}
        data.setdefault("resolution", self._resolution)
        return json.dumps(data, sort_keys=True)

    def contains(self, grain_form: dict) -> bool:
        with self._lock:
            return self.key(grain_form) in self._items

    def get(self, grain_form: dict) -> Grain:
        key = self.key(grain_form)
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key]
        grain = grain_from_dict(json.loads(key))
        with self._lock:
            self._items[key] = grain
            while len(self._items) > self._max_size:
                self._items.popitem(last=False)
        return grain
