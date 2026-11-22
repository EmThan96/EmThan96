""" HBT catalogue access and fixture geometry.

Pure Python (no Allplan imports), so everything here can be tested outside Allplan.
Data source: HBT_Catalogue.json (typed from the official technical product information HBT 22-E, pages 10-13, 22).

Local fixture coordinate system (mm):

* origin = reference point = casing end, on the formwork face, centre of the casing width
* +x     = along the casing length
* +y     = across the casing width
* +z     = into component 1 (anchor side, length h); -z = connected component (length lü)

The dimensioning point is the centre of the casing on the formwork face: (L/2, 0, 0).
"""

from __future__ import annotations

__author__ = "Em Than - gbc engineers"

import json
import math
import os

from dataclasses import dataclass, field
from itertools import product as _product
from typing import Callable

Point = tuple[float, float, float]

DEFAULT_CATALOGUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HBT_Catalogue.json")

# placement constants (must match the .pyp file)
FACE_HORIZONTAL         = 1
FACE_VERTICAL_BOX_HORIZ = 2
FACE_VERTICAL_BOX_VERT  = 3

BARS_STRAIGHTENED = 1
BARS_DELIVERED    = 2

SHEET_THICKNESS = 1.0

ANCHOR_SHAPES     = ("straight", "hook", "hook_in", "hook_out", "u_rows", "loop_x")
CONNECTION_SHAPES = ("straight", "stirrup")

EPS = 1e-6


class CatalogueError(Exception):
    """ error in the catalogue data """


def fmt(value: float) -> str:
    """ number without trailing .0 """

    value = round(float(value), 3)
    return str(int(value)) if value.is_integer() else str(value)


# ---------------------------------------------------------------------------------------------------------------------
# catalogue
# ---------------------------------------------------------------------------------------------------------------------

