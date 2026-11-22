""" tests for the pure Python part of the HBT fixture (no Allplan needed)

Expected values are taken from the HBT technical product information, pages 10-13.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonPartsScripts"))

from HBT import hbt_catalogue as hbt  # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return hbt.HBTCatalogue.load()


def T(cat, casing, code):
    return cat.rebar_types[code]["text"]


def test_casings(cat):
    assert cat.casing_codes(1) == ["HBT 55", "HBT 85", "HBT 120"]
    assert cat.casing_codes(2) == ["HBT 80", "HBT 120", "HBT 150", "HBT 190", "HBT 220"]


def test_rebar_types_per_casing(cat):
    codes = lambda r, c: [cat.rebar_type_code(t) for t in cat.rebar_type_texts(r, c)]
    assert codes(1, "HBT 85") == ["1", "2", "3", "4"]
    assert "4" not in codes(1, "HBT 120")                 # single-row HBT 120: type 4 on request
    assert "7" not in codes(2, "HBT 80")                  # footnote 3: type 7 not for HBT 80
    assert codes(2, "HBT 150") == ["5", "11", "22", "23", "33", "6", "7", "8", "9"]


def test_dependent_lists(cat):
    assert cat.diameters(1, "HBT 55") == ["8", "10"]
    assert cat.diameters(2, "HBT 150") == ["8", "10", "12"]
    assert cat.spacings(1, "HBT 85", "12") == ["10", "15", "20", "25"]
    assert cat.element_lengths() == ["1250", "800"]


def test_first_valid(cat):
    t1 = T(cat, "HBT 85", "1")
    assert cat.first_valid(1, "HBT 85", t1, "12", "15", "1250") == (1, "HBT 85", t1, "12", "15", "1250")
    rows, casing, text, dia, _, _ = cat.first_valid(2, "HBT 85", t1, "12", "15", "1250")
    assert (rows, casing, cat.rebar_type_code(text), dia) == (2, "HBT 80", "5", "8")


@pytest.mark.parametrize("length,s,count,a", [("1250", "10", 12, 75), ("1250", "15", 8, 100), ("1250", "20", 6, 125),
                                              ("1250", "25", 5, 125), ("800", "10", 8, 50), ("800", "15", 6, 25),
                                              ("800", "20", 4, 100), ("800", "25", 4, 25)])
def test_bar_layout_table(cat, length, s, count, a):
    spec = cat.spec(1, "HBT 85", T(cat, "", "1"), "10", s, length)
    assert spec.bar_count == count
    assert spec.end_spacing == a
    xs = spec.bar_x_positions
    assert xs[0] + (spec.length - xs[-1]) == pytest.approx(2 * a)     # symmetric, fills L


def test_single_row_standard(cat):
    # catalogue order example: HBT 85 - 10/10 - 2 - 1250
    spec = cat.spec(1, "HBT 85", T(cat, "", "1"), "12", "15", "1250")
    assert (spec.casing_width, spec.casing_depth) == (86, 36)
    assert (spec.h, spec.lu, spec.leg) == (170, 460, 110)          # h*, lü*, y
    assert spec.lu_max == 510 and spec.h_min == 120
    assert spec.check() == []
    assert spec.article == "HBT 85 - 12/15 - 1 - 1250, h = 170, lü = 460, y = 110"


def test_lu_max_short_element(cat):
    spec = cat.spec(1, "HBT 55", T(cat, "", "3"), "8", "25", "800")
    assert spec.lu_max == 480


def test_double_row_type5(cat):
    spec = cat.spec(2, "HBT 150", T(cat, "", "5"), "8", "15", "1250")   # application example page 20
    assert spec.rebar_width == 116 and spec.casing_width == 150 and spec.casing_depth == 24
    assert (spec.h, spec.lu) == (170, 320)
    assert spec.row_distance == 108


def test_stirrup_type(cat):
    spec = cat.spec(2, "HBT 220", T(cat, "", "7"), "12", "20", "1250", strip=True)
    assert spec.h_min == 170 and spec.h == 170
    assert spec.lu == 190 and spec.lu_max == 190 and spec.lu_min == 60
    assert spec.article.startswith("HBT-S 220 - 12/20 - 7 - 1250")


def test_checks(cat):
    spec = cat.spec(1, "HBT 85", T(cat, "", "1"), "10", "10", "1250", h=100, lu=999)
    msgs = " ".join(spec.check())
    assert "hmin" in msgs and "lü,max" in msgs
    spec = cat.spec(1, "HBT 85", T(cat, "", "4"), "10", "10", "1250", leg=100)
    assert any("b outside" in m for m in spec.check())


def test_layout_type1_straightened(cat):
    spec = cat.spec(1, "HBT 85", T(cat, "", "1"), "10", "15", "1250")
    lay = hbt.compute_layout(spec)
    assert len(lay.bars) == 8
    bar = lay.bars[0]
    assert bar[0] == pytest.approx((100, -95, 170))        # hook tip
    assert bar[-1] == pytest.approx((100, 0, -390))        # connection tip
    assert lay.dim_point == (625.0, 0.0, 0.0)


def test_layout_type5_one_bar_per_position(cat):
    spec = cat.spec(2, "HBT 150", T(cat, "", "5"), "8", "15", "1250")
    lay = hbt.compute_layout(spec)
    assert len(lay.bars) == spec.bar_count
    assert len(lay.bars[0]) == 6                            # leg - up - across - down - leg


def test_layout_stirrup_continuous(cat):
    spec = cat.spec(2, "HBT 150", T(cat, "", "6"), "10", "15", "1250")
    lay = hbt.compute_layout(spec)
    assert len(lay.bars) == spec.bar_count
    zs = [p[2] for p in lay.bars[0]]
    assert max(zs) == 170 and min(zs) == -spec.lu


def test_layout_delivered_inside_casing(cat):
    for rows, code, casing, dia in [(1, "1", "HBT 85", "10"), (2, "6", "HBT 150", "10"), (2, "5", "HBT 120", "12")]:
        spec = cat.spec(rows, casing, T(cat, "", code), dia, "10", "1250")
        lay = hbt.compute_layout(spec, hbt.BARS_DELIVERED)
        for bar in lay.bars:
            for x, _, z in bar:
                assert -1e-6 <= x <= spec.length
                assert z >= 0


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
    x, _, _ = hbt.placement_axes((5, 5, 5), (5, 5, 900), hbt.FACE_VERTICAL_BOX_HORIZ, False)
    assert x == pytest.approx((1, 0, 0))


def test_dim_point_world():
    axes = hbt.placement_axes((1000, 0, 0), (1000, 500, 0), hbt.FACE_VERTICAL_BOX_HORIZ, False)
    assert hbt.local_to_world((625, 0, 0), (1000, 0, 0), axes) == pytest.approx((1000, 625, 0))


def test_invalid_catalogue_rejected(cat):
    bad = dict(cat.data)
    bad["casings"] = [{"code": "X", "rows": 1, "width_B": 50, "rebar_types": ["5"], "diameters": {}}]
    with pytest.raises(hbt.CatalogueError):
        hbt.HBTCatalogue(bad)
