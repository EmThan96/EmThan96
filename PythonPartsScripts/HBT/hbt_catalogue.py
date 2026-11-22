""" HBT catalogue access and fixture layout calculation.

This module is pure Python (no Allplan imports), so it can be tested outside Allplan.

Local fixture coordinate system (all values in mm):

* origin  = reference point = box end, on the formwork face, centre of the box width
* +x      = along the box length
* +y      = across the box width
* +z      = into the first pour (anchor side); -z = second pour (connection side)

The dimensioning point is the centre of the box on the formwork face: (L/2, 0, 0).
"""

from __future__ import annotations

import json
import math
import os

from dataclasses import dataclass, field

Point = tuple[float, float, float]

DEFAULT_CATALOGUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HBT_Catalogue.json")

# placement constants (must match the values in the .pyp file)
FACE_HORIZONTAL         = 1     # formwork face is horizontal, box along the click direction
FACE_VERTICAL_BOX_HORIZ = 2     # formwork face is vertical, box horizontal along the click direction
FACE_VERTICAL_BOX_VERT  = 3     # formwork face is vertical, box vertical, face along the click direction

BARS_STRAIGHTENED = 1           # installed state: connection legs straightened into the second pour
BARS_DELIVERED    = 2           # delivery state: connection legs bent into the box

SHEET_THICKNESS = 2.0           # visual thickness of the steel box walls


class CatalogueError(Exception):
    """ error in the catalogue data """


# ---------------------------------------------------------------------------------------------------------------------
# catalogue
# ---------------------------------------------------------------------------------------------------------------------

class HBTCatalogue:
    """ read access to the HBT catalogue JSON file """

    def __init__(self, data: dict):
        self.data  = data
        self.types = {t["code"]: t for t in data.get("types", [])}

        if not self.types:
            raise CatalogueError("Catalogue contains no types")

        for code, typ in self.types.items():
            self._validate_type(code, typ)

    @classmethod
    def load(cls, path: str = DEFAULT_CATALOGUE) -> HBTCatalogue:
        """ load the catalogue from a JSON file """

        with open(path, encoding="utf-8") as file:
            return cls(json.load(file))

    @staticmethod
    def _validate_type(code: str, typ: dict):
        rows = typ.get("rows")

        if rows not in (1, 2):
            raise CatalogueError(f"{code}: rows must be 1 or 2")

        if typ.get("anchor_shape") not in ("straight", "hook90", "u"):
            raise CatalogueError(f"{code}: unknown anchor_shape {typ.get('anchor_shape')}")

        if typ["anchor_shape"] == "u" and rows != 2:
            raise CatalogueError(f"{code}: anchor_shape 'u' needs rows = 2")

        if not typ.get("box_lengths"):
            raise CatalogueError(f"{code}: box_lengths missing")

        if not typ.get("diameters"):
            raise CatalogueError(f"{code}: diameters missing")

        for dia, var in typ["diameters"].items():
            for key in ("spacings", "box_width", "box_depth", "anchor_length", "connection_length"):
                if key not in var:
                    raise CatalogueError(f"{code} D{dia}: '{key}' missing")

            if rows == 2 and "row_distance" not in var:
                raise CatalogueError(f"{code} D{dia}: 'row_distance' missing for 2 rows")

    # ----- lists for the palette (all as strings, used in StringComboBox controls)

    def type_codes(self) -> list[str]:
        return list(self.types)

    def type_name(self, code: str) -> str:
        return self.types[code].get("name", code)

    def diameters(self, code: str) -> list[str]:
        return sorted(self.types[code]["diameters"], key=float)

    def spacings(self, code: str, dia: str) -> list[str]:
        return [_fmt(s) for s in self.types[code]["diameters"][dia]["spacings"]]

    def box_lengths(self, code: str) -> list[str]:
        return [_fmt(length) for length in self.types[code]["box_lengths"]]

    # ----- product specification

    def spec(self, code: str, dia: str, spacing: str, box_length: str) -> HBTSpec:
        """ build a validated product specification """

        typ = self.types[code]
        var = typ["diameters"][dia]

        spec = HBTSpec(type_code         = code,
                       type_name         = typ.get("name", code),
                       rows              = typ["rows"],
                       anchor_shape      = typ["anchor_shape"],
                       diameter          = float(dia),
                       spacing           = float(spacing),
                       box_length        = float(box_length),
                       box_width         = float(var["box_width"]),
                       box_depth         = float(var["box_depth"]),
                       anchor_length     = float(var["anchor_length"]),
                       connection_length = float(var["connection_length"]),
                       row_distance      = float(var.get("row_distance", 0.0)),
                       edge_distance     = float(typ.get("edge_distance", 50.0)),
                       hook_length       = float(typ.get("hook_length", 0.0)) * float(dia),
                       article_pattern   = typ.get("article_pattern", "{type} D{d}-{s} L={L}"))
        return spec

    def first_valid(self, code: str | None, dia: str | None, spacing: str | None,
                    box_length: str | None) -> tuple[str, str, str, str]:
        """ return a valid selection, keeping the given values where they are still valid """

        code    = code if code in self.types else self.type_codes()[0]
        dias    = self.diameters(code)
        dia     = dia if dia in dias else dias[0]
        spcs    = self.spacings(code, dia)
        spacing = spacing if spacing in spcs else spcs[0]
        lens    = self.box_lengths(code)
        box_length = box_length if box_length in lens else lens[0]

        return code, dia, spacing, box_length


