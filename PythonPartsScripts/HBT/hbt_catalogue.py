""" HBT catalogue access and fixture layout calculation.

Pure Python (no Allplan imports), so it can be tested outside Allplan.
Data source: HBT_Catalogue.json (typed from the official technical product information, pages 10-13).

Local fixture coordinate system (mm):

* origin = reference point = casing end, on the formwork face, centre of the casing width
* +x     = along the casing length
* +y     = across the casing width
* +z     = into component 1 (anchor side, length h); -z = connected component (length lü)

The dimensioning point is the centre of the casing on the formwork face: (L/2, 0, 0).
"""

from __future__ import annotations

import json
import math
import os

from dataclasses import dataclass, field

Point = tuple[float, float, float]

DEFAULT_CATALOGUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HBT_Catalogue.json")

# placement constants (must match the .pyp file)
FACE_HORIZONTAL         = 1
FACE_VERTICAL_BOX_HORIZ = 2
FACE_VERTICAL_BOX_VERT  = 3

BARS_STRAIGHTENED = 1           # installed state: connection legs straightened into the connected component
BARS_DELIVERED    = 2           # delivery state: connection legs bent into the casing

SHEET_THICKNESS = 1.0           # visual thickness of the casing walls

ANCHOR_SHAPES     = ("straight", "hook", "hook_in", "hook_out", "u_rows", "loop_x")
CONNECTION_SHAPES = ("straight", "stirrup")


class CatalogueError(Exception):
    """ error in the catalogue data """


def _fmt(value: float) -> str:
    """ number without trailing .0 """

    return str(int(value)) if float(value).is_integer() else str(value)


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

    # ----- lists for the palette (strings for StringComboBox)

    def casing_codes(self, rows: int) -> list[str]:
        return [code for (r, code) in self.casings if r == rows]

    def rebar_type_texts(self, rows: int, casing: str) -> list[str]:
        return [self.rebar_types[t]["text"] for t in self.casings[(rows, casing)]["rebar_types"]]

    def rebar_type_code(self, text: str) -> str | None:
        for code, rdef in self.rebar_types.items():
            if rdef["text"] == text:
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
                    spacing: str | None, length: str | None) -> tuple[int, str, str, str, str, str]:
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
        lens    = self.element_lengths()
        length  = length if length in lens else lens[0]

        return rows, casing, type_text, dia, spacing, length

    # ----- specification

    def spec(self, rows: int, casing: str, type_text: str, dia: str, spacing: str, length: str,
             h: float | None = None, lu: float | None = None, leg: float | None = None,
             strip: bool = False) -> HBTSpec:
        """ product specification; h, lu, leg = None -> catalogue default """

        cas   = self.casings[(rows, casing)]
        rtype = self.rebar_type_code(type_text)

        if rtype is None:
            raise CatalogueError(f"unknown rebar type '{type_text}'")

        rdef  = self.rebar_types[rtype]
        var   = cas["diameters"][dia]
        d     = float(dia)
        stirrup = rdef["connection"] == "stirrup"

        count, end_mm = self.data["bar_layout"][length][spacing]

        lu_max = float(var["lu_max_stirrup"][spacing] if stirrup else
                       var["lu_max_1250" if length == "1250" else "lu_max_800"][spacing])
        lu_min = 60.0 if stirrup else 0.0
        lu_def = lu_max if stirrup else min(float(var["lu_std"][spacing]), lu_max)

        h_min = float(self.data["h_min_stirrup"][rtype][dia] if stirrup else self.data["h_min"])
        h_def = max(float(self.data["h_std"]), h_min)

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

        return HBTSpec(casing        = casing,
                       rows          = rows,
                       rebar_type    = rtype,
                       type_text     = type_text,
                       anchor        = rdef["anchor"],
                       connection    = rdef["connection"],
                       diameter      = d,
                       spacing       = float(spacing) * 10,
                       length        = float(length),
                       bar_count     = int(count),
                       end_spacing   = float(end_mm),
                       casing_width  = float(cas["width_B"]),
                       casing_depth  = float(self.data["casing_H2"][dia]),
                       casing_h1     = float(self.data.get("casing_H1", 12)),
                       rebar_width   = float(var.get("b", 0.0)),
                       h             = h_def if h is None else float(h),
                       h_min         = h_min,
                       lu            = lu_def if lu is None else float(lu),
                       lu_min        = lu_min,
                       lu_max        = lu_max,
                       leg_name      = leg_name,
                       leg           = leg_def if leg is None else float(leg),
                       leg_range     = tuple(leg_range) if leg_range else None,
                       strip         = strip and stirrup)


