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
        self.X, self.Y, self.Z = (tuple(a) + (0.0, 0.0, 0.0))[:3]


class _Value:
    def __init__(self, value, name=""):
        self.value, self.name = value, name


class _Path:
    def __init__(self):
        self.items = []

    def __iadd__(self, other):
        self.items.append(other)
        return self


def _install_stubs(tmp_usr):
    geo = types.ModuleType("NemAll_Python_Geometry")
    geo.Point3D = _P3
    geo.Vector3D = _P3
    geo.Matrix3D = mock.MagicMock
    geo.AxisPlacement3D = mock.MagicMock()
    geo.BRep3D = mock.MagicMock()
    geo.Line3D = mock.MagicMock()
    geo.Arc3D = mock.MagicMock()
    geo.Path3D = _Path
    geo.eOK = 0
    geo.CreateSweptBRep3D = mock.MagicMock(return_value=(0, "brep"))

    base = types.ModuleType("NemAll_Python_BaseElements")
    for name in ("CommonProperties", "CreateElements", "DrawElementPreview", "AttributeString", "AttributeSet",
                 "Attributes"):
        setattr(base, name, mock.MagicMock())
    base.AttributeService = mock.MagicMock()
    base.AttributeService.GetAttributeID = mock.MagicMock(
        side_effect=lambda doc, name: {"Plan_text": 100, "Answer 1": 101, "Answer_2": 102}.get(name, -1))

    settings = types.ModuleType("NemAll_Python_AllplanSettings")
    settings.AllplanPaths = mock.MagicMock()
    settings.AllplanPaths.GetUsrPath = mock.MagicMock(return_value=tmp_usr)

    stubs = {
        "NemAll_Python_Geometry": geo,
        "NemAll_Python_BaseElements": base,
        "NemAll_Python_AllplanSettings": settings,
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

    for key in [k for k in sys.modules if k.startswith("gbc_engineers")]:
        del sys.modules[key]
    sys.modules.update(stubs)
    return base, geo


def _build_ele(library_path):
    names = dict(Rows=2, Casing="HBT 55", RebarType="xx", Diameter="16", Spacing="99", ElementLength="1250",
                 CustomLength=1000, HBTStrip=False, StandardDims=True, AnchorLength=0, ConnectionLength=0,
                 LegName="", LegLength=0, HMin=0, LuMax=0, LMin=0, MandrelCatalogue=0, MandrelEC2=0,
                 CasingWidth=0, CasingDepth=0, RebarWidth=0, BarCount=0, EndSpacing=0, InfoText="",
                 CatalogueFile="", PlacementMode=1, FacePlane=2, VerticalFaceAngle=0, FlipSide=False, BarState=1,
                 CutBoxVolume=True, PlanText="", Answer1="Lot A", Answer2="", Answer3="", Answer4="", Answer5="",
                 LibraryPath=library_path, LibraryFolder="", LibraryStatus="", SavedItem="", CommonProp=None,
                 BarColor=6, InputMode=1, CasingList="", RebarTypeList="", DiameterList="", SpacingList="",
                 LengthList="", SavedList="")
    ele = types.SimpleNamespace(**{k: _Value(v, k) for k, v in names.items()})
    ele.REF_POINT, ele.DIR_POINT, ele.MODE_SINGLE, ele.MODE_POLYLINE = 1, 2, 1, 2
    ele.LOAD_SAVED, ele.REFRESH_LIBRARY = 1001, 1002
    return ele


def _click(obj, x, y, z=0):
    obj.pnt_result.input_point = _P3(x, y, z)
    obj.draw_preview()
    obj.start_next_input()


def test_single_and_library(tmp_path):
    base, geo = _install_stubs(str(tmp_path / "usr"))
    import gbc_engineers.hbt_fixture.HBTFixture as mod

    lib_dir = tmp_path / "company"
    ele = _build_ele(str(lib_dir))
    obj = mod.create_script_object(ele, "doc")

    assert (ele.Casing.value, ele.Diameter.value, ele.Spacing.value) == ("HBT 80", "8", "10")
    assert ele.MandrelCatalogue.value == 10 and ele.MandrelEC2.value == 4
    assert ele.InfoText.value == "OK"
    assert ele.LibraryStatus.value.startswith("New product")

    obj.start_input()
    _click(obj, 1000, 2000)
    _click(obj, 1000, 3000)
    assert base.CreateElements.call_count == 1
    assert geo.CreateSweptBRep3D.called
    assert len(os.listdir(lib_dir)) == 1

    # attributes: Plan_text + Answer 1 found, value set
    attr_values = [c.args for c in base.AttributeString.call_args_list]
    assert (100, ele.PlanText.value) in attr_values and (101, "Lot A") in attr_values

    # same input again -> reused, no new file
    obj._update_palette()
    assert ele.LibraryStatus.value.startswith("Existing product")
    _click(obj, 0, 0)
    _click(obj, 0, 500)
    assert len(os.listdir(lib_dir)) == 1

    # load from the library into the palette
    ele.Rows.value, ele.Answer1.value = 1, ""
    obj.modify_element_property("Rows", 1)
    ele.SavedItem.value = ele.SavedList.value.split("|")[1]
    obj.on_control_event(ele.LOAD_SAVED)
    assert ele.Rows.value == 2 and ele.Answer1.value == "Lot A" and ele.StandardDims.value is False


def test_blocked_custom_length_not_created(tmp_path):
    base, _ = _install_stubs(str(tmp_path / "usr"))
    import gbc_engineers.hbt_fixture.HBTFixture as mod

    ele = _build_ele(str(tmp_path / "company"))
    ele.Rows.value, ele.Casing.value = 1, "HBT 85"
    ele.ElementLength.value, ele.CustomLength.value = "Custom", 600
    obj = mod.create_script_object(ele, "doc")
    assert ele.InfoText.value.startswith("BLOCKED")

    obj.start_input()
    _click(obj, 0, 0)
    _click(obj, 1000, 0)
    assert base.CreateElements.call_count == 0


def test_polyline(tmp_path):
    base, _ = _install_stubs(str(tmp_path / "usr"))
    import gbc_engineers.hbt_fixture.HBTFixture as mod

    ele = _build_ele(str(tmp_path / "company"))
    ele.Rows.value, ele.Casing.value, ele.Diameter.value, ele.Spacing.value = 1, "HBT 85", "10", "15"
    ele.PlacementMode.value = 2
    obj = mod.create_script_object(ele, "doc")

    obj.start_input()
    _click(obj, 0, 0)
    _click(obj, 3300, 0)          # 1250 + 1250 + 800
    _click(obj, 3300, 2050)       # 1250 + 800
    obj.on_cancel_function()

    fixtures = base.CreateElements.call_args.args[2]
    assert len(fixtures) == 5
    assert len(os.listdir(tmp_path / "company")) == 2           # two distinct products (1250, 800)
    assert ele.InfoText.value == "5 elements created"
