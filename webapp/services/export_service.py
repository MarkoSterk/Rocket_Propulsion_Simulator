"""Animated GIF of the burn-back from frames rendered in the browser."""
from __future__ import annotations

import base64
import io

from PIL import Image

from .errors import ServiceError

PALETTE_COLOURS = 160


class ExportService:
    def __init__(self, max_frames: int):
        self.max_frames = max_frames

    def gif(self, frames: list[str], fps: float = 15, hold_last_ms: int = 1000) -> bytes:
        """Build a looping GIF from PNG data URLs.

        All frames share one palette built from the first, middle and last frame so the colours
        do not flicker; the last frame is held for ``hold_last_ms``.
        """
        if not frames or not 1 <= len(frames) <= self.max_frames:
            raise ServiceError(f"between 1 and {self.max_frames} frames are required")
        fps = min(max(float(fps), 1.0), 50.0)
        hold_last_ms = min(max(int(hold_last_ms), 0), 10000)
        try:
            images = [Image.open(io.BytesIO(base64.b64decode(f.split(",", 1)[-1]))).convert("RGB") for f in frames]
        except Exception as exc:
            raise ServiceError(f"invalid frame data: {exc}") from exc
        width, height = images[0].size
        sample = [images[0], images[len(images) // 2], images[-1]]
        strip = Image.new("RGB", (width, height * len(sample)), "white")
        for k, im in enumerate(sample):
            strip.paste(im.resize((width, height)), (0, k * height))
        quantize = getattr(Image, "Quantize", Image)
        no_dither = getattr(getattr(Image, "Dither", Image), "NONE", 0)
        palette = strip.quantize(colors=PALETTE_COLOURS, method=quantize.MEDIANCUT)
        frames_q = [im.resize((width, height)).quantize(palette=palette, dither=no_dither) for im in images]
        durations = [int(round(1000.0 / fps))] * len(frames_q)  # noqa: RUF046
        durations[-1] += hold_last_ms
        buf = io.BytesIO()
        frames_q[0].save(buf, format="GIF", save_all=True, append_images=frames_q[1:], duration=durations,
                         loop=0, disposal=1)
        return buf.getvalue()