# ---------------------------------------------------------------------------------------------------------------------
# specification
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class HBTSpec:
    """ full specification of one HBT element """

    casing      : str
    rows        : int
    rebar_type  : str
    type_text   : str
    anchor      : str
    connection  : str
    diameter    : float
    spacing     : float          # mm
    length      : float
    bar_count   : int            # per row
    end_spacing : float          # mm
    casing_width: float          # B
    casing_depth: float          # H2
    casing_h1   : float
    rebar_width : float          # b (double row, outer dimension)
    h           : float
    h_min       : float
    lu          : float
    lu_min      : float
    lu_max      : float
    leg_name    : str
    leg         : float
    leg_range   : tuple | None = None
    strip       : bool = False

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
    def article(self) -> str:
        """ order designation as in the catalogue, e.g. HBT 85 - 10/10 - 2 - 1250, h = 170, lü = 430 """

        prefix = self.casing.replace("HBT", "HBT-S", 1) if self.strip else self.casing
        text   = (f"{prefix} - {_fmt(self.diameter)}/{_fmt(self.spacing / 10)} - {self.rebar_type} - "
                  f"{_fmt(self.length)}, h = {_fmt(self.h)}, lü = {_fmt(self.lu)}")

        if self.leg_name:
            text += f", {self.leg_name} = {_fmt(self.leg)}"

        return text

    def check(self) -> list[str]:
        """ checks against the catalogue limits """

        warnings = []

        if self.h < self.h_min:
            warnings.append(f"h < hmin = {_fmt(self.h_min)}")

        if self.lu > self.lu_max:
            warnings.append(f"lü > lü,max = {_fmt(self.lu_max)}")

        if self.lu < self.lu_min:
            warnings.append(f"lü < {_fmt(self.lu_min)}")

        if self.leg_name and self.leg <= 0:
            warnings.append(f"{self.leg_name} must be > 0")

        if self.leg_range and not self.leg_range[0] <= self.leg <= self.leg_range[1]:
            warnings.append(f"b outside {self.leg_range[0]}...{self.leg_range[1]}")

        if self.rebar_type == "4" and not self.leg_range:
            warnings.append("Type 4 for this casing: on request")

        if self.end_spacing + (self.bar_count - 1) * self.spacing > self.length:
            warnings.append("bars do not fit into the casing length")

        return warnings


# ---------------------------------------------------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class HBTLayout:
    """ geometry of one HBT element in local coordinates """

    spec       : HBTSpec
    box_plates : list[tuple[Point, Point]] = field(default_factory=list)
    box_outline: tuple[Point, Point] = ((0, 0, 0), (0, 0, 0))
    bars       : list[list[Point]]   = field(default_factory=list)
    ref_point  : Point = (0.0, 0.0, 0.0)
    dim_point  : Point = (0.0, 0.0, 0.0)


