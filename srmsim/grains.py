"""Propellant grain geometries: cylindrical grains (segments) of length L.

Every grain is case-bonded, so its outer surface never burns.  The basic
grain classes describe one segment whose end faces are inhibited, so the only
burning surface is the inner canal (core).  The canal is prismatic, so the
burning area is simply

    A_b(w) = P(w) * L,

where P(w) is the perimeter of the flame front after a burnt web distance w
(measured normal to the surface) and L is constant.

``SegmentedGrain`` stacks N identical segments (BATES grain) and lets k = 0, 1
or 2 end faces of every segment burn as well.  The faces then recede, so the
segment length is L - k w and the burning area of the stack is

    A_b(w) = N [ P(w) (L - k w) + k A_s(w) ],     A_s = pi R^2 - A_port(w),

where A_s is the propellant cross-section.  The segment is consumed when the
canal reaches the case or when the faces meet (w = L / k).

The exception is the end burner ("fireworks motor"): a solid cylinder without a
canal that burns only on its aft (nozzle-side) face, A_b = pi R^2, while its
length shrinks; it is always a single segment.

Geometries
----------
* ``CircularCoreGrain`` - circular canal (analytic, progressive)
* ``StarGrain``         - n-point star canal (numerical, ~neutral)
* ``CrossGrain``        - cross-shaped canal of n radial slots (numerical)
* ``MoonGrain``         - circular canal displaced from the axis, "moon burner"
* ``EndBurnerGrain``    - no canal, burns on the aft face (analytic, neutral)

Numerical canals are rasterised; a Euclidean distance transform gives the
arrival "time" (in web units) of the flame front at every point, the port area
A_p(w) is obtained by (area-weighted) counting and the perimeter P(w) as the
length of the level set {d = w} inside the case (marching squares).
"""
from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

try:
    from scipy.ndimage import distance_transform_edt
except ImportError:
    distance_transform_edt = None


class Grain:
    """Base class. ``web`` is the burnt distance at which the grain is consumed."""

    kind = "grain"
    label = "grain"
    web: float = 0.0
    outer_diameter: float = 0.0
    length: float = 0.0

    def burning_area(self, w: float) -> float:
        raise NotImplementedError

    def propellant_volume(self, w: float) -> float:
        raise NotImplementedError

    def port_area(self, w: float) -> float:
        return 0.0

    def perimeter(self, w: float) -> float:
        return 0.0

    def mass(self, density: float) -> float:
        return density * self.propellant_volume(0.0)

    def describe(self) -> str:
        return self.label

    def outline(self, w: float = 0.0):
        """Return (x, y) arrays (m) of the canal outline for plotting, or None."""
        return None


class CircularCoreGrain(Grain):
    """Cylindrical grain with a circular canal on the axis; only the canal burns."""

    kind = "circular"
    label = "circular canal"

    def __init__(self, outer_diameter: float, core_diameter: float, length: float):
        if not 0 < core_diameter < outer_diameter:
            raise ValueError("canal diameter must be between 0 and the outer diameter")
        self.outer_diameter = outer_diameter
        self.core_diameter = core_diameter
        self.length = length
        self.web = 0.5 * (outer_diameter - core_diameter)

    def _r(self, w):
        return 0.5 * self.core_diameter + w

    def perimeter(self, w):
        return 0.0 if w >= self.web else 2.0 * math.pi * self._r(w)

    def burning_area(self, w):
        return self.perimeter(w) * self.length

    def port_area(self, w):
        return math.pi * min(self._r(w), 0.5 * self.outer_diameter) ** 2

    def propellant_volume(self, w):
        if w >= self.web:
            return 0.0
        R = 0.5 * self.outer_diameter
        return math.pi * (R * R - self._r(w) ** 2) * self.length

    def outline(self, w=0.0):
        t = np.linspace(0, 2 * np.pi, 200)
        r = min(self._r(w), 0.5 * self.outer_diameter)
        return r * np.cos(t), r * np.sin(t)

    def describe(self):
        return (f"circular canal: D = {self.outer_diameter*1e3:.1f} mm, d = {self.core_diameter*1e3:.1f} mm, "
                f"L = {self.length*1e3:.0f} mm")


class EndBurnerGrain(Grain):
    """Solid cylinder burning only on its aft face ("fireworks motor")."""

    kind = "endburner"
    label = "end burner"

    def __init__(self, outer_diameter: float, length: float):
        self.outer_diameter = outer_diameter
        self.length = length
        self.web = length

    def burning_area(self, w):
        return 0.0 if w >= self.web else math.pi * 0.25 * self.outer_diameter ** 2

    def propellant_volume(self, w):
        return 0.0 if w >= self.web else math.pi * 0.25 * self.outer_diameter ** 2 * (self.length - w)

    def describe(self):
        return f"end burner: D = {self.outer_diameter*1e3:.1f} mm, L = {self.length*1e3:.0f} mm"