class HBTCatalogue:
    """ read access to the HBT catalogue """

    def __init__(self, data: dict):
        self.data        = data
        self.casings     = {(c["rows"], c["code"]): c for c in data.get("casings", [])}
        self.rebar_types = data.get("rebar_types", {})

        if not self.casings:
            raise CatalogueError("Catalogue contains no casings")

        for (_, code), cas in self.casings.items():
            self._validate_casing(code, cas)

    @classmethod
    def load(cls, path: str = DEFAULT_CATALOGUE) -> HBTCatalogue:
        with open(path, encoding="utf-8") as file:
            return cls(json.load(file))

    def _validate_casing(self, code: str, cas: dict):
        rows = cas.get("rows")

        if rows not in (1, 2):
            raise CatalogueError(f"{code}: rows must be 1 or 2")

        for rtype in cas.get("rebar_types", []):
            rdef = self.rebar_types.get(rtype)

            if rdef is None:
                raise CatalogueError(f"{code}: unknown rebar type {rtype}")
            if rdef["rows"] != rows:
                raise CatalogueError(f"{code}: rebar type {rtype} is for {rdef['rows']} row(s)")
            if rdef["anchor"] not in ANCHOR_SHAPES or rdef["connection"] not in CONNECTION_SHAPES:
                raise CatalogueError(f"rebar type {rtype}: unknown shape")

        keys = ["lu_std", "lu_max_1250", "lu_max_800"] + (["b", "lu_max_stirrup"] if rows == 2 else ["y"])

        for dia, var in cas.get("diameters", {}).items():
            for key in keys:
                if key not in var:
                    raise CatalogueError(f"{code} D{dia}: '{key}' missing")
            if dia not in self.data.get("casing_H2", {}):
                raise CatalogueError(f"{code} D{dia}: no casing height H2")

    # ----- settings

    @property
    def mandrel_defaults(self) -> tuple[float, float]:
        """ (catalogue D/Ø, EC2 default D/Ø) """

        mand = self.data.get("mandrel", {})
        return float(mand.get("catalogue", 10)), float(mand.get("ec2", 4))

    @property
    def custom_settings(self) -> dict:
        return {"min_without_table": 800, "max": 1250, "end_spacing_min": 25, **self.data.get("custom_length", {})}

    def attribute_names(self) -> tuple[list[str], list[list[str]]]:
        attr = self.data.get("attributes", {})
        answers = attr.get("answers", [[f"Answer {i}"] for i in range(1, 6)])
        return list(attr.get("plan_text", ["Plan_text"])), [list(a) for a in answers]

    # ----- lists for the palette

    def casing_codes(self, rows: int) -> list[str]:
        return [code for (r, code) in self.casings if r == rows]

    def rebar_type_texts(self, rows: int, casing: str) -> list[str]:
        return [self.rebar_types[t]["text"] for t in self.casings[(rows, casing)]["rebar_types"]]

    def rebar_type_code(self, text: str) -> str | None:
        for code, rdef in self.rebar_types.items():
            if rdef["text"] == text or code == text:
                return code
        return None

    def diameters(self, rows: int, casing: str) -> list[str]:
        return sorted(self.casings[(rows, casing)]["diameters"], key=float)

    def spacings(self, rows: int, casing: str, dia: str) -> list[str]:
        """ bar spacings in cm (as in the catalogue) """

        return sorted(self.casings[(rows, casing)]["diameters"][dia]["lu_std"], key=float)

    def element_lengths(self) -> list[str]:
        return list(self.data["element_lengths"])

    def first_valid(self, rows: int, casing: str | None, type_text: str | None, dia: str | None,
                    spacing: str | None) -> tuple[int, str, str, str, str]:
        """ valid selection, keeping the given values where they are still valid """

        rows    = rows if self.casing_codes(rows) else next(iter(self.casings))[0]
        codes   = self.casing_codes(rows)
        casing  = casing if casing in codes else codes[0]
        texts   = self.rebar_type_texts(rows, casing)
        type_text = type_text if type_text in texts else texts[0]
        dias    = self.diameters(rows, casing)
        dia     = dia if dia in dias else dias[0]
        spcs    = self.spacings(rows, casing, dia)
        spacing = spacing if spacing in spcs else spcs[0]

        return rows, casing, type_text, dia, spacing

    # ----- specification

    def spec(self, rows: int, casing: str, type_text: str, dia: str, spacing: str, length: float | str,
             h: float | None = None, lu: float | None = None, leg: float | None = None, strip: bool = False,
             mandrel_catalogue: float | None = None, mandrel_ec2: float | None = None) -> HBTSpec:
        """ product specification; h, lu, leg, mandrels = None -> catalogue default

        Args:
            spacing: bar spacing in cm as in the catalogue ("10", "15", ...)
            length:  element length in mm (standard 1250 / 800 or any custom length)
        """

        cas   = self.casings[(rows, casing)]
        rtype = self.rebar_type_code(type_text)

        if rtype is None:
            raise CatalogueError(f"unknown rebar type '{type_text}'")

        rdef    = self.rebar_types[rtype]
        var     = cas["diameters"][dia]
        d       = float(dia)
        s_mm    = float(spacing) * 10
        length  = float(length)
        len_key = fmt(length)
        stirrup = rdef["connection"] == "stirrup"
        custom  = self.custom_settings

        # ----- bar layout: catalogue table for standard lengths, else a >= end_spacing_min, symmetric

        if len_key in self.data["bar_layout"] and spacing in self.data["bar_layout"][len_key]:
            count, end_mm = self.data["bar_layout"][len_key][spacing]
            standard_length = True
        else:
            a_min = float(custom["end_spacing_min"])
            count = int(math.floor((length - 2 * a_min) / s_mm + EPS)) + 1 if length >= 2 * a_min else 0
            end_mm = (length - (count - 1) * s_mm) / 2 if count > 0 else 0.0
            standard_length = False

        # ----- lü limits (column by length)

        lu_star = float(self.data.get("lu_standard", {}).get(dia, var["lu_std"][spacing]))

        if stirrup:
            lu_max = float(var["lu_max_stirrup"][spacing])
        elif length >= 1250 - EPS:
            lu_max = float(var["lu_max_1250"][spacing])
        else:
            lu_max = float(var["lu_max_800"][spacing])

        if length < 800 - EPS and not stirrup:
            lu_max = min(lu_max, lu_star)

        lu_min = 60.0 if stirrup else 0.0
        lu_def = lu_max if stirrup else min(float(var["lu_std"][spacing]), lu_max)

        h_min = float(self.data["h_min_stirrup"][rtype][dia] if stirrup else self.data["h_min"])
        h_def = max(float(self.data["h_std"]), h_min)

        # ----- leg of the anchor

        leg_name  = rdef.get("leg") or ""
        leg_range = None

        if leg_name == "y":
            leg_def = float(var["y"]) if "y" in var else 10 * d
        elif rtype == "4":
            leg_range = cas.get("type4_b_range")
            leg_def   = float(leg_range[0]) if leg_range else 200.0
        elif leg_name:
            leg_def = 10 * d
        else:
            leg_def = 0.0

        # ----- minimum length

        min_table = self.data.get("min_casing_length", {}).get(dia, {}).get(spacing)
        min_custom = float(custom["min_without_table"])

        cat_mand, ec2_mand = self.mandrel_defaults

        spec = HBTSpec(casing          = casing,
                       rows            = rows,
                       rebar_type      = rtype,
                       type_text       = rdef["text"],
                       anchor          = rdef["anchor"],
                       connection      = rdef["connection"],
                       leg_bend        = rdef.get("leg_bend", "ec2"),
                       diameter        = d,
                       spacing         = s_mm,
                       length          = length,
                       standard_length = standard_length,
                       bar_count       = int(count),
                       end_spacing     = float(end_mm),
                       casing_width    = float(cas["width_B"]),
                       casing_depth    = float(self.data["casing_H2"][dia]),
                       casing_h1       = float(self.data.get("casing_H1", 12)),
                       rebar_width     = float(var.get("b", 0.0)),
                       h               = h_def if h is None else float(h),
                       h_min           = h_min,
                       lu              = lu_def if lu is None else float(lu),
                       lu_min          = lu_min,
                       lu_max          = lu_max,
                       lu_star         = lu_star,
                       leg_name        = leg_name,
                       leg             = leg_def if leg is None else float(leg),
                       leg_range       = tuple(leg_range) if leg_range else None,
                       strip           = strip and stirrup,
                       mandrel_catalogue = cat_mand if mandrel_catalogue is None else float(mandrel_catalogue),
                       mandrel_ec2     = ec2_mand if mandrel_ec2 is None else float(mandrel_ec2),
                       min_length_table = float(min_table) if min_table is not None else None,
                       min_length_custom = min_custom,
                       max_length_custom = float(custom["max"]),
                       type4_on_request = rtype == "4" and not leg_range)
        return spec