def compute_layout(spec: HBTSpec, bar_state: int = BARS_STRAIGHTENED) -> HBTLayout:
    """ casing plates and bar centre lines in local coordinates """

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

    delivered = bar_state == BARS_DELIVERED
    z_face    = min(spec.diameter, depth / 2) if delivered else 0.0     # where the bar leaves the face
    x_limit   = length - SHEET_THICKNESS - spec.diameter                 # bent legs stay inside the casing
    rows_y    = spec.row_y_positions

    for x in spec.bar_x_positions:
        anchors = [_anchor(spec, x, y, z_face, idx) for idx, y in enumerate(rows_y)]   # face -> tip

        bent_len = max(0.0, min(spec.lu, x_limit - x))

        if spec.rows == 2 and spec.connection == "stirrup":
            y1, y2 = rows_y
            if delivered:
                conn = [(x, y1, z_face), (x + bent_len, y1, z_face), (x + bent_len, y2, z_face), (x, y2, z_face)]
            else:
                conn = [(x, y1, 0.0), (x, y1, -spec.lu), (x, y2, -spec.lu), (x, y2, 0.0)]
            layout.bars.append(_join(_join(anchors[0][::-1], conn), anchors[1]))
            continue

        conns = []
        for y in rows_y:
            if delivered:
                conns.append([(x, y, z_face), (x + bent_len, y, z_face)])
            else:
                conns.append([(x, y, 0.0), (x, y, -spec.lu)])

        if spec.anchor == "u_rows":
            y1, y2 = rows_y
            u_bar = [(x, y1, z_face), (x, y1, spec.h), (x, y2, spec.h), (x, y2, z_face)]
            layout.bars.append(_join(_join(conns[0][::-1], u_bar), conns[1]))
        else:
            for anchor, conn in zip(anchors, conns):
                layout.bars.append(_join(anchor[::-1], conn))

    layout.bars = [_clean(bar) for bar in layout.bars]

    return layout


def _anchor(spec: HBTSpec, x: float, y: float, z_face: float, row_index: int) -> list[Point]:
    """ anchor path in component 1, from the face to the tip """

    pts = [(x, y, z_face), (x, y, spec.h)]
    leg = spec.leg

    if spec.anchor == "hook":                       # leg across the casing width (-y)
        pts.append((x, y - leg, spec.h))
    elif spec.anchor in ("hook_in", "hook_out"):
        outward = -1.0 if row_index == 0 else 1.0
        sign    = outward if spec.anchor == "hook_out" else -outward
        pts.append((x, y + sign * leg, spec.h))
    elif spec.anchor == "loop_x":                   # schematic: leg along the casing length
        pts.append((x + leg, y, spec.h))

    return pts


def _join(first: list[Point], second: list[Point]) -> list[Point]:
    if first and second and math.dist(first[-1], second[0]) < 1e-6:
        return first + second[1:]
    return first + second


def _clean(polyline: list[Point]) -> list[Point]:
    """ remove zero-length segments """

    result: list[Point] = []
    for pnt in polyline:
        if not result or math.dist(result[-1], pnt) > 1e-6:
            result.append(pnt)
    return result


# ---------------------------------------------------------------------------------------------------------------------
# placement frame
# ---------------------------------------------------------------------------------------------------------------------

def _norm(vec: Point) -> Point:
    length = math.sqrt(sum(c * c for c in vec))
    return (vec[0] / length, vec[1] / length, vec[2] / length) if length > 1e-9 else (0.0, 0.0, 0.0)


def _cross(a: Point, b: Point) -> Point:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def placement_axes(ref_point: Point, dir_point: Point | None, face_plane: int, flip: bool,
                   default_dir: Point = (1.0, 0.0, 0.0)) -> tuple[Point, Point, Point]:
    """ local axes (x, y, z) in world coordinates; z points into component 1

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
        z_dir  = (normal[0] * sign, normal[1] * sign, normal[2] * sign)
        x_dir  = up if face_plane == FACE_VERTICAL_BOX_VERT else direction

    return x_dir, _norm(_cross(z_dir, x_dir)), z_dir


def local_to_world(pnt: Point, origin: Point, axes: tuple[Point, Point, Point]) -> Point:
    x_dir, y_dir, z_dir = axes
    return tuple(origin[i] + pnt[0] * x_dir[i] + pnt[1] * y_dir[i] + pnt[2] * z_dir[i] for i in range(3))  # type: ignore
