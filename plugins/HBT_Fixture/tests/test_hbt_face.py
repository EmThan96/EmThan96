""" tests for the automatic face detection (pure Python) """

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonPartsScripts"))

from gbc_engineers.hbt_fixture import hbt_face as hf  # noqa: E402


def box(x0, y0, z0, x1, y1, z1, flip_some=False):
    """ cuboid as vertices + oriented face edges; flip_some reverses some loops (inward normals) """
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    loops = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    if flip_some:
        loops[2] = loops[2][::-1]
        loops[5] = loops[5][::-1]
    return v, [[(lp[i], lp[(i + 1) % 4]) for i in range(4)] for lp in loops]


@pytest.fixture
def wall():
    """ wall 3000 long (x), 200 thick (y), 2500 high (z) """
    return hf.make_solid(*box(0, 0, 0, 3000, 200, 2500, flip_some=True), source="wall")


def test_normals_outward_even_if_input_inward(wall):
    for face in wall.faces:
        probe = hf._add(face.centroid, hf._mul(face.normal, 1.0))
        assert not wall.is_inside(probe)
        assert wall.is_inside(hf._add(face.centroid, hf._mul(face.normal, -1.0)))


def test_find_face_and_axes(wall):
    face = hf.find_face([wall], [(500, 0, 1000), (1500, 0, 1000)])
    assert face.normal == pytest.approx((0, -1, 0))
    x, y, z = hf.face_axes(face, (500, 0, 1000), (1500, 0, 1000))
    assert x == pytest.approx((1, 0, 0)) and z == pytest.approx((0, 1, 0))     # h into the wall
    x, y, z = hf.face_axes(face, (500, 0, 1000), (1500, 0, 1000), flip=True)
    assert z == pytest.approx((0, -1, 0))


def test_edge_preference(wall):
    pts = [(500, 0, 2500), (1500, 0, 2500)]                         # on the top edge
    assert hf.find_face([wall], pts, prefer_horizontal=True).normal == pytest.approx((0, 0, 1))
    assert hf.find_face([wall], pts, prefer_horizontal=False).normal == pytest.approx((0, -1, 0))


def test_no_face_in_air(wall):
    assert hf.find_face([wall], [(500, -50, 1000)]) is None


def test_fit_warnings(wall):
    face = hf.find_face([wall], [(500, 0, 1000)])
    axes = hf.face_axes(face, (500, 0, 1000), (1500, 0, 1000))
    pts = [(500, 0, 1000), (1125, 0, 1000), (1750, 0, 1000)]
    assert hf.fit_warnings(face, [wall], pts, axes[2], 170, 390) == []
    assert any("leaves the concrete" in w for w in hf.fit_warnings(face, [wall], pts, axes[2], 250, 390))


def test_face_run_and_casing_on_face(wall):
    face = hf.find_face([wall], [(1000, 0, 1000)])
    run = hf.face_run(face, (1000, 0, 1000), (1, 0, 0), width=86, edge_distance=50)
    assert run[0] == pytest.approx((50, 0, 1000), abs=0.2) and run[1] == pytest.approx((2950, 0, 1000), abs=0.2)
    axes = hf.face_axes(face, run[0], run[1])
    assert hf.casing_on_face(face, run[0], axes, 1250, 86)
    assert not hf.casing_on_face(face, (2500, 0, 1000), axes, 1250, 86)       # runs past the wall end


def test_row_direction(wall):
    face = hf.find_face([wall], [(1000, 0, 1000)])
    assert abs(hf.row_direction(face)[2]) < 1e-9                              # horizontal on a vertical face
    assert hf.row_direction(face, box_vertical=True) == pytest.approx((0, 0, 1))