# ---------------------------------------------------------------------------------------------------------------------
# specification
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class HBTSpec:
    """ full specification of one HBT element """

    casing           : str
    rows             : int
    rebar_type       : str
    type_text        : str
    anchor           : str
    connection       : str
    leg_bend         : str
    diameter         : float
    spacing          : float          # mm
    length           : float
    standard_length  : bool
    bar_count        : int            # bar positions (catalogue "number of rebar")
    end_spacing      : float          # mm
    casing_width     : float          # B
    casing_depth     : float          # H2
    casing_h1        : float
    rebar_width      : float          # b (double row, outer dimension)
    h                : float
    h_min            : float
    lu               : float
    lu_min           : float
    lu_max           : float
    lu_star          : float          # lü standard (type test) for the min. length table
    leg_name         : str
    leg              : float
    leg_range        : tuple | None = None
    strip            : bool = False
    mandrel_catalogue: float = 10.0
    mandrel_ec2      : float = 4.0
    min_length_table : float | None = None
    min_length_custom: float = 800.0
    max_length_custom: float = 1250.0
    type4_on_request : bool = False

    @property
    def row_distance(self) -> float:
        """ axis distance of the two rows (b is the outer dimension) """

        return self.rebar_width - self.diameter if self.rows == 2 else 0.0

    @property
    def bar_x_positions(self) -> list[float]:
        return [self.end_spacing + i * self.spacing for i in range(self.bar_count)]

    @property
    def row_y_positions(self) -> list[float]:
        return [0.0] if self.rows == 1 else [-self.row_distance / 2, self.row_distance / 2]

    @property
    def minimum_length(self) -> float:
        """ shortest allowed casing length for this rebar configuration (hard limit) """

        if self.connection == "straight" and self.lu <= self.lu_star + EPS and self.min_length_table:
            return min(self.min_length_table, self.min_length_custom)

        return self.min_length_custom

    @property
    def designation(self) -> str:
        """ order designation as in the catalogue, e.g. HBT 85 - 10/10 - 2 - 1250, h = 170, lü = 430, b = 100 """

        prefix = self.casing.replace("HBT", "HBT-S", 1) if self.strip else self.casing
        text   = (f"{prefix} - {fmt(self.diameter)}/{fmt(self.spacing / 10)} - {self.rebar_type} - "
                  f"{fmt(self.length)}, h = {fmt(self.h)}, lü = {fmt(self.lu)}")

        if self.leg_name:
            text += f", {self.leg_name} = {fmt(self.leg)}"

        return text

    def errors(self) -> list[str]:
        """ violations of catalogue limits - the element must not be created """

        err = []

        if self.h < self.h_min - EPS:
            err.append(f"h < hmin = {fmt(self.h_min)}")

        if self.lu > self.lu_max + EPS:
            err.append(f"lü > lü,max = {fmt(self.lu_max)} (L = {fmt(self.length)})")

        if self.lu < self.lu_min - EPS:
            err.append(f"lü < {fmt(self.lu_min)}")

        if self.leg_name and self.leg <= 0:
            err.append(f"{self.leg_name} must be > 0")

        if self.leg_range and not self.leg_range[0] - EPS <= self.leg <= self.leg_range[1] + EPS:
            err.append(f"b outside {self.leg_range[0]}...{self.leg_range[1]}")

        if self.type4_on_request:
            err.append("Type 4 for this casing: on request")

        if not self.standard_length:
            if self.length < self.minimum_length - EPS:
                err.append(f"L < Lmin = {fmt(self.minimum_length)}")
            if self.length > self.max_length_custom + EPS:
                err.append(f"L > {fmt(self.max_length_custom)}: on request")

        if self.bar_count < 1:
            err.append("no rebar fits into the casing")

        return err