class CoreMapGrain(Grain):
    """Grain with an arbitrary prismatic canal, evaluated numerically.

    ``core_fn(x, y)`` receives coordinate arrays (m, origin on the grain axis)
    and returns a boolean mask that is True inside the initial canal.
    """

    kind = "coremap"
    label = "arbitrary canal"

    def __init__(self, outer_diameter: float, length: float,
                 core_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
                 resolution: int = 601, n_web: int = 250):
        if distance_transform_edt is None:
            raise ImportError("numerical canals require scipy")
        self.outer_diameter = outer_diameter
        self.length = length
        R = 0.5 * outer_diameter
        n = int(resolution)
        x = np.linspace(-R, R, n)
        h = x[1] - x[0]
        X, Y = np.meshgrid(x, x)
        inside = X ** 2 + Y ** 2 <= R ** 2
        core = core_fn(X, Y) & inside
        if not core.any():
            raise ValueError("the canal is empty - check its dimensions")
        if core.sum() >= inside.sum():
            raise ValueError("the canal fills the whole grain")
        dist = distance_transform_edt(~core) * h
        dist[core] = 0.0
        self._X, self._Y, self._core, self._inside, self._dist, self._h = X, Y, core, inside, dist, h
        d_prop = dist[inside & ~core] - 0.5 * h
        n_core = int(core.sum())
        radial_web = float(d_prop.max()) + 0.5 * h
        self._w = np.linspace(0.0, radial_web + h, n_web)
        cell = h * h
        area_full = math.pi * R * R
        scale = area_full / (cell * inside.sum())
        ap = np.array([cell * (n_core + np.clip((w - d_prop) / h + 0.5, 0.0, 1.0).sum())
                       for w in self._w]) * scale
        self._ap = np.minimum(ap, area_full)
        perim = self._contour_perimeters(core, h, R)
        if perim is None:
            perim = np.gradient(self._ap, self._w, edge_order=2)
        perim[perim < 0] = 0.0
        self._perim = perim
        full = np.nonzero(self._ap >= area_full * 0.9995)[0]
        self.web = float(self._w[full[0]]) if len(full) else float(self._w[-1])
        self._area_full = area_full

    def _contour_perimeters(self, core, h, R):
        try:
            from skimage import measure
        except ImportError:
            return None
        phi = np.where(core, -(distance_transform_edt(core) * h - 0.5 * h),
                       distance_transform_edt(~core) * h - 0.5 * h)
        self._phi = phi
        perim = np.zeros_like(self._w)
        for i, w in enumerate(self._w):
            tot = 0.0
            for c in measure.find_contours(phi, w):
                xy = c[:, ::-1] * h - R
                seg = np.diff(xy, axis=0)
                mid = 0.5 * (xy[1:] + xy[:-1])
                ok = (mid ** 2).sum(axis=1) < R * R
                tot += float(np.hypot(seg[ok, 0], seg[ok, 1]).sum())
            perim[i] = tot
        j = int(np.searchsorted(self._w, 2.0 * h))
        if j + 6 < len(perim):
            k = np.polyfit(self._w[j:j + 6], perim[j:j + 6], 1)
            perim[:j] = np.polyval(k, self._w[:j])
        return perim

    def port_area(self, w):
        return float(np.interp(w, self._w, self._ap))

    def perimeter(self, w):
        return 0.0 if w >= self.web else float(np.interp(w, self._w, self._perim))

    def burning_area(self, w):
        return self.perimeter(w) * self.length

    def propellant_volume(self, w):
        if w >= self.web:
            return 0.0
        return (self._area_full - self.port_area(w)) * self.length

    def field(self):
        """(X, Y, distance, core mask, inside mask) for plotting burn-back contours."""
        return self._X, self._Y, self._dist, self._core, self._inside


