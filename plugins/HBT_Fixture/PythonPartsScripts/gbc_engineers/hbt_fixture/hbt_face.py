""" Automatic face detection for the HBT placement.

The user clicks points on a concrete surface. This module finds the planar face of a solid that contains
the clicked points and returns the outward face normal. The HBT is then oriented so that

* the anchor h goes INTO the solid (component 1, the concrete that is already modelled),
* the connection length lü points OUT of the solid (the connected component, concreted later),
* the casing length follows the clicked direction, projected onto the face.

The outward direction is computed here with a ray parity test, because the normals stored in Allplan
polyhedra are not reliably outward (seen on a Volume3D: end faces pointed inwards).

Pure Python (no Allplan imports): solids are given as vertex lists + face loops of vertex indices.
"""

from __future__ import annotations

__author__ = "Em Than - gbc engineers"

import math

from dataclasses import dataclass, field

Point = tuple[float, float, float]

ON_FACE_TOL = 1.0         # mm, distance of a clicked point to the face plane / face boundary
EPS         = 1e-9

# slightly skewed ray direction for the parity test (avoids hitting edges and vertices exactly)
_RAY_SKEW = (0.000137, 0.000291, 0.000419)


# ---------------------------------------------------------------------------------------------------------------------
# vector helpers
# ---------------------------------------------------------------------------------------------------------------------