# ---------------------------------------------------------------------------------------------------------------------
# bars and layout
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Bar:
    """ bar centre line with the mandrel factor D/Ø for each interior vertex """

    points  : list[Point]
    mandrels: list[float]


@dataclass
class HBTLayout:
    """ geometry of one HBT element in local coordinates """

    spec       : HBTSpec
    box_plates : list[tuple[Point, Point]] = field(default_factory=list)
    box_outline: tuple[Point, Point] = ((0, 0, 0), (0, 0, 0))
    bars       : list[Bar]          = field(default_factory=list)
    ref_point  : Point = (0.0, 0.0, 0.0)
    dim_point  : Point = (0.0, 0.0, 0.0)


class _Path:
    """ helper to build a polyline with a mandrel factor per vertex """

    def __init__(self):
        self.pts : list[Point] = []
        self.mand: list[float] = []      # factor at each point (ends ignored)

    def add(self, pnt: Point, mandrel: float = 0.0):
        if self.pts and math.dist(self.pts[-1], pnt) < EPS:
            self.mand[-1] = max(self.mand[-1], mandrel)
            return
        self.pts.append(pnt)
        self.mand.append(mandrel)

    def bar(self) -> Bar:
        return Bar(list(self.pts), [self.mand[i] for i in range(1, len(self.pts) - 1)])


