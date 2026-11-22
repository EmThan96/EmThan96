""" smoke test of HBTFixture.py with stubbed Allplan modules (checks the script flow, not Allplan itself) """

import os
import sys
import types
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonPartsScripts"))


class _P3:
    def __init__(self, *a):
        if len(a) == 1:
            a = (a[0].X, a[0].Y, a[0].Z)
        self.X, self.Y, self.Z = (a + (0.0, 0.0, 0.0))[:3]


class _Value:
    def __init__(self, value, name=""):
        self.value, self.name = value, name


def _install_stubs():
    geo = types.ModuleType("NemAll_Python_Geometry")
    geo.Point3D = _P3
    geo.Vector3D = _P3
    geo.Matrix3D = mock.MagicMock
    geo.AxisPlacement3D = mock.MagicMock()
    geo.BRep3D = mock.MagicMock()
    base = types.ModuleType("NemAll_Python_BaseElements")
    base.CommonProperties = mock.MagicMock()
    base.CreateElements = mock.MagicMock()
    base.DrawElementPreview = mock.MagicMock()
    stubs = {
        "NemAll_Python_Geometry": geo,
        "NemAll_Python_BaseElements": base,
        "NemAll_Python_BasisElements": mock.MagicMock(),
        "NemAll_Python_Precast": mock.MagicMock(),
        "CreateElementResult": mock.MagicMock(),
        "BuildingElementListService": mock.MagicMock(),
        "BuildingElement": mock.MagicMock(),
        "ScriptObjectInteractors": mock.MagicMock(),
        "ScriptObjectInteractors.OnCancelFunctionResult": mock.MagicMock(),
    }

    bso = types.ModuleType("BaseScriptObject")

    class BaseScriptObject:
        def __init__(self, data):
            self.document = data
            self.script_object_interactor = None

    bso.BaseScriptObject = BaseScriptObject
    bso.BaseScriptObjectData = object
    stubs["BaseScriptObject"] = bso

    pim = types.ModuleType("ScriptObjectInteractors.PointInteractor")

    class PointInteractorResult:
        def __init__(self):
            self.input_point = _P3(0, 0, 0)

    pim.PointInteractorResult = PointInteractorResult
    pim.PointInteractor = mock.MagicMock()
    stubs["ScriptObjectInteractors.PointInteractor"] = pim
    sys.modules.update(stubs)
    return base


def _build_ele():
    names = dict(Rows=2, Casing="HBT 55", RebarType="xx", Diameter="16", Spacing="99", ElementLength="1250",
                 HBTStrip=False, Article="", StandardDims=True, AnchorLength=0, ConnectionLength=0, LegName="",
                 LegLength=0, HMin=0, LuMax=0, CasingWidth=0, CasingDepth=0, RebarWidth=0, BarCount=0,
                 EndSpacing=0, InfoText="", CatalogueFile="", FacePlane=2, FlipSide=False, BarState=1,
                 CutBoxVolume=True, CommonProp=None, BarColor=6, InputMode=1, CasingList="", RebarTypeList="",
                 DiameterList="", SpacingList="", LengthList="")
    ele = types.SimpleNamespace(**{k: _Value(v, k) for k, v in names.items()})
    ele.REF_POINT, ele.DIR_POINT = 1, 2
    return ele


def test_full_flow():
    base = _install_stubs()
    import HBT.HBTFixture as mod

    ele = _build_ele()
    obj = mod.create_script_object(ele, "doc")

    # invalid selection was repaired and lists filled
    assert ele.Casing.value == "HBT 80"
    assert ele.Diameter.value == "8"
    assert ele.Spacing.value == "10"
    assert ele.DiameterList.value == "8|10"
    assert ele.BarCount.value == 12
    assert ele.AnchorLength.value == 170 and ele.ConnectionLength.value == 170
    assert ele.InfoText.value == "OK"

    obj.start_input()
    obj.pnt_result.input_point = _P3(1000, 2000, 0)
    obj.draw_preview()
    obj.start_next_input()                     # reference point
    assert ele.InputMode.value == ele.DIR_POINT

    obj.pnt_result.input_point = _P3(1000, 3000, 0)
    obj.draw_preview()
    obj.start_next_input()                     # direction point -> create
    assert base.CreateElements.called
    assert ele.InputMode.value == ele.REF_POINT

    ele.Rows.value = 1
    assert obj.modify_element_property("Rows", 1) is True
    assert ele.CasingList.value == "HBT 55|HBT 85|HBT 120"
    assert ele.LegName.value == "y"

    ele.StandardDims.value = False
    ele.AnchorLength.value = 100
    obj.modify_element_property("AnchorLength", 100)
    assert "hmin" in ele.InfoText.value
