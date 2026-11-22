""" tests for the pure Python part of the HBT fixture (no Allplan needed) """

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonPartsScripts"))

from HBT import hbt_catalogue as hbt  # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return hbt.HBTCatalogue.load()


def test_catalogue_loads_all_types(cat):
    assert cat.type_codes() == ["HBT-1R", "HBT-1R-H", "HBT-2R", "HBT-2R-U"]


def test_dependent_lists(cat):
    assert cat.diameters("HBT-1R") == ["8", "10", "12", "14", "16"]
    assert cat.spacings("HBT-1R", "16") == ["150", "200", "250"]
    assert cat.box_lengths("HBT-2R") == ["1250"]


def test_first_valid_keeps_and_repairs(cat):
    assert cat.first_valid("HBT-1R", "12", "150", "1250") == ("HBT-1R", "12", "150", "1250")
    # D16 does not exist for HBT-2R -> first diameter, spacing kept if valid
    assert cat.first_valid("HBT-2R", "16", "150", "1250") == ("HBT-2R", "8", "150", "1250")
    assert cat.first_valid("XXX", None, None, None)[0] == "HBT-1R"


def test_bar_count_and_positions(cat):
    spec = cat.spec("HBT-1R", "12", "150", "1250")
    # usable 1250 - 2*50 = 1150 -> 7 spaces + 1 = 8 bars
    assert spec.bar_count == 8
    xs = spec.bar_x_positions
    assert xs[0] == pytest.approx(1250 - xs[-1])           # centred
    assert xs[1] - xs[0] == pytest.approx(150)
    assert spec.article == "HBT-1R D12-150 L=1250"
    assert spec.check() == []


def test_layout_straight_single_row(cat):
    spec = cat.spec("HBT-1R", "12", "150", "1250")
    lay = hbt.compute_layout(spec, hbt.BARS_STRAIGHTENED)
    assert len(lay.bars) == 8
    bar = lay.bars[0]
    assert bar[0][2] == pytest.approx(spec.anchor_length)
    assert bar[-1][2] == pytest.approx(-spec.connection_length)
    assert lay.ref_point == (0.0, 0.0, 0.0)
    assert lay.dim_point == (625.0, 0.0, 0.0)
    assert len(lay.box_plates) == 5


def test_layout_delivered_legs_inside_box(cat):
    spec = cat.spec("HBT-1R", "12", "150", "1250")
    lay = hbt.compute_layout(spec, hbt.BARS_DELIVERED)
    for bar in lay.bars:
        for x, _, z in bar[1:]:
            assert 0 <= x <= spec.box_length
            assert 0 <= z <= spec.anchor_length


def test_layout_u_anchor(cat):
    spec = cat.spec("HBT-2R-U", "10", "200", "1250")
    lay = hbt.compute_layout(spec)
    # per bar position: 2 connection legs + 1 U-bar
    assert len(lay.bars) == 3 * spec.bar_count
    u_bars = [b for b in lay.bars if len(b) == 4]
    assert len(u_bars) == spec.bar_count
    assert abs(u_bars[0][1][1] - u_bars[0][2][1]) == pytest.approx(spec.row_distance)


def test_layout_hook(cat):
    spec = cat.spec("HBT-1R-H", "10", "150", "1250")
    lay = hbt.compute_layout(spec)
    assert lay.bars[0][0][0] - lay.bars[0][1][0] == pytest.approx(100)    # 10 * d


def _is_right_handed_orthonormal(axes):
    x, y, z = axes
    dot = lambda a, b: sum(i * j for i, j in zip(a, b))
    for v in axes:
        assert math.isclose(dot(v, v), 1.0, abs_tol=1e-9)
    assert abs(dot(x, y)) < 1e-9 and abs(dot(y, z)) < 1e-9 and abs(dot(x, z)) < 1e-9
    assert hbt._cross(x, y) == pytest.approx(z)


@pytest.mark.parametrize("face", [hbt.FACE_HORIZONTAL, hbt.FACE_VERTICAL_BOX_HORIZ, hbt.FACE_VERTICAL_BOX_VERT])
@pytest.mark.parametrize("flip", [False, True])
def test_axes_orthonormal(face, flip):
    axes = hbt.placement_axes((100, 200, 300), (400, 600, 300), face, flip)
    _is_right_handed_orthonormal(axes)


def test_axes_horizontal_face():
    x, _, z = hbt.placement_axes((0, 0, 0), (0, 1000, 0), hbt.FACE_HORIZONTAL, False)
    assert x == pytest.approx((0, 1, 0))
    assert z == pytest.approx((0, 0, -1))


def test_axes_vertical_box_vertical():
    x, y, z = hbt.placement_axes((0, 0, 0), (1000, 0, 0), hbt.FACE_VERTICAL_BOX_VERT, False)
    assert x == pytest.approx((0, 0, 1))
    assert y == pytest.approx((1, 0, 0))
    assert z == pytest.approx((0, 1, 0))


def test_axes_without_direction_point_uses_default():
    x, _, _ = hbt.placement_axes((5, 5, 5), None, hbt.FACE_VERTICAL_BOX_HORIZ, False)
    assert x == pytest.approx((1, 0, 0))
    x, _, _ = hbt.placement_axes((5, 5, 5), (5, 5, 900), hbt.FACE_VERTICAL_BOX_HORIZ, False)  # vertical click
    assert x == pytest.approx((1, 0, 0))


def test_dim_point_world():
    axes = hbt.placement_axes((1000, 0, 0), (1000, 500, 0), hbt.FACE_VERTICAL_BOX_HORIZ, False)
    assert hbt.local_to_world((625, 0, 0), (1000, 0, 0), axes) == pytest.approx((1000, 625, 0))


def test_invalid_catalogue_rejected():
    with pytest.raises(hbt.CatalogueError):
        hbt.HBTCatalogue({"types": [{"code": "X", "rows": 1, "anchor_shape": "u",
                                     "box_lengths": [1], "diameters": {"8": {}}}]})