def compute_layout(spec: HBTSpec, bar_state: int = BARS_STRAIGHTENED) -> HBTLayout:
    """ casing plates and bar centre lines (with bend data) in local coordinates """

    length = spec.length
    half_w = spec.casing_width / 2
    depth  = spec.casing_depth
    thick  = SHEET_THICKNESS

    layout = HBTLayout(spec=spec)

    layout.box_outline = ((0.0, -half_w, 0.0), (length, half_w, depth))
    layout.box_plates  = [((0.0,            -half_w,         depth - thick), (length, half_w, depth)),
                          ((0.0,            -half_w,         0.0),           (length, -half_w + thick, depth)),
                          ((0.0,             half_w - thick, 0.0),           (length, half_w, depth)),
                          ((0.0,            -half_w,         0.0),           (thick, half_w, depth)),
                          ((length - thick, -half_w,         0.0),           (length, half_w, depth))]

    layout.ref_point = (0.0, 0.0, 0.0)
    layout.dim_point = (length / 2, 0.0, 0.0)

    ec2      = spec.mandrel_ec2
    leg_mand = spec.mandrel_catalogue if spec.leg_bend == "catalogue" else ec2

    delivered = bar_state == BARS_DELIVERED
    z_face    = min(spec.diameter * 1.5, depth - spec.diameter) if delivered else 0.0
    x_limit   = length - SHEET_THICKNESS - spec.diameter
    rows_y    = spec.row_y_positions

    for x in spec.bar_x_positions:
        bent_len = max(0.0, min(spec.lu, x_limit - x))

        def anchor_tip_to_face(path: _Path, y: float, row_index: int):
            """ add the anchor from its tip to the face point """

            tip    = _anchor_tip(spec, x, y, row_index)
            corner = (x + _anchor_x_offset(spec, row_index), y, spec.h)
            if tip is not None:
                path.add(tip)
                path.add(corner, leg_mand)
            else:
                path.add(corner)
            path.add((x, y, z_face), ec2 if delivered else 0.0)

        def anchor_face_to_tip(path: _Path, y: float, row_index: int):
            path.add((x, y, z_face), ec2 if delivered else 0.0)
            tip    = _anchor_tip(spec, x, y, row_index)
            corner = (x + _anchor_x_offset(spec, row_index), y, spec.h)
            if tip is not None:
                path.add(corner, leg_mand)
                path.add(tip)
            else:
                path.add(corner)

        def connection(path: _Path, y: float, reverse: bool = False):
            pts = [(x, y, z_face), (x + bent_len, y, z_face)] if delivered else [(x, y, 0.0), (x, y, -spec.lu)]
            for pnt in (pts[::-1] if reverse else pts):
                path.add(pnt)

        if spec.rows == 2 and spec.connection == "stirrup":
            y1, y2 = rows_y
            path = _Path()
            anchor_tip_to_face(path, y1, 0)
            if delivered:
                path.add((x + bent_len, y1, z_face), ec2)
                path.add((x + bent_len, y2, z_face), ec2)
            else:
                path.add((x, y1, -spec.lu), ec2)
                path.add((x, y2, -spec.lu), ec2)
            anchor_face_to_tip(path, y2, 1)
            layout.bars.append(path.bar())
            continue

        if spec.anchor == "u_rows":
            y1, y2 = rows_y
            path = _Path()
            connection(path, y1, reverse=True)
            path.add((x, y1, z_face), ec2 if delivered else 0.0)
            path.add((x, y1, spec.h), ec2)
            path.add((x, y2, spec.h), ec2)
            path.add((x, y2, z_face), ec2 if delivered else 0.0)
            connection(path, y2)
            layout.bars.append(path.bar())
            continue

        for idx, y in enumerate(rows_y):
            path = _Path()
            anchor_tip_to_face(path, y, idx)
            connection(path, y)
            layout.bars.append(path.bar())

    return layout


def _anchor_x_offset(spec: HBTSpec, row_index: int) -> float:
    """ x offset of the anchor corner (z = h) against the bar position

    Inward bends (b2) that reach the other row cannot lie in one plane. As in the catalogue sketches
    (HBT 22-E page 12, types 8 and 22), the two legs pass side by side: the anchor legs lean apart
    along the casing length by one diameter each.
    """

    if spec.anchor == "hook_in" and spec.rows == 2 and 2 * spec.leg > spec.row_distance - spec.diameter - EPS:
        return -spec.diameter if row_index == 0 else spec.diameter

    return 0.0


def _anchor_tip(spec: HBTSpec, x: float, y: float, row_index: int) -> Point | None:
    """ tip of the anchor leg at z = h, or None for a straight anchor """

    leg = spec.leg
    cx  = x + _anchor_x_offset(spec, row_index)

    if spec.anchor == "hook":
        if spec.leg_name == "y":
            # hook y points along the casing length (catalogue sketches, types 1, 9, 11)
            return (cx - leg, y, spec.h)
        # bend b (type 2, D = 10Ø) lies across the casing width (catalogue page 10)
        return (cx, y - leg, spec.h)

    if spec.anchor in ("hook_in", "hook_out"):
        outward = -1.0 if row_index == 0 else 1.0
        sign    = outward if spec.anchor == "hook_out" else -outward
        return (cx, y + sign * leg, spec.h)

    if spec.anchor == "loop_x":
        return (x + leg, y, spec.h)

    return None


# ---------------------------------------------------------------------------------------------------------------------
# bends: fillet algorithm
# ---------------------------------------------------------------------------------------------------------------------

def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a: Point, f: float) -> Point:
    return (a[0] * f, a[1] * f, a[2] * f)


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(vec: Point) -> Point:
    length = math.sqrt(_dot(vec, vec))
    return _mul(vec, 1.0 / length) if length > 1e-9 else (0.0, 0.0, 0.0)


def _cross(a: Point, b: Point) -> Point:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


@dataclass
class LineSeg:
    start: Point
    end  : Point

    @property
    def length(self) -> float:
        return math.dist(self.start, self.end)