def star_core(n_points: int, r_inner: float, r_outer: float, rotation: float = np.pi / 2):
    """core_fn of an n-point star (valley radius r_inner, tip radius r_outer)."""
    from matplotlib.path import Path

    ang = np.linspace(0, 2 * np.pi, 2 * n_points, endpoint=False) + rotation
    rad = np.where(np.arange(2 * n_points) % 2 == 0, r_outer, r_inner)
    verts = np.column_stack([rad * np.cos(ang), rad * np.sin(ang)])
    path = Path(np.vstack([verts, verts[:1]]), closed=True)

    def fn(X, Y):
        return path.contains_points(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    return fn


def cross_core(n_slots: int, slot_width: float, slot_radius: float, hub_diameter: float = 0.0):
    """core_fn of n radial slots of width b reaching radius r_s (n = 4 gives a cross)."""
    def fn(X, Y):
        m = X ** 2 + Y ** 2 <= (0.5 * hub_diameter) ** 2
        for k in range(n_slots):
            a = 2 * np.pi * k / n_slots + np.pi / 2
            u = X * np.cos(a) + Y * np.sin(a)
            v = -X * np.sin(a) + Y * np.cos(a)
            m |= (u >= 0) & (u <= slot_radius) & (np.abs(v) <= 0.5 * slot_width)
        return m
    return fn


def moon_core(core_diameter: float, offset: float):
    def fn(X, Y):
        return X ** 2 + (Y - offset) ** 2 <= (0.5 * core_diameter) ** 2
    return fn


class StarGrain(CoreMapGrain):
    kind = "star"
    label = "star canal"

    def __init__(self, outer_diameter, length, n_points, star_inner_diameter, star_outer_diameter, resolution=601):
        if not 0 < star_inner_diameter < star_outer_diameter < outer_diameter:
            raise ValueError("require 0 < inner star diameter < outer star diameter < grain diameter")
        self.n_points, self.d_in, self.d_out = int(n_points), star_inner_diameter, star_outer_diameter
        super().__init__(outer_diameter, length,
                         star_core(int(n_points), 0.5 * star_inner_diameter, 0.5 * star_outer_diameter),
                         resolution=resolution)

    def describe(self):
        return (f"{self.n_points}-point star canal: D = {self.outer_diameter*1e3:.1f} mm, "
                f"d_in = {self.d_in*1e3:.1f} mm, d_out = {self.d_out*1e3:.1f} mm, L = {self.length*1e3:.0f} mm")


class CrossGrain(CoreMapGrain):
    kind = "cross"
    label = "cross canal"

    def __init__(self, outer_diameter, length, n_slots, slot_width, slot_length_diameter, resolution=601):
        if not 0 < slot_width < slot_length_diameter < outer_diameter:
            raise ValueError("require 0 < slot width < slot span < grain diameter")
        self.n_slots, self.b, self.span = int(n_slots), slot_width, slot_length_diameter
        super().__init__(outer_diameter, length,
                         cross_core(int(n_slots), slot_width, 0.5 * slot_length_diameter, slot_width),
                         resolution=resolution)

    def describe(self):
        return (f"cross canal ({self.n_slots} slots): D = {self.outer_diameter*1e3:.1f} mm, "
                f"b = {self.b*1e3:.1f} mm, span = {self.span*1e3:.1f} mm, L = {self.length*1e3:.0f} mm")


class MoonGrain(CoreMapGrain):
    kind = "moon"
    label = "moon burner"

    def __init__(self, outer_diameter, length, core_diameter, offset, resolution=601):
        if not 0 < core_diameter < outer_diameter or abs(offset) + 0.5 * core_diameter >= 0.5 * outer_diameter:
            raise ValueError("the displaced canal must lie inside the grain")
        self.d, self.e = core_diameter, offset
        super().__init__(outer_diameter, length, moon_core(core_diameter, offset), resolution=resolution)

    def describe(self):
        return (f"moon burner (displaced canal): D = {self.outer_diameter*1e3:.1f} mm, d = {self.d*1e3:.1f} mm, "
                f"e = {self.e*1e3:.1f} mm, L = {self.length*1e3:.0f} mm")


BURNING_FACES = {"none": 0, "aft": 1, "both": 2}


class SegmentedGrain(Grain):
    """N identical case-bonded segments of a canal grain, optionally burning on their end faces.

    ``faces`` selects the end faces of every segment that burn:
    ``"none"`` (canal only, faces inhibited), ``"aft"`` (canal + the nozzle-side face)
    or ``"both"`` (canal + both faces, the classic BATES segment).  ``gap`` is the
    axial spacing between neighbouring segments (it only adds free chamber volume).
    In the lumped (0-D) model the pressure is uniform, so the position of a
    segment or of its burning face does not change the result.
    """

    kind = "segmented"

    def __init__(self, segment: Grain, n_segments: int = 1, faces: str = "none", gap: float = 0.0):
        if isinstance(segment, (EndBurnerGrain, SegmentedGrain)):
            raise ValueError("the end burner is a single grain burning on its aft face; it cannot be segmented")
        if faces not in BURNING_FACES:
            raise ValueError(f"burning faces must be one of {', '.join(BURNING_FACES)}")
        n = int(n_segments)
        if n < 1:
            raise ValueError("the number of segments must be at least 1")
        if gap < 0:
            raise ValueError("the gap between segments must not be negative")
        self.segment, self.n, self.faces, self.k, self.gap = segment, n, faces, BURNING_FACES[faces], float(gap)
        self.outer_diameter = segment.outer_diameter
        self.segment_length = segment.length
        self.length = n * segment.length + (n - 1) * self.gap
        self.web = min(segment.web, segment.length / self.k) if self.k else segment.web
        self.label = segment.label

    def section_area(self, w: float) -> float:
        L = self.segment_length
        return self.segment.propellant_volume(w) / L if w < self.segment.web else 0.0

    def _seg_len(self, w: float) -> float:
        return max(self.segment_length - self.k * w, 0.0)

    def burning_area(self, w):
        if w >= self.web:
            return 0.0
        L = self.segment_length
        canal = self.segment.burning_area(w) * self._seg_len(w) / L
        return self.n * (canal + self.k * self.section_area(w))

    def propellant_volume(self, w):
        if w >= self.web:
            return 0.0
        return self.n * self.section_area(w) * self._seg_len(w)

    def port_area(self, w):
        return self.segment.port_area(w)

    def perimeter(self, w):
        return self.segment.perimeter(w) if w < self.web else 0.0

    def outline(self, w=0.0):
        return self.segment.outline(w)

    def bates_neutral_length(self):
        """Segment length for which a circular canal burning on both faces is ~neutral:
        the burning area at ignition equals the area at burnout -> L = (3 D + d) / 2
        (classic BATES rule; in between the area is up to ~15 % larger)."""
        g = self.segment
        if isinstance(g, CircularCoreGrain):
            return 0.5 * (3.0 * g.outer_diameter + g.core_diameter)
        return None

    def describe(self):
        base = self.segment.describe()
        if self.n == 1 and self.k == 0:
            return base
        base = base.rsplit(", L = ", 1)[0]
        faces = {"none": "canal only", "aft": "canal + aft faces", "both": "canal + both faces"}[self.faces]
        gap = f", gap {self.gap*1e3:.0f} mm" if self.n > 1 and self.gap > 0 else ""
        return f"{base}, {self.n} × L = {self.segment_length*1e3:.0f} mm ({faces}{gap})"


def unwrap(grain: Grain) -> Grain:
    """The cross-section (single-segment) grain behind a SegmentedGrain."""
    return grain.segment if isinstance(grain, SegmentedGrain) else grain


GRAIN_TYPES = ("circular", "star", "cross", "moon", "endburner")


def grain_from_dict(d: dict) -> Grain:
    """Build a grain from a dictionary with dimensions in millimetres.

    ``length_mm`` is the length of one segment.  Optional keys: ``segments`` (number of
    identical segments, default 1), ``burning_faces`` ("none", "aft" or "both", default
    "none") and ``segment_gap_mm`` (default 0).  They are ignored for the end burner,
    which is always one grain burning on its aft face.
    """
    t = d["type"].lower()
    mm = 1e-3
    D, L = float(d["outer_diameter_mm"]) * mm, float(d["length_mm"]) * mm
    res = int(d.get("resolution", 601))
    if t in ("endburner", "end_burner", "end-burner"):
        return EndBurnerGrain(D, L)
    if t in ("circular", "tubular", "core"):
        g = CircularCoreGrain(D, float(d["core_diameter_mm"]) * mm, L)
    elif t == "star":
        g = StarGrain(D, L, int(d["points"]), float(d["star_inner_diameter_mm"]) * mm,
                      float(d["star_outer_diameter_mm"]) * mm, res)
    elif t == "cross":
        g = CrossGrain(D, L, int(d.get("slots", 4)), float(d["slot_width_mm"]) * mm,
                       float(d["slot_span_mm"]) * mm, res)
    elif t in ("moon", "moonburner"):
        g = MoonGrain(D, L, float(d["core_diameter_mm"]) * mm, float(d["offset_mm"]) * mm, res)
    else:
        raise ValueError(f"unknown grain type '{d['type']}' (use one of {', '.join(GRAIN_TYPES)})")
    n = int(d.get("segments", 1))
    faces = str(d.get("burning_faces", "none")).lower()
    gap = float(d.get("segment_gap_mm", 0.0)) * mm
    if n == 1 and faces == "none":
        return g
    return SegmentedGrain(g, n, faces, gap)