def _fmt(value: float) -> str:
    """ format a number without trailing .0 """

    return str(int(value)) if float(value).is_integer() else str(value)


# ---------------------------------------------------------------------------------------------------------------------
# specification and layout
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class HBTSpec:
    """ full product specification of one HBT box """

    type_code        : str
    type_name        : str
    rows             : int
    anchor_shape     : str
    diameter         : float
    spacing          : float
    box_length       : float
    box_width        : float
    box_depth        : float
    anchor_length    : float
    connection_length: float
    row_distance     : float = 0.0
    edge_distance    : float = 50.0
    hook_length      : float = 0.0
    article_pattern  : str   = "{type} D{d}-{s} L={L}"

    @property
    def bar_count(self) -> int:
        """ bars per row: as many as fit with the spacing inside the box minus the edge distances """

        usable = self.box_length - 2 * self.edge_distance

        if usable < 0:
            return 0

        return int(math.floor(usable / self.spacing + 1e-9)) + 1

    @property
    def bar_x_positions(self) -> list[float]:
        """ x positions of the bars, centred in the box length """

        count = self.bar_count
        start = (self.box_length - (count - 1) * self.spacing) / 2

        return [start + i * self.spacing for i in range(count)]

    @property
    def row_y_positions(self) -> list[float]:
        return [0.0] if self.rows == 1 else [-self.row_distance / 2, self.row_distance / 2]

    @property
    def article(self) -> str:
        return self.article_pattern.format(type=self.type_code, d=_fmt(self.diameter),
                                           s=_fmt(self.spacing), L=_fmt(self.box_length))

    def check(self) -> list[str]:
        """ plausibility checks, returns a list of warnings """

        warnings = []

        if self.bar_count < 1:
            warnings.append("Box too short for the edge distance")

        if self.rows == 2 and self.row_distance + self.diameter > self.box_width:
            warnings.append("Row distance does not fit into the box width")

        if self.anchor_length <= self.box_depth:
            warnings.append("Anchor length is not longer than the box depth")

        return warnings


@dataclass
class HBTLayout:
    """ geometry of one HBT box in local coordinates """

    spec       : HBTSpec
    box_plates : list[tuple[Point, Point]] = field(default_factory=list)   # (min corner, max corner)
    box_outline: tuple[Point, Point] = ((0, 0, 0), (0, 0, 0))
    bars       : list[list[Point]]   = field(default_factory=list)          # bar centre lines
    ref_point  : Point = (0.0, 0.0, 0.0)
    dim_point  : Point = (0.0, 0.0, 0.0)