def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a: Point, f: float) -> Point:
    return (a[0] * f, a[1] * f, a[2] * f)


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point, b: Point) -> Point:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a: Point) -> Point:
    length = math.sqrt(_dot(a, a))
    return _mul(a, 1.0 / length) if length > EPS else (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------------------------------------------------
# faces and solids
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Face:
    """ planar face with outward unit normal

    A face can have holes (openings): loops holds every closed boundary loop (outer loop and holes);
    inside / outside uses the even-odd rule over all loops.
    """

    loops   : list[list[Point]]
    normal  : Point                       # outward after Solid.orient()
    offset  : float = 0.0                 # plane: dot(normal, p) = offset
    centroid: Point = (0.0, 0.0, 0.0)     # a point ON the face (not in a hole), used for the orientation probe
    solid   : "Solid | None" = field(default=None, repr=False)
    group   : list["Face"] = field(default_factory=list, repr=False)   # coplanar faces of the solid (incl. self)

    def on_surface(self, pnt: Point, tol: float = ON_FACE_TOL) -> bool:
        """ point on this face or on a coplanar face of the same solid (one flat surface split into pieces) """

        return any(face.contains(pnt, tol) for face in (self.group or [self]))

    @property
    def points(self) -> list[Point]:
        """ outer loop (the loop with the largest area) """

        return max(self.loops, key=lambda lp: _dot(_newell_vector(lp), _newell_vector(lp)))

    def distance(self, pnt: Point) -> float:
        return _dot(self.normal, pnt) - self.offset

    def contains(self, pnt: Point, tol: float = ON_FACE_TOL) -> bool:
        """ point on the face plane and inside the face (holes excluded, boundary included within tol) """

        if abs(self.distance(pnt)) > max(tol, 1e-6):          # floor: rounding on inclined faces
            return False

        return _point_in_loops(pnt, self.loops, self.normal, tol)


@dataclass
class Solid:
    """ closed polyhedral solid """

    faces : list[Face]
    bbox  : tuple[Point, Point]
    source: object = None                 # e.g. element name, for messages

    def near(self, pnt: Point, tol: float = ON_FACE_TOL) -> bool:
        lo, hi = self.bbox
        return all(lo[k] - tol <= pnt[k] <= hi[k] + tol for k in range(3))

    def is_inside(self, pnt: Point) -> bool:
        """ ray parity test """

        direction = _norm(_add((0.0, 0.0, 1.0), _RAY_SKEW))
        hits = 0

        for face in self.faces:
            denom = _dot(face.normal, direction)
            if abs(denom) < EPS:
                continue
            t = (face.offset - _dot(face.normal, pnt)) / denom
            if t <= EPS:
                continue
            hit = _add(pnt, _mul(direction, t))
            if _point_in_loops(hit, face.loops, face.normal, 0.0):
                hits += 1

        return hits % 2 == 1

    def orient(self, probe: float = 0.5):
        """ make every face normal point outwards (probe point just in front of the face must be outside) """

        for face in self.faces:
            probe_pnt = _add(face.centroid, _mul(face.normal, probe))
            if self.is_inside(probe_pnt):
                face.normal = _mul(face.normal, -1.0)
                face.offset = -face.offset


def chain_loops(edges: list[tuple[int, int]]) -> list[list[int]]:
    """ closed vertex loops from the oriented edges of one face (outer boundary and holes) """

    nxt: dict[int, list[int]] = {}
    for start, end in edges:
        nxt.setdefault(start, []).append(end)

    loops = []
    used  = set()

    for start, end in edges:
        if (start, end) in used:
            continue
        loop = [start]
        used.add((start, end))
        cur = end
        while cur != start and len(loop) <= len(edges):
            loop.append(cur)
            cands = [n for n in nxt.get(cur, []) if (cur, n) not in used]
            if not cands:
                break
            used.add((cur, cands[0]))
            cur = cands[0]
        if cur == start and len(loop) >= 3:
            loops.append(loop)

    return loops


def make_solid(vertices: list[Point], faces_edges: list[list[tuple[int, int]]], source: object = None) -> Solid | None:
    """ solid from vertices and, per face, its oriented edges (start index, end index)

    Returns:
        solid with outward normals, or None if it has no usable face
    """

    faces = []

    for edges in faces_edges:
        loops = [[tuple(vertices[i]) for i in lp] for lp in chain_loops(edges)]
        if not loops:
            continue

        # net area vector of all loops (holes run the other way) -> plane normal
        normal = _norm(_sum([_newell_vector(lp) for lp in loops]))
        if normal == (0.0, 0.0, 0.0):
            continue

        offset = _dot(normal, loops[0][0])
        face   = Face(loops, normal, offset)
        face.centroid = _inner_point(face)
        faces.append(face)

    if not faces:
        return None

    lo = tuple(min(v[k] for v in vertices) for k in range(3))
    hi = tuple(max(v[k] for v in vertices) for k in range(3))

    solid = Solid(faces, (lo, hi), source)

    for face in faces:
        face.solid = solid

    solid.orient()

    # coplanar groups (same outward normal and plane), so a flat surface split into pieces acts as one surface
    for face in faces:
        face.group = [other for other in faces
                      if _dot(other.normal, face.normal) > 0.99999 and abs(other.offset - face.offset) < 0.5]

    return solid


# ---------------------------------------------------------------------------------------------------------------------
# face search and axes
# ---------------------------------------------------------------------------------------------------------------------

def faces_at(solids: list[Solid], pnt: Point, tol: float = ON_FACE_TOL) -> list[Face]:
    """ all visible (not buried) faces that contain the point """

    found = []

    for solid in solids:
        if not solid.near(pnt, tol):
            continue
        for face in solid.faces:
            if face.contains(pnt, tol) and not solid.is_inside(_add(pnt, _mul(face.normal, 0.5))):
                found.append(face)

    return found


def find_face(solids: list[Solid], points: list[Point], prefer_horizontal: bool | None = None,
              tol: float = ON_FACE_TOL) -> Face | None:
    """ face that contains all given points

    If several faces qualify (points on an edge between two faces), the preference decides:
    prefer_horizontal True -> face with the most vertical normal, False -> the most horizontal normal,
    None -> the first one found.
    """

    candidates = []

    for solid in solids:
        if not all(solid.near(p, tol) for p in points):
            continue
        for face in solid.faces:
            # first point on this face, the others anywhere on the same flat surface
            if face.contains(points[0], tol) and all(face.on_surface(p, tol) for p in points[1:]):
                # skip buried faces (solids made of overlapping parts): the front side must be outside
                if solid.is_inside(_add(points[0], _mul(face.normal, 0.5))):
                    continue
                candidates.append(face)

    if not candidates:
        return None

    if prefer_horizontal is None or len(candidates) == 1:
        return candidates[0]

    key = (lambda f: -abs(f.normal[2])) if prefer_horizontal else (lambda f: abs(f.normal[2]))
    return min(candidates, key=key)


def face_axes(face: Face, start: Point, end: Point | None, flip: bool = False,
              box_vertical: bool = False) -> tuple[Point, Point, Point] | None:
    """ local HBT axes on a face: x = casing length, z = into component 1 (anchor h)

    Args:
        face:         face with outward normal
        start, end:   clicked points (end None -> default direction)
        flip:         anchor out of the solid instead of into it (solid is the connected component)
        box_vertical: default direction for end None: steepest line of the face instead of global X

    Returns:
        (x, y, z) or None if no direction in the face plane exists
    """

    normal = face.normal
    z_dir  = normal if flip else _mul(normal, -1.0)

    def projected(vec: Point) -> Point:
        return _sub(vec, _mul(normal, _dot(vec, normal)))

    x_dir = (0.0, 0.0, 0.0)

    if end is not None:
        x_dir = _norm(projected(_sub(end, start)))

    if x_dir == (0.0, 0.0, 0.0):
        # default direction: preferred axis if it lies well in the face, else the axis that lies best in it
        defaults = ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)) if box_vertical else \
                   ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        proj = [projected(d) for d in defaults]
        best = proj[0] if _dot(proj[0], proj[0]) >= 0.5 else max(proj, key=lambda p: _dot(p, p))
        x_dir = _norm(best)

    if x_dir == (0.0, 0.0, 0.0):
        return None

    return x_dir, _norm(_cross(z_dir, x_dir)), z_dir


