""" tests for the pure Python part of the HBT fixture (no Allplan needed)

Expected values are taken from the HBT technical product information HBT 22-E, pages 10-13 and 22.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonPartsScripts"))

from HBT import hbt_catalogue as hbt  # noqa: E402

DOUBLE = {"5", "11", "22", "23", "33", "6", "7", "8", "9"}


@pytest.fixture(scope="module")
def cat():
    return hbt.HBTCatalogue.load()


def spec(cat, casing, rtype, dia, s, length, **kw):
    rows = 2 if rtype in DOUBLE else 1
    return cat.spec(rows, casing, cat.rebar_types[rtype]["text"], dia, s, length, **kw)


# ----- catalogue lists

def test_casings(cat):
    assert cat.casing_codes(1) == ["HBT 55", "HBT 85", "HBT 120"]
    assert cat.casing_codes(2) == ["HBT 80", "HBT 120", "HBT 150", "HBT 190", "HBT 220"]


def test_rebar_types_per_casing(cat):
    codes = lambda r, c: [cat.rebar_type_code(t) for t in cat.rebar_type_texts(r, c)]
    assert codes(1, "HBT 85") == ["1", "2", "3", "4"]
    assert "4" not in codes(1, "HBT 120")
    assert "7" not in codes(2, "HBT 80")
    assert codes(2, "HBT 150") == ["5", "11", "22", "23", "33", "6", "7", "8", "9"]


def test_dependent_lists(cat):
    assert cat.diameters(1, "HBT 55") == ["8", "10"]
    assert cat.diameters(2, "HBT 150") == ["8", "10", "12"]
    assert cat.spacings(1, "HBT 85", "12") == ["10", "15", "20", "25"]


def test_first_valid(cat):
    rows, casing, text, dia, _ = cat.first_valid(2, "HBT 85", "x", "12", "15")
    assert (rows, casing, cat.rebar_type_code(text), dia) == (2, "HBT 80", "5", "8")


# ----- bar layout

@pytest.mark.parametrize("length,s,count,a", [(1250, "10", 12, 75), (1250, "15", 8, 100), (1250, "20", 6, 125),
                                              (1250, "25", 5, 125), (800, "10", 8, 50), (800, "15", 6, 25),
                                              (800, "20", 4, 100), (800, "25", 4, 25)])
def test_bar_layout_table(cat, length, s, count, a):
    sp = spec(cat, "HBT 85", "1", "10", s, length)
    assert (sp.bar_count, sp.end_spacing, sp.standard_length) == (count, a, True)


def test_custom_layout_a_min_25(cat):
    sp = spec(cat, "HBT 85", "1", "10", "15", 1000)
    # n = floor((1000 - 50) / 150) + 1 = 7, a = (1000 - 900) / 2 = 50
    assert (sp.bar_count, sp.end_spacing, sp.standard_length) == (7, 50, False)


# ----- dimensions and designation

def test_single_row_standard(cat):
    sp = spec(cat, "HBT 85", "1", "12", "15", 1250)
    assert (sp.casing_width, sp.casing_depth, sp.h, sp.lu, sp.leg, sp.lu_max) == (86, 36, 170, 460, 110, 510)
    assert sp.errors() == []
    assert sp.designation == "HBT 85 - 12/15 - 1 - 1250, h = 170, lü = 460, y = 110"


def test_double_row_type5(cat):
    sp = spec(cat, "HBT 150", "5", "8", "15", 1250)      # application example page 20
    assert (sp.rebar_width, sp.row_distance, sp.h, sp.lu) == (116, 108, 170, 320)


def test_stirrup_type(cat):
    sp = spec(cat, "HBT 220", "7", "12", "20", 1250, strip=True)
    assert (sp.h_min, sp.lu, sp.lu_max, sp.lu_min) == (170, 190, 190, 60)
    assert sp.designation.startswith("HBT-S 220 - 12/20 - 7 - 1250")


# ----- hard limits

def test_errors_h_lu_leg(cat):
    msgs = " ".join(spec(cat, "HBT 85", "1", "10", "10", 1250, h=100, lu=999).errors())
    assert "hmin" in msgs and "lü,max" in msgs
    assert any("b outside" in m for m in spec(cat, "HBT 85", "4", "10", "10", 1250, leg=100).errors())
    assert not any("on request" in m for m in spec(cat, "HBT 120", "1", "10", "10", 1250).errors())


def test_lu_max_column_by_length(cat):
    assert spec(cat, "HBT 55", "3", "8", "25", 1250).lu_max == 600
    assert spec(cat, "HBT 55", "3", "8", "25", 800).lu_max == 480
    assert spec(cat, "HBT 55", "3", "8", "25", 1000).lu_max == 480     # custom 800..1250 -> column L >= 800


def test_min_length_table_page22(cat):
    # Ø10 / s = 15: Lmin = 750 with lü standard 390
    sp = spec(cat, "HBT 85", "1", "10", "15", 740)
    assert sp.minimum_length == 750
    assert any("Lmin" in m for m in sp.errors())
    assert spec(cat, "HBT 85", "1", "10", "15", 750).errors() == []


def test_min_length_non_standard_lu_blocks_below_800(cat):
    sp = spec(cat, "HBT 85", "1", "10", "15", 760, lu=400)   # lü > lü standard -> Lmin = 800
    assert sp.minimum_length == 800
    assert sp.errors()


def test_stirrups_below_800_blocked(cat):
    assert spec(cat, "HBT 150", "6", "10", "15", 790).errors()
    assert spec(cat, "HBT 150", "6", "10", "15", 800).errors() == []


def test_custom_above_1250_blocked(cat):
    assert any("on request" in m for m in spec(cat, "HBT 85", "1", "10", "15", 1300).errors())


# ----- layout

def test_layout_type1(cat):
    sp = spec(cat, "HBT 85", "1", "10", "15", 1250)
    lay = hbt.compute_layout(sp)
    assert len(lay.bars) == 8
    bar = lay.bars[0]
    assert bar.points[0] == pytest.approx((100, -95, 170))
    assert bar.points[-1] == pytest.approx((100, 0, -390))
    assert bar.mandrels[0] == 4                              # hook y: EC2
    assert lay.dim_point == (625.0, 0.0, 0.0)


def test_layout_type2_catalogue_mandrel(cat):
    bar = hbt.compute_layout(spec(cat, "HBT 85", "2", "10", "15", 1250)).bars[0]
    assert bar.mandrels[0] == 10                             # leg b: D = 10Ø


def test_layout_type5_and_stirrup(cat):
    sp = spec(cat, "HBT 150", "5", "8", "15", 1250)
    assert len(hbt.compute_layout(sp).bars) == sp.bar_count
    sp = spec(cat, "HBT 150", "6", "10", "15", 1250)
    bar = hbt.compute_layout(sp).bars[0]
    zs = [p[2] for p in bar.points]
    assert max(zs) == 170 and min(zs) == -sp.lu


def test_layout_delivered_inside_casing(cat):
    for code, casing, dia in [("1", "HBT 85", "10"), ("6", "HBT 150", "10"), ("5", "HBT 120", "12")]:
        sp = spec(cat, casing, code, dia, "10", 1250)
        for bar in hbt.compute_layout(sp, hbt.BARS_DELIVERED).bars:
            for x, _, z in bar.points:
                assert -1e-6 <= x <= sp.length and z >= 0


# ----- fillet algorithm

def _check_continuous(segments):
    for a, b in zip(segments[:-1], segments[1:]):
        assert a.end == pytest.approx(b.start)


def test_fillet_90_degree(cat):
    bar = hbt.Bar([(0, 0, 0), (100, 0, 0), (100, 100, 0)], [4])
    segs, reduced = hbt.fillet_bar(bar, 10)
    assert not reduced
    assert [type(s).__name__ for s in segs] == ["LineSeg", "ArcSeg", "LineSeg"]
    arc = segs[1]
    assert arc.radius == 25 and arc.angle == pytest.approx(math.pi / 2)      # R = (4*10 + 10) / 2
    assert arc.start == pytest.approx((75, 0, 0)) and arc.end == pytest.approx((100, 25, 0))
    assert hbt.arc_point(arc, arc.angle) == pytest.approx(arc.end)
    assert hbt.arc_point(arc, arc.angle / 2) == pytest.approx((75 + 25 * math.sin(math.pi / 4),
                                                              25 - 25 * math.cos(math.pi / 4), 0))
    _check_continuous(segs)


def test_fillet_reduces_radius_when_too_short():
    bar = hbt.Bar([(0, 0, 0), (0, 0, 100), (30, 0, 100), (30, 0, 0)], [4, 4])   # U with 30 mm width
    segs, reduced = hbt.fillet_bar(bar, 10)
    assert reduced
    arcs = [s for s in segs if isinstance(s, hbt.ArcSeg)]
    assert all(a.radius == pytest.approx(15) for a in arcs)
    _check_continuous(segs)


def test_fillet_all_layout_bars(cat):
    for code, casing, dia in [("1", "HBT 85", "12"), ("7", "HBT 150", "10"), ("5", "HBT 220", "12"),
                              ("22", "HBT 190", "8"), ("4", "HBT 85", "10")]:
        sp = spec(cat, casing, code, dia, "15", 1250)
        for state in (hbt.BARS_STRAIGHTENED, hbt.BARS_DELIVERED):
            for bar in hbt.compute_layout(sp, state).bars:
                segs, _ = hbt.fillet_bar(bar, sp.diameter)
                _check_continuous(segs)
                assert segs[0].start == pytest.approx(bar.points[0])
                assert segs[-1].end == pytest.approx(bar.points[-1])


# ----- split algorithm

@pytest.fixture(scope="module")
def valid(cat):
    return lambda length: not spec(cat, "HBT 85", "1", "10", "15", length).errors()


@pytest.mark.parametrize("total,expected", [(1250, [1250]), (2050, [1250, 800]), (3300, [1250, 1250, 800]),
                                            (2500, [1250, 1250]), (1000, [1000]), (2251, [1250, 1001]),
                                            (4321, [1250, 1250, 800, 1021])])
def test_split_length(valid, total, expected):
    assert hbt.split_length(total, valid) == expected


@pytest.mark.parametrize("total", [500, 700, 1300])
def test_split_length_impossible(valid, total):
    assert hbt.split_length(total, valid) is None


def test_split_lengths_all_valid(valid):
    for total in range(750, 9000, 37):
        result = hbt.split_length(total, valid)
        if result is not None:
            assert sum(result) == total
            assert all(valid(x) for x in result)


def test_split_skips_invalid_800(cat):
    # Ø8 / s = 15 with lü = 510: valid for 1250 (lü,max 510) but not for 800 (lü,max 430)
    check = lambda length: not spec(cat, "HBT 55", "3", "8", "15", length, lu=510).errors()
    assert hbt.split_length(2500, check) == [1250, 1250]
    assert hbt.split_length(2050, check) is None


# ----- placement frames

def _right_handed(axes):
    x, y, z = axes
    dot = lambda a, b: sum(i * j for i, j in zip(a, b))
    for v in axes:
        assert math.isclose(dot(v, v), 1.0, abs_tol=1e-9)
    assert abs(dot(x, y)) < 1e-9 and abs(dot(y, z)) < 1e-9 and abs(dot(x, z)) < 1e-9
    assert hbt._cross(x, y) == pytest.approx(z)


@pytest.mark.parametrize("face", [hbt.FACE_HORIZONTAL, hbt.FACE_VERTICAL_BOX_HORIZ, hbt.FACE_VERTICAL_BOX_VERT])
@pytest.mark.parametrize("flip", [False, True])
def test_axes_orthonormal(face, flip):
    _right_handed(hbt.placement_axes((100, 200, 300), (400, 600, 300), face, flip))


def test_axes_cases():
    x, _, z = hbt.placement_axes((0, 0, 0), (0, 1000, 0), hbt.FACE_HORIZONTAL, False)
    assert x == pytest.approx((0, 1, 0)) and z == pytest.approx((0, 0, -1))
    x, y, z = hbt.placement_axes((0, 0, 0), (1000, 0, 0), hbt.FACE_VERTICAL_BOX_VERT, False)
    assert x == pytest.approx((0, 0, 1)) and y == pytest.approx((1, 0, 0)) and z == pytest.approx((0, 1, 0))


def test_segment_axes():
    axes = hbt.segment_axes((0, 0, 0), (3000, 0, 0), hbt.FACE_VERTICAL_BOX_HORIZ, False)
    _right_handed(axes)
    assert axes[2] == pytest.approx((0, 1, 0))
    axes = hbt.segment_axes((0, 0, 0), (0, 0, 3300), hbt.FACE_VERTICAL_BOX_HORIZ, False, 90)   # vertical wall joint
    _right_handed(axes)
    assert axes[0] == pytest.approx((0, 0, 1)) and axes[2] == pytest.approx((0, 1, 0))
    assert hbt.segment_axes((0, 0, 0), (0, 0, 100), hbt.FACE_HORIZONTAL, False) is None
    assert hbt.segment_axes((1, 1, 1), (1, 1, 1), hbt.FACE_HORIZONTAL, False) is None


def test_invalid_catalogue_rejected(cat):
    bad = dict(cat.data)
    bad["casings"] = [{"code": "X", "rows": 1, "width_B": 50, "rebar_types": ["5"], "diameters": {}}]
    with pytest.raises(hbt.CatalogueError):
        hbt.HBTCatalogue(bad)