@dataclass
class ArcSeg:
    """ circular arc: starts at center + radius * x_dir, turns by angle around normal """

    center: Point
    x_dir : Point
    normal: Point
    radius: float
    angle : float
    start : Point
    end   : Point

    @property
    def length(self) -> float:
        return self.radius * self.angle


def fillet_bar(bar: Bar, diameter: float) -> tuple[list[LineSeg | ArcSeg], bool]:
    """ replace each corner of the bar centre line by an arc with the mandrel radius

    Centre-line bend radius R = D/2 + Ø/2 with D = mandrel factor * Ø.
    At a corner with turning angle θ the tangent length is t = R * tan(θ/2); both adjacent straight parts
    are shortened by t. If two fillets do not fit on one straight part (t1 + t2 > segment length),
    both radii are reduced proportionally and the function reports it.

    Returns:
        (segments, radius_reduced)
    """

    pts = bar.points
    n   = len(pts)

    if n < 2:
        return [], False

    radii  = [0.0] * n
    angles = [0.0] * n
    dirs   = [_norm(_sub(pts[i + 1], pts[i])) for i in range(n - 1)]

    for i in range(1, n - 1):
        cos_t     = max(-1.0, min(1.0, _dot(dirs[i - 1], dirs[i])))
        angles[i] = math.acos(cos_t)
        if angles[i] > 1e-6 and bar.mandrels[i - 1] > 0:
            radii[i] = (bar.mandrels[i - 1] * diameter + diameter) / 2

    tangents = [radii[i] * math.tan(angles[i] / 2) if radii[i] > 0 else 0.0 for i in range(n)]

    reduced = False

    for i in range(n - 1):
        seg_len = math.dist(pts[i], pts[i + 1])
        need    = tangents[i] + tangents[i + 1]
        if need > seg_len + EPS:
            factor = seg_len / need
            for k in (i, i + 1):
                tangents[k] *= factor
                radii[k]    *= factor
            reduced = True

    segments: list[LineSeg | ArcSeg] = []
    current = pts[0]

    for i in range(1, n):
        u = dirs[i - 1]

        if i == n - 1 or radii[i] <= 0:
            if math.dist(current, pts[i]) > EPS:
                segments.append(LineSeg(current, pts[i]))
            current = pts[i]
            continue

        v  = dirs[i]
        t1 = _sub(pts[i], _mul(u, tangents[i]))
        t2 = _add(pts[i], _mul(v, tangents[i]))

        if math.dist(current, t1) > EPS:
            segments.append(LineSeg(current, t1))

        inward = _norm(_sub(v, _mul(u, _dot(v, u))))          # from t1 towards the centre
        center = _add(t1, _mul(inward, radii[i]))
        x_dir  = _norm(_sub(t1, center))
        normal = _norm(_cross(x_dir, u))

        segments.append(ArcSeg(center, x_dir, normal, radii[i], angles[i], t1, t2))
        current = t2

    return segments, reduced


def arc_point(arc: ArcSeg, angle: float) -> Point:
    """ point on the arc at the given angle from the start """

    y_dir = _cross(arc.normal, arc.x_dir)
    return _add(arc.center, _add(_mul(arc.x_dir, arc.radius * math.cos(angle)),
                                 _mul(y_dir, arc.radius * math.sin(angle))))


# ---------------------------------------------------------------------------------------------------------------------
# line placement: split a length into standard and custom elements
# ---------------------------------------------------------------------------------------------------------------------