def fit_warnings(face: Face, solids: list[Solid], points: list[Point], z_dir: Point, h: float, lu: float,
                 flip: bool = False) -> list[str]:
    """ check that the embedded leg stays in the concrete of the face's solid and the free leg does not run
    into concrete

    Normal: h is embedded in the solid, lü is free. Flip: the solid is the connected component, so lü is
    embedded in it and h is free (h goes into concrete that is not modelled yet).

    Args:
        points: check points on the face (e.g. casing start, middle, end)
        z_dir:  direction of the anchor h

    Returns:
        warning texts (empty = fits)
    """

    warnings = []

    if flip:
        embedded, embedded_name, embedded_dir = lu, "lü", _mul(z_dir, -1.0)
        free, free_name, free_dir             = h, "h", z_dir
    else:
        embedded, embedded_name, embedded_dir = h, "h", z_dir
        free, free_name, free_dir             = lu, "lü", _mul(z_dir, -1.0)

    if face.solid is not None and embedded > 0:
        if any(not face.solid.is_inside(_add(p, _mul(embedded_dir, embedded))) for p in points):
            warnings.append(f"{embedded_name} = {embedded:.0f} leaves the concrete (opening / thin part / edge)")

    if free > 0:
        ends = [_add(p, _mul(free_dir, free)) for p in points]
        if any(s.near(e, 0.0) and s.is_inside(e) for s in solids for e in ends):
            warnings.append(f"{free_name} = {free:.0f} runs into concrete (other element / across an opening)")

    return warnings


def row_direction(face: Face, box_vertical: bool = False) -> Point:
    """ direction of an automatic row on the face

    * vertical face:   horizontal line in the face (box_vertical: steepest line, pointing up)
    * other faces:     direction of the longest boundary edge of the flat surface
    """

    normal = face.normal

    if abs(normal[2]) < 0.9:
        if box_vertical:
            up = _sub((0.0, 0.0, 1.0), _mul(normal, normal[2]))
            return _norm(up)
        return _norm(_cross((0.0, 0.0, 1.0), normal))

    best, best_len = (1.0, 0.0, 0.0), -1.0
    for part in (face.group or [face]):
        for loop in part.loops:
            for i, a in enumerate(loop):
                vec = _sub(loop[(i + 1) % len(loop)], a)
                vec = _sub(vec, _mul(normal, _dot(vec, normal)))
                length = math.sqrt(_dot(vec, vec))
                if length > best_len:
                    best, best_len = _mul(vec, 1.0 / length), length

    return best


def face_run(face: Face, pnt: Point, direction: Point, width: float, edge_distance: float = 50.0,
             step: float = 10.0, max_length: float = 100000.0) -> tuple[Point, Point] | None:
    """ free run on the flat surface through pnt along direction, wide enough for the casing

    The run stops at the face boundary, at openings and at recesses (holes in the face). Both ends are
    moved inwards by edge_distance.

    Returns:
        (start, end) or None if there is no free run at the point
    """

    d_dir = _norm(_sub(direction, _mul(face.normal, _dot(direction, face.normal))))
    y_dir = _norm(_cross(face.normal, d_dir))
    half  = width / 2
    tol   = 0.5                                   # on-surface tolerance; removed again from the run ends below

    def free(t: float) -> bool:
        p = _add(pnt, _mul(d_dir, t))
        return face.on_surface(p, tol) and face.on_surface(_add(p, _mul(y_dir, half)), tol) and \
               face.on_surface(_sub(p, _mul(y_dir, half)), tol)

    if not free(0.0):
        return None

    def reach(sign: float) -> float:
        t = 0.0
        while t + step <= max_length and free(sign * (t + step)):
            t += step
        lo, hi = t, t + step                      # refine the end to 0.1 mm
        for _ in range(7):
            mid = (lo + hi) / 2
            if free(sign * mid):
                lo = mid
            else:
                hi = mid
        return lo

    t_hi = reach(1.0) - tol - edge_distance
    t_lo = -(reach(-1.0) - tol) + edge_distance

    if t_hi - t_lo <= 0:
        return None

    return _add(pnt, _mul(d_dir, t_lo)), _add(pnt, _mul(d_dir, t_hi))