def compute_layout(spec: HBTSpec, bar_state: int = BARS_STRAIGHTENED) -> HBTLayout:
    """ calculate the box plates and bar centre lines in local coordinates """

    length = spec.box_length
    half_w = spec.box_width / 2
    depth  = spec.box_depth
    thick  = SHEET_THICKNESS

    layout = HBTLayout(spec=spec)

    # ----- box: open at the formwork face (z = 0), back plate at z = depth

    layout.box_outline = ((0.0, -half_w, 0.0), (length, half_w, depth))
    layout.box_plates  = [((0.0,            -half_w,         depth - thick), (length, half_w, depth)),     # back
                          ((0.0,            -half_w,         0.0),           (length, -half_w + thick, depth)),
                          ((0.0,             half_w - thick, 0.0),           (length, half_w, depth)),
                          ((0.0,            -half_w,         0.0),           (thick, half_w, depth)),      # ends
                          ((length - thick, -half_w,         0.0),           (length, half_w, depth))]

    layout.ref_point = (0.0, 0.0, 0.0)
    layout.dim_point = (length / 2, 0.0, 0.0)

    # ----- bars

    dia     = spec.diameter
    z_bend  = min(dia * 1.5, depth / 2)            # height of the bent leg inside the box (delivery state)
    z_anch  = spec.anchor_length
    rows_y  = spec.row_y_positions
    x_end   = length - spec.edge_distance / 2      # bent legs stay inside the box

    for x in spec.bar_x_positions:

        # connection legs (second pour side), one per row

        for y in rows_y:
            if bar_state == BARS_DELIVERED:
                leg = [(x, y, z_bend), (min(x + spec.connection_length, x_end), y, z_bend)]
            else:
                leg = [(x, y, 0.0), (x, y, -spec.connection_length)]

            if spec.anchor_shape == "u":
                layout.bars.append(leg)                     # anchor added once as U-bar below
            else:
                layout.bars.append(_join(_anchor_leg(spec, x, y, z_anch, z_bend, bar_state), leg))

        if spec.anchor_shape == "u":
            y1, y2 = rows_y
            z0 = z_bend if bar_state == BARS_DELIVERED else 0.0
            layout.bars.append([(x, y1, z0), (x, y1, z_anch), (x, y2, z_anch), (x, y2, z0)])

    return layout


def _anchor_leg(spec: HBTSpec, x: float, y: float, z_anch: float, z_bend: float, bar_state: int) -> list[Point]:
    """ anchor leg from its end to the face (or bend point), ordered towards the face """

    z0 = z_bend if bar_state == BARS_DELIVERED else 0.0

    pts: list[Point] = []

    if spec.anchor_shape == "hook90" and spec.hook_length > 0:
        pts.append((x + spec.hook_length, y, z_anch))

    pts.append((x, y, z_anch))
    pts.append((x, y, z0))

    return pts


def _join(first: list[Point], second: list[Point]) -> list[Point]:
    """ join two polylines that share the end / start point """

    if first and second and _dist(first[-1], second[0]) < 1e-6:
        return first + second[1:]

    return first + second


def _dist(p1: Point, p2: Point) -> float:
    return math.dist(p1, p2)


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
    """ calculate the local axes (x, y, z) in world coordinates

    Args:
        ref_point:   first click (reference point)
        dir_point:   second click (direction point) or None during the first input
        face_plane:  FACE_HORIZONTAL / FACE_VERTICAL_BOX_HORIZ / FACE_VERTICAL_BOX_VERT
        flip:        put the anchor side on the other side of the face
        default_dir: direction used when no valid direction point is given

    Returns:
        x, y and z direction (unit vectors); z points into the first pour
    """

    direction = default_dir

    if dir_point is not None:
        cand = (dir_point[0] - ref_point[0], dir_point[1] - ref_point[1], 0.0)    # direction in plan
        if math.hypot(cand[0], cand[1]) > 1e-6:
            direction = cand

    direction = _norm((direction[0], direction[1], 0.0))

    if direction == (0.0, 0.0, 0.0):
        direction = (1.0, 0.0, 0.0)

    up   = (0.0, 0.0, 1.0)
    sign = -1.0 if flip else 1.0

    if face_plane == FACE_HORIZONTAL:
        x_dir = direction
        z_dir = (0.0, 0.0, -sign)                                   # default: anchor goes down into the slab
    elif face_plane == FACE_VERTICAL_BOX_VERT:
        x_dir = up
        normal = _cross(up, direction)                              # left side of the click direction
        z_dir = (normal[0] * sign, normal[1] * sign, normal[2] * sign)
    else:
        x_dir = direction
        normal = _cross(up, direction)
        z_dir = (normal[0] * sign, normal[1] * sign, normal[2] * sign)

    y_dir = _cross(z_dir, x_dir)

    return x_dir, _norm(y_dir), z_dir


def local_to_world(pnt: Point, origin: Point, axes: tuple[Point, Point, Point]) -> Point:
    """ transform a local point to world coordinates (used for tests and checks) """

    x_dir, y_dir, z_dir = axes

    return tuple(origin[i] + pnt[0] * x_dir[i] + pnt[1] * y_dir[i] + pnt[2] * z_dir[i] for i in range(3))  # type: ignore