def split_length(total: float, is_valid: Callable[[float], bool],
                 standards: tuple[float, ...] = (1250.0, 800.0)) -> list[float] | None:
    """ split a length into elements: as many standard elements (1250 first, then 800) as possible,
    the rest as custom element(s)

    Ranking of the candidates:
        1. fewest custom elements (0, 1 or 2 equal custom elements)
        2. fewest elements in total
        3. most 1250 elements
    Every element length must pass is_valid (catalogue limits incl. minimum length and lü,max).

    Args:
        total:    length to fill [mm] (rounded down to 1 mm)
        is_valid: check of one element length
        standards: standard lengths, longest first

    Returns:
        element lengths in placement order (1250, 800, custom) or None if no valid split exists
    """

    total = math.floor(total + EPS)

    if total <= 0:
        return None

    cache: dict[float, bool] = {}
    check = is_valid

    def is_valid(length: float) -> bool:          # noqa: F811 - cached wrapper
        if length not in cache:
            cache[length] = check(length)
        return cache[length]

    valid_std = [s for s in standards if is_valid(s)]
    best: tuple | None = None

    ranges = [range(int(total // s) + 1) for s in valid_std]

    for counts in _product(*ranges):
        used = sum(c * s for c, s in zip(counts, valid_std))
        rest = total - used

        if rest < -EPS:
            continue

        for n_custom in (0, 1, 2):
            if n_custom == 0:
                if rest > EPS:
                    continue
                customs = []
            else:
                piece = math.floor(rest / n_custom)
                customs = [piece] * (n_custom - 1) + [rest - piece * (n_custom - 1)]
                if any(c <= 0 or not is_valid(c) for c in customs):
                    continue

            count_1250 = counts[0] if valid_std and valid_std[0] == standards[0] else 0
            key = (n_custom, sum(counts) + n_custom, -count_1250)

            if best is None or key < best[0]:
                lengths = [s for c, s in zip(counts, valid_std) for _ in range(c)] + customs
                best = (key, lengths)

            break     # fewer customs always ranks better for this standard combination

    return None if best is None else best[1]


# ---------------------------------------------------------------------------------------------------------------------
# placement frames
# ---------------------------------------------------------------------------------------------------------------------

def placement_axes(ref_point: Point, dir_point: Point | None, face_plane: int, flip: bool,
                   default_dir: Point = (1.0, 0.0, 0.0)) -> tuple[Point, Point, Point]:
    """ local axes (x, y, z) in world coordinates for the single placement; z points into component 1

    Args:
        ref_point:   first click (reference point)
        dir_point:   second click (direction point) or None during the first input
        face_plane:  FACE_HORIZONTAL / FACE_VERTICAL_BOX_HORIZ / FACE_VERTICAL_BOX_VERT
        flip:        put component 1 on the other side of the face
        default_dir: direction when no valid direction point is given
    """

    direction = default_dir

    if dir_point is not None:
        cand = (dir_point[0] - ref_point[0], dir_point[1] - ref_point[1], 0.0)
        if math.hypot(cand[0], cand[1]) > 1e-6:
            direction = cand

    direction = _norm((direction[0], direction[1], 0.0))

    if direction == (0.0, 0.0, 0.0):
        direction = (1.0, 0.0, 0.0)

    up   = (0.0, 0.0, 1.0)
    sign = -1.0 if flip else 1.0

    if face_plane == FACE_HORIZONTAL:
        x_dir = direction
        z_dir = (0.0, 0.0, -sign)
    else:
        normal = _cross(up, direction)
        z_dir  = _mul(normal, sign)
        x_dir  = up if face_plane == FACE_VERTICAL_BOX_VERT else direction

    return x_dir, _norm(_cross(z_dir, x_dir)), z_dir


def segment_axes(start: Point, end: Point, face_plane: int, flip: bool,
                 vertical_face_angle: float = 0.0) -> tuple[Point, Point, Point] | None:
    """ local axes for an element along a polyline segment (x = segment direction, 3D)

    * horizontal face: z = down (or up when flipped), made perpendicular to x
    * vertical face:   z = horizontal normal left of the segment; for a vertical segment the normal
                       is given by vertical_face_angle (degrees in plan)

    Returns:
        (x, y, z) or None for a zero length segment
    """

    x_dir = _norm(_sub(end, start))

    if x_dir == (0.0, 0.0, 0.0):
        return None

    sign = -1.0 if flip else 1.0
    up   = (0.0, 0.0, 1.0)

    if face_plane == FACE_HORIZONTAL:
        z_ref = (0.0, 0.0, -sign)
        z_dir = _norm(_sub(z_ref, _mul(x_dir, _dot(z_ref, x_dir))))
        if z_dir == (0.0, 0.0, 0.0):                      # vertical segment on a horizontal face: impossible
            return None
    else:
        horiz = _norm(_cross(up, x_dir))
        if horiz == (0.0, 0.0, 0.0):                      # vertical segment
            ang   = math.radians(vertical_face_angle)
            horiz = (math.cos(ang), math.sin(ang), 0.0)
        z_dir = _mul(horiz, sign)

    return x_dir, _norm(_cross(z_dir, x_dir)), z_dir


def local_to_world(pnt: Point, origin: Point, axes: tuple[Point, Point, Point]) -> Point:
    x_dir, y_dir, z_dir = axes
    return tuple(origin[i] + pnt[0] * x_dir[i] + pnt[1] * y_dir[i] + pnt[2] * z_dir[i] for i in range(3))  # type: ignore