def casing_on_face(face: Face, origin: Point, axes: tuple[Point, Point, Point], length: float, width: float,
                   tol: float = 2.0) -> bool:
    """ the casing footprint (length x width, starting at origin, centred across) lies on the face

    Checked at the 4 corners and the 2 mid points of the long sides.
    """

    x_dir, y_dir, _ = axes
    half = width / 2

    for t in (0.0, length / 2, length):
        for s in (-half, half):
            pnt = _add(_add(origin, _mul(x_dir, t)), _mul(y_dir, s))
            if not face.on_surface(pnt, tol):
                return False

    return True


# ---------------------------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------------------------

def _sum(pts: list[Point]) -> Point:
    return (sum(p[0] for p in pts), sum(p[1] for p in pts), sum(p[2] for p in pts))


def _newell_vector(pts: list[Point]) -> Point:
    """ area vector of a closed loop (length = 2 x area, direction by the loop orientation) """

    nx = ny = nz = 0.0
    for i, cur in enumerate(pts):
        nxt = pts[(i + 1) % len(pts)]
        nx += (cur[1] - nxt[1]) * (cur[2] + nxt[2])
        ny += (cur[2] - nxt[2]) * (cur[0] + nxt[0])
        nz += (cur[0] - nxt[0]) * (cur[1] + nxt[1])
    return (nx, ny, nz)


def _newell_normal(pts: list[Point]) -> Point:
    return _norm(_newell_vector(pts))


def _inner_point(face: Face) -> Point:
    """ a point inside the face (not in a hole, not on the boundary) for the orientation probe """

    outer = face.points
    cand  = _mul(_sum(outer), 1.0 / len(outer))
    if _point_in_loops(cand, face.loops, face.normal, 0.0) and not _point_in_loops(cand, face.loops, face.normal, 0.5, True):
        return cand

    # centroids of fan triangles, then points between them and the loop vertices
    p0 = outer[0]
    for i in range(1, len(outer) - 1):
        tri = _mul(_add(_add(p0, outer[i]), outer[i + 1]), 1.0 / 3.0)
        if _point_in_loops(tri, face.loops, face.normal, 0.0) and not _point_in_loops(tri, face.loops, face.normal, 0.5, True):
            return tri

    for lp in face.loops:
        for i, a in enumerate(lp):
            b = lp[(i + 1) % len(lp)]
            mid = _mul(_add(a, b), 0.5)
            for side in (1.0, -1.0):
                probe = _add(mid, _mul(_norm(_cross(face.normal, _sub(b, a))), 2.0 * side))
                if _point_in_loops(probe, face.loops, face.normal, 0.0) and \
                   not _point_in_loops(probe, face.loops, face.normal, 0.5, True):
                    return probe

    return cand


def _point_in_loops(pnt: Point, loops: list[list[Point]], normal: Point, tol: float,
                    boundary_only: bool = False) -> bool:
    """ 2D point-in-face test in the face plane, even-odd rule over all loops (holes excluded)

    Points within tol of a boundary count as inside. boundary_only = True: only the boundary test.
    """

    # drop the dominant normal axis
    ax = max(range(3), key=lambda k: abs(normal[k]))
    u, v = [k for k in range(3) if k != ax]

    px, py = pnt[u], pnt[v]
    inside = False

    for loop in loops:
        pts2 = [(p[u], p[v]) for p in loop]

        for i, (x1, y1) in enumerate(pts2):
            x2, y2 = pts2[(i + 1) % len(pts2)]

            if tol > 0 and _dist_point_segment_2d(px, py, x1, y1, x2, y2) <= tol:
                return True

            if not boundary_only and (y1 > py) != (y2 > py):
                x_cross = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if px < x_cross:
                    inside = not inside

    return False if boundary_only else inside


def _point_in_polygon(pnt: Point, poly: list[Point], normal: Point, tol: float) -> bool:
    return _point_in_loops(pnt, [poly], normal, tol)


def _dist_point_segment_2d(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    len2   = dx * dx + dy * dy
    t      = 0.0 if len2 < EPS else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
