""" HBT Fixture - places HBT rebend connections as Allplan precast point fixtures.

Placement modes
    1. Single element: click the reference point, then the direction point.
    2. Polyline:       click any number of points; ESC creates the elements. Every segment is filled with
                       1250 / 800 standard elements and, if needed, custom elements (catalogue limits checked).

Each created fixture
    * AllplanPrecast.FixturePlacementElement (point fixture)
      - slide e3D_VIEW               casing and bars (bends swept along arcs with the mandrel radius)
      - slide e3D_VIEW_OUTLINE_VOLUME casing volume (optional cut in the precast element)
      - slide eMEASURE_POINTS        dimensioning point (centre of the casing on the face)
      - insertion point = reference point (casing end on the face)
    * attributes Plan_text (catalogue order designation, automatic) and Answer 1..5 (user input)
    * a record in the company library folder (one JSON file per product); identical products are
      reused (same record, same fixture hash)
"""

from __future__ import annotations

import hashlib
import math

from typing import TYPE_CHECKING, Any

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_BasisElements as AllplanBasisEle
import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_Precast as AllplanPrecast

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from CreateElementResult import CreateElementResult
from BuildingElementListService import BuildingElementListService

from ScriptObjectInteractors.OnCancelFunctionResult import OnCancelFunctionResult
from ScriptObjectInteractors.PointInteractor import PointInteractor, PointInteractorResult

from HBT import hbt_catalogue as hbt
from HBT import hbt_library as hlib

if TYPE_CHECKING:
    from __BuildingElementStubFiles.HBTFixtureBuildingElement import HBTFixtureBuildingElement as BuildingElement  # type: ignore
else:
    from BuildingElement import BuildingElement

print('Load HBTFixture.py')

CUSTOM_LENGTH = "Custom"
ARC_FALLBACK_SEGMENTS = 8


def check_allplan_version(_build_ele: BuildingElement,
                          _version  : str) -> bool:
    """ Check the current Allplan version

    Args:
        _build_ele: building element with the parameter properties
        _version:   the current Allplan version

    Returns:
        True
    """

    return True


def create_script_object(build_ele         : BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    """ Creation of the script object

    Args:
        build_ele:          building element with the parameter properties
        script_object_data: script object data

    Returns:
        created script object
    """

    return HBTFixture(build_ele, script_object_data)


class HBTFixture(BaseScriptObject):
    """ Script object for the placement of HBT fixtures """

    def __init__(self,
                 build_ele         : BuildingElement,
                 script_object_data: BaseScriptObjectData):
        """ Initialization

        Args:
            build_ele:          building element with the parameter properties
            script_object_data: script object data
        """

        super().__init__(script_object_data)

        self.build_ele  = build_ele
        self.pnt_result = PointInteractorResult()
        self.ref_point  = AllplanGeo.Point3D()
        self.poly_points: list[AllplanGeo.Point3D] = []

        self.catalogue: hbt.HBTCatalogue | None = None
        self.catalogue_error = ""
        self.library: hlib.HBTLibrary | None = None
        self.attr_ids: dict[str, int] | None = None

        self._load_catalogue()
        self._open_library()
        self._update_palette()


    # =================================================================================================================
    # catalogue, library, palette
    # =================================================================================================================

    def _load_catalogue(self):
        path = self.build_ele.CatalogueFile.value.strip() or hbt.DEFAULT_CATALOGUE

        try:
            self.catalogue       = hbt.HBTCatalogue.load(path)
            self.catalogue_error = ""
        except (OSError, ValueError, KeyError, hbt.CatalogueError) as err:
            self.catalogue       = None
            self.catalogue_error = str(err)
            print("HBT catalogue error:", err)

        if self.catalogue is not None and self.build_ele.MandrelCatalogue.value <= 0:
            cat_mand, ec2_mand = self.catalogue.mandrel_defaults
            self.build_ele.MandrelCatalogue.value = cat_mand
            self.build_ele.MandrelEC2.value       = ec2_mand


    def _open_library(self):
        """ open (and read) the company library folder """

        fallback = AllplanSettings.AllplanPaths.GetUsrPath().rstrip("\\/") + "\\HBT_Library"
        folder, source = hlib.resolve_folder(self.build_ele.LibraryPath.value, fallback)

        self.library = hlib.HBTLibrary(folder).refresh()

        build_ele = self.build_ele
        build_ele.LibraryFolder.value = f"{folder} ({source})"
        build_ele.SavedList.value     = "|".join([""] + self.library.labels())

        if build_ele.SavedItem.value not in self.library.labels():
            build_ele.SavedItem.value = ""


    def _answers(self) -> list[str]:
        build_ele = self.build_ele
        return [build_ele.Answer1.value, build_ele.Answer2.value, build_ele.Answer3.value,
                build_ele.Answer4.value, build_ele.Answer5.value]


    def _length_choice(self) -> float:
        """ element length of the single placement """

        build_ele = self.build_ele

        if build_ele.ElementLength.value == CUSTOM_LENGTH:
            return float(build_ele.CustomLength.value)

        return float(build_ele.ElementLength.value)


    def _spec(self, length: float | None = None) -> hbt.HBTSpec | None:
        """ specification from the palette values, optionally with another element length """

        build_ele = self.build_ele

        if self.catalogue is None:
            return None

        std = build_ele.StandardDims.value

        try:
            return self.catalogue.spec(build_ele.Rows.value, build_ele.Casing.value, build_ele.RebarType.value,
                                       build_ele.Diameter.value, build_ele.Spacing.value,
                                       self._length_choice() if length is None else length,
                                       h     = None if std else build_ele.AnchorLength.value,
                                       lu    = None if std else build_ele.ConnectionLength.value,
                                       leg   = None if std else build_ele.LegLength.value,
                                       strip = build_ele.HBTStrip.value,
                                       mandrel_catalogue = build_ele.MandrelCatalogue.value,
                                       mandrel_ec2       = build_ele.MandrelEC2.value)
        except (KeyError, ValueError, hbt.CatalogueError) as err:
            print("HBT selection error:", err)
            return None


    def _identity(self, spec: hbt.HBTSpec) -> str:
        return hlib.identity_key(spec.designation, spec.rows, self._answers(),
                                 spec.mandrel_catalogue, spec.mandrel_ec2)


    def _update_palette(self):
        """ valid selection, dependent lists, dimensions, check and library status """

        build_ele = self.build_ele
        cat       = self.catalogue

        if cat is None:
            build_ele.InfoText.value = f"Catalogue error: {self.catalogue_error}"
            return

        rows, casing, type_text, dia, spacing = cat.first_valid(
            build_ele.Rows.value, build_ele.Casing.value, build_ele.RebarType.value,
            build_ele.Diameter.value, build_ele.Spacing.value)

        build_ele.Rows.value      = rows
        build_ele.Casing.value    = casing
        build_ele.RebarType.value = type_text
        build_ele.Diameter.value  = dia
        build_ele.Spacing.value   = spacing

        lengths = cat.element_lengths() + [CUSTOM_LENGTH]
        if build_ele.ElementLength.value not in lengths:
            build_ele.ElementLength.value = lengths[0]

        build_ele.CasingList.value    = "|".join(cat.casing_codes(rows))
        build_ele.RebarTypeList.value = "|".join(cat.rebar_type_texts(rows, casing))
        build_ele.DiameterList.value  = "|".join(cat.diameters(rows, casing))
        build_ele.SpacingList.value   = "|".join(cat.spacings(rows, casing, dia))
        build_ele.LengthList.value    = "|".join(lengths)

        spec = self._spec()

        if spec is None:
            build_ele.InfoText.value = "Invalid selection"
            return

        if build_ele.StandardDims.value:
            build_ele.AnchorLength.value     = spec.h
            build_ele.ConnectionLength.value = spec.lu
            build_ele.LegLength.value        = spec.leg

        build_ele.LegName.value     = spec.leg_name
        build_ele.PlanText.value    = spec.designation
        build_ele.CasingWidth.value = spec.casing_width
        build_ele.CasingDepth.value = spec.casing_depth
        build_ele.RebarWidth.value  = spec.rebar_width
        build_ele.HMin.value        = spec.h_min
        build_ele.LuMax.value       = spec.lu_max
        build_ele.LMin.value        = spec.minimum_length
        build_ele.BarCount.value    = spec.bar_count
        build_ele.EndSpacing.value  = spec.end_spacing

        if build_ele.PlacementMode.value == build_ele.MODE_SINGLE:
            errors = spec.errors()
            build_ele.InfoText.value = "BLOCKED: " + "; ".join(errors) if errors else "OK"
        else:
            build_ele.InfoText.value = f"Polyline: elements checked per segment (Lmin = {hbt.fmt(spec.minimum_length)})"

        if self.library is not None:
            record = self.library.find(self._identity(spec))
            build_ele.LibraryStatus.value = (f"Existing product #{record['id'][:6]} ({record.get('created', '')})"
                                             if record else "New product - saved on placement")


    def modify_element_property(self,
                                name : str,
                                value: Any) -> bool:
        """ modify the element property

        Args:
            name:  name of the modified property
            value: new value

        Returns:
            update palette state
        """

        del value

        if name == "CatalogueFile":
            self._load_catalogue()
        elif name == "LibraryPath":
            self._open_library()
        elif name == "PlacementMode":
            self.start_input()

        self._update_palette()
        self.draw_preview()

        return True


    def on_control_event(self,
                         event_id: int) -> bool:
        """ palette buttons

        Args:
            event_id: event id of the clicked button

        Returns:
            update palette state
        """

        build_ele = self.build_ele

        if event_id == build_ele.REFRESH_LIBRARY:
            self._open_library()

        elif event_id == build_ele.LOAD_SAVED and self.library is not None:
            record = self.library.by_label(build_ele.SavedItem.value)
            if record is not None:
                self._apply_record(record)

        self._update_palette()
        self.draw_preview()

        return True


    def _apply_record(self, record: dict):
        """ copy a library record into the palette """

        build_ele = self.build_ele
        cat       = self.catalogue

        if cat is None:
            return

        build_ele.Rows.value      = int(record["rows"])
        build_ele.Casing.value    = record["casing"]
        build_ele.RebarType.value = cat.rebar_types.get(record["rebar_type"], {}).get("text", "")
        build_ele.Diameter.value  = record["diameter"]
        build_ele.Spacing.value   = record["spacing_cm"]

        length = hbt.fmt(record["length"])
        if length in cat.element_lengths():
            build_ele.ElementLength.value = length
        else:
            build_ele.ElementLength.value = CUSTOM_LENGTH
            build_ele.CustomLength.value  = float(record["length"])

        build_ele.StandardDims.value     = False
        build_ele.AnchorLength.value     = float(record["h"])
        build_ele.ConnectionLength.value = float(record["lu"])
        build_ele.LegLength.value        = float(record.get("leg", 0.0))
        build_ele.HBTStrip.value         = bool(record.get("strip", False))
        build_ele.MandrelCatalogue.value = float(record["mandrel_catalogue"])
        build_ele.MandrelEC2.value       = float(record["mandrel_ec2"])

        answers = (list(record.get("answers", [])) + [""] * 5)[:5]
        build_ele.Answer1.value, build_ele.Answer2.value, build_ele.Answer3.value, \
            build_ele.Answer4.value, build_ele.Answer5.value = answers


    # =================================================================================================================
    # input
    # =================================================================================================================

    def start_input(self):
        """ start the first point input of the current mode """

        build_ele = self.build_ele

        build_ele.InputMode.value = build_ele.REF_POINT
        self.poly_points = []

        text = ("HBT: reference point (casing end on formwork face)"
                if build_ele.PlacementMode.value == build_ele.MODE_SINGLE else "HBT polyline: first point")

        self.script_object_interactor = PointInteractor(self.pnt_result, True, text, self.draw_preview,
                                                        z_coord_input = True)


    def start_next_input(self):
        """ next input after a point was clicked """

        build_ele = self.build_ele
        point     = AllplanGeo.Point3D(self.pnt_result.input_point)

        if build_ele.PlacementMode.value == build_ele.MODE_POLYLINE:
            self.poly_points.append(point)
            build_ele.InputMode.value = build_ele.DIR_POINT
            self.script_object_interactor = PointInteractor(self.pnt_result, False,
                                                            "HBT polyline: next point (ESC = create)",
                                                            self.draw_preview, z_coord_input = True,
                                                            start_point = point)
            return

        if build_ele.InputMode.value == build_ele.REF_POINT:
            self.ref_point = point
            build_ele.InputMode.value = build_ele.DIR_POINT
            self.script_object_interactor = PointInteractor(self.pnt_result, False,
                                                            "HBT: direction point (casing length direction)",
                                                            self.draw_preview, z_coord_input = True,
                                                            start_point = self.ref_point)
            return

        spec = self._spec()

        if spec is not None and not spec.errors():
            matrix = self._single_matrix(self.ref_point, point)
            self._create_fixtures([(spec, matrix)])

        self.start_input()


    def execute(self) -> CreateElementResult:
        """ elements are created in start_next_input / on_cancel_function

        Returns:
            empty result
        """

        return CreateElementResult()


    def on_cancel_function(self) -> OnCancelFunctionResult:
        """ ESC: polyline -> create the elements; single -> back to the first point; else end

        Returns:
            cancel result
        """

        build_ele = self.build_ele

        BuildingElementListService.write_to_default_favorite_file([build_ele])

        if build_ele.PlacementMode.value == build_ele.MODE_POLYLINE and self.poly_points:
            if len(self.poly_points) >= 2:
                elements, problems = self._polyline_elements(self.poly_points)
                self._create_fixtures(elements)
                build_ele.InfoText.value = "; ".join(problems) if problems else f"{len(elements)} elements created"
            self.poly_points = []
            return OnCancelFunctionResult.RESTART

        if build_ele.InputMode.value == build_ele.DIR_POINT:
            return OnCancelFunctionResult.RESTART

        return OnCancelFunctionResult.CANCEL_INPUT


    def draw_preview(self):
        """ preview at the cursor """

        build_ele = self.build_ele
        cursor    = self.pnt_result.input_point

        if build_ele.PlacementMode.value == build_ele.MODE_POLYLINE:
            if not self.poly_points:
                return
            elements, _ = self._polyline_elements(self.poly_points + [AllplanGeo.Point3D(cursor)])
        else:
            spec = self._spec()
            if spec is None:
                return
            if build_ele.InputMode.value == build_ele.DIR_POINT:
                matrix = self._single_matrix(self.ref_point, cursor)
            else:
                matrix = self._single_matrix(cursor, None)
            elements = [(spec, matrix)]

        for spec, matrix in elements:
            geo = self._geometry(spec)
            if geo is not None:
                AllplanBaseEle.DrawElementPreview(self.document, matrix, geo[0], False, None)


    # =================================================================================================================
    # placement matrices
    # =================================================================================================================

    def _single_matrix(self,
                       ref_point: AllplanGeo.Point3D,
                       dir_point: AllplanGeo.Point3D | None) -> AllplanGeo.Matrix3D:
        build_ele = self.build_ele

        ref = (ref_point.X, ref_point.Y, ref_point.Z)
        drp = None if dir_point is None else (dir_point.X, dir_point.Y, dir_point.Z)

        axes = hbt.placement_axes(ref, drp, build_ele.FacePlane.value, build_ele.FlipSide.value)

        return _matrix(ref, axes)


    def _polyline_elements(self, points: list) -> tuple[list[tuple[hbt.HBTSpec, Any]], list[str]]:
        """ split each polyline segment into elements

        Returns:
            ([(spec, matrix)], problem texts)
        """

        build_ele = self.build_ele
        result    = []
        problems  = []
        cache: dict[float, hbt.HBTSpec | None] = {}

        def spec_for(length: float) -> hbt.HBTSpec | None:
            if length not in cache:
                cache[length] = self._spec(length)
            return cache[length]

        def is_valid(length: float) -> bool:
            spec = spec_for(length)
            return spec is not None and not spec.errors()

        for index, (p_start, p_end) in enumerate(zip(points[:-1], points[1:]), start=1):
            start = (p_start.X, p_start.Y, p_start.Z)
            end   = (p_end.X, p_end.Y, p_end.Z)
            axes  = hbt.segment_axes(start, end, build_ele.FacePlane.value, build_ele.FlipSide.value,
                                     build_ele.VerticalFaceAngle.value)

            if axes is None:
                problems.append(f"segment {index}: no valid direction")
                continue

            lengths = hbt.split_length(math.dist(start, end), is_valid)

            if lengths is None:
                problems.append(f"segment {index}: {hbt.fmt(math.dist(start, end))} mm cannot be split "
                                f"within the catalogue limits")
                continue

            offset = 0.0

            for length in lengths:
                origin = tuple(start[i] + axes[0][i] * offset for i in range(3))
                result.append((spec_for(length), _matrix(origin, axes)))
                offset += length

        return result, problems


    # =================================================================================================================
    # geometry and fixture creation
    # =================================================================================================================

    def _geometry(self, spec: hbt.HBTSpec):
        """ local geometry of one element

        Returns:
            (all 3D elements, outline elements, layout) or None
        """

        if spec is None or spec.bar_count < 1:
            return None

        build_ele = self.build_ele
        layout    = hbt.compute_layout(spec, build_ele.BarState.value)

        box_prop = AllplanBaseEle.CommonProperties(build_ele.CommonProp.value)
        bar_prop = AllplanBaseEle.CommonProperties(build_ele.CommonProp.value)
        bar_prop.Color = build_ele.BarColor.value

        elements = [AllplanBasisEle.ModelElement3D(box_prop, _cuboid(pmin, pmax)) for pmin, pmax in layout.box_plates]

        for bar in layout.bars:
            elements.extend(AllplanBasisEle.ModelElement3D(bar_prop, brep) for brep in _bar_breps(bar, spec.diameter))

        outline = [AllplanBasisEle.ModelElement3D(box_prop, _cuboid(*layout.box_outline))]

        return elements, outline, layout


    def _attribute_ids(self) -> dict[str, int]:
        """ Allplan attribute IDs for Plan_text and Answer 1..5 (first name found in the project) """

        if self.attr_ids is not None:
            return self.attr_ids

        self.attr_ids = {}

        if self.catalogue is None:
            return self.attr_ids

        plan_names, answer_names = self.catalogue.attribute_names()

        def find(names: list[str]) -> int:
            for name in names:
                try:
                    attr_id = AllplanBaseEle.AttributeService.GetAttributeID(self.document, name)
                except (RuntimeError, ValueError, TypeError):
                    attr_id = -1
                if attr_id and attr_id > 0:
                    return attr_id
            print("HBT: attribute not found:", names)
            return -1

        self.attr_ids["plan_text"] = find(plan_names)

        for i, names in enumerate(answer_names, start=1):
            self.attr_ids[f"answer{i}"] = find(names)

        return self.attr_ids


    def _attributes(self, spec: hbt.HBTSpec) -> AllplanBaseEle.Attributes | None:
        ids    = self._attribute_ids()
        values = [("plan_text", spec.designation)] + \
                 [(f"answer{i}", text) for i, text in enumerate(self._answers(), start=1)]

        attr_list = [AllplanBaseEle.AttributeString(ids[key], text)
                     for key, text in values if ids.get(key, -1) > 0 and text]

        if not attr_list:
            return None

        return AllplanBaseEle.Attributes([AllplanBaseEle.AttributeSet(attr_list)])


    def _library_record(self, spec: hbt.HBTSpec) -> dict:
        build_ele = self.build_ele

        return {"id"               : self._identity(spec),
                "designation"      : spec.designation,
                "plan_text"        : spec.designation,
                "rows"             : spec.rows,
                "casing"           : spec.casing,
                "rebar_type"       : spec.rebar_type,
                "diameter"         : build_ele.Diameter.value,
                "spacing_cm"       : build_ele.Spacing.value,
                "length"           : spec.length,
                "h"                : spec.h,
                "lu"               : spec.lu,
                "leg_name"         : spec.leg_name,
                "leg"              : spec.leg,
                "strip"            : spec.strip,
                "mandrel_catalogue": spec.mandrel_catalogue,
                "mandrel_ec2"      : spec.mandrel_ec2,
                "answers"          : self._answers(),
                "catalogue"        : (self.catalogue.data.get("_info", {}).get("source", "")
                                      if self.catalogue else "")}


    def _create_fixtures(self, elements: list):
        """ create the fixtures and store new products in the library """

        fixtures = []
        saved    = 0
        reused   = 0

        for spec, matrix in elements:
            if spec is None or spec.errors():
                continue

            record = self._library_record(spec)

            if self.library is not None:
                try:
                    record, is_new = self.library.save(record)
                    saved  += int(is_new)
                    reused += int(not is_new)
                except OSError as err:
                    print("HBT library save failed:", err)
                    self.build_ele.LibraryStatus.value = f"Library save failed: {err}"

            fixture = self._fixture(spec, matrix, record["id"])
            if fixture is not None:
                fixtures.append(fixture)

        if fixtures:
            AllplanBaseEle.CreateElements(self.document, AllplanGeo.Matrix3D(), fixtures, [], None)

        if self.library is not None:
            self.build_ele.SavedList.value = "|".join([""] + self.library.labels())
            self.build_ele.LibraryStatus.value = f"{len(fixtures)} placed, {saved} new in library, {reused} reused"


    def _fixture(self,
                 spec      : hbt.HBTSpec,
                 matrix    : AllplanGeo.Matrix3D,
                 identity  : str) -> AllplanPrecast.FixturePlacementElement | None:
        """ create one precast point fixture """

        geo = self._geometry(spec)

        if geo is None:
            return None

        elements, outline, layout = geo
        build_ele = self.build_ele

        com_prop = AllplanBaseEle.CommonProperties(build_ele.CommonProp.value)

        slides = []

        slide_prop                 = AllplanPrecast.FixtureSlideProperties()
        slide_prop.ViewType        = AllplanPrecast.FixtureSlideViewType.e3D_VIEW
        slide_prop.VisibilityGeo3D = True
        slide_prop.VisibilityGeo2D = False
        slides.append(AllplanPrecast.FixtureSlideElement(slide_prop, elements))

        outline_prop          = AllplanPrecast.FixtureSlideProperties()
        outline_prop.ViewType = AllplanPrecast.FixtureSlideViewType.e3D_VIEW_OUTLINE_VOLUME
        slides.append(AllplanPrecast.FixtureSlideElement(outline_prop, outline))

        measure_prop          = AllplanPrecast.FixtureSlideProperties()
        measure_prop.ViewType = AllplanPrecast.FixtureSlideViewType.eMEASURE_POINTS
        slides.append(AllplanPrecast.FixtureSlideElement(
            measure_prop, [AllplanBasisEle.ModelElement3D(com_prop, AllplanGeo.Point3D(*layout.dim_point))]))

        fixture_prop                = AllplanPrecast.FixtureProperties()
        fixture_prop.Type           = AllplanPrecast.MacroType.ePoint_Fixture
        fixture_prop.SubType        = AllplanPrecast.MacroSubType.eJointReinforcement
        fixture_prop.Name           = spec.designation
        fixture_prop.InsertionPoint = AllplanGeo.Point3D(*layout.ref_point)

        fixture = AllplanPrecast.FixtureElement(fixture_prop, slides)

        # same product + representation -> same hash -> one fixture definition in every project
        hash_key = f"{identity}|{build_ele.BarState.value}|{build_ele.BarColor.value}"
        fixture.SetHash(hashlib.sha224(hash_key.encode("utf-8")).hexdigest())

        placement_prop              = AllplanPrecast.FixturePlacementProperties()
        placement_prop.Name         = spec.designation
        placement_prop.OutlineType  = AllplanPrecast.OutlineType.eBUILTIN_OUTLINE_TYPE_MINUS \
                                      if build_ele.CutBoxVolume.value else \
                                      AllplanPrecast.OutlineType.eBUILTIN_OUTLINE_TYPE_NO_AFFECT
        placement_prop.OutlineShape = AllplanPrecast.OutlineShape.eBUILTIN_OUTLINE_SHAPE_RECTANGLE
        placement_prop.Matrix       = matrix

        placement = AllplanPrecast.FixturePlacementElement(com_prop, placement_prop, fixture)

        attributes = self._attributes(spec)
        if attributes is not None:
            placement.SetAttributes(attributes)

        return placement


# =====================================================================================================================
# geometry helpers
# =====================================================================================================================

def _matrix(origin, axes) -> AllplanGeo.Matrix3D:
    """ local -> world matrix """

    x_dir, _, z_dir = axes

    placement = AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*origin),
                                           AllplanGeo.Vector3D(*x_dir), AllplanGeo.Vector3D(*z_dir))

    return placement.GetTransformationMatrix()


def _cuboid(pmin: hbt.Point, pmax: hbt.Point) -> AllplanGeo.BRep3D:
    """ axis parallel cuboid from min / max corner """

    return AllplanGeo.BRep3D.CreateCuboid(AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*pmin)),
                                          pmax[0] - pmin[0], pmax[1] - pmin[1], pmax[2] - pmin[2])


def _bar_breps(bar: hbt.Bar, diameter: float) -> list[AllplanGeo.BRep3D]:
    """ bar solid: circle swept along the filleted centre line (lines + mandrel arcs)

    Fallback if the sweep fails: cylinders per line, arcs approximated by short cylinders, spheres at joints.
    """

    segments, _ = hbt.fillet_bar(bar, diameter)

    if not segments:
        return []

    radius = diameter / 2

    path = AllplanGeo.Path3D()

    for seg in segments:
        if isinstance(seg, hbt.LineSeg):
            path += AllplanGeo.Line3D(AllplanGeo.Point3D(*seg.start), AllplanGeo.Point3D(*seg.end))
        else:
            path += AllplanGeo.Arc3D(AllplanGeo.Point3D(*seg.center), AllplanGeo.Vector3D(*seg.x_dir),
                                     AllplanGeo.Vector3D(*seg.normal), seg.radius, seg.radius, 0.0, seg.angle)

    first     = segments[0]
    start     = first.start
    start_dir = _unit(_sub(first.end, first.start)) if isinstance(first, hbt.LineSeg) else \
                _unit(hbt._cross(first.normal, first.x_dir))

    profile = AllplanGeo.Arc3D(AllplanGeo.Point3D(*start), AllplanGeo.Vector3D(*_any_perpendicular(start_dir)),
                               AllplanGeo.Vector3D(*start_dir), radius, radius, 0.0, 2 * math.pi)

    try:
        err, brep = AllplanGeo.CreateSweptBRep3D([profile], path, True, True)
        if err == AllplanGeo.eOK:
            return [brep]
        print("HBT sweep failed:", err)
    except (RuntimeError, TypeError, ValueError) as exc:
        print("HBT sweep failed:", exc)

    return _bar_breps_fallback(segments, radius)


def _bar_breps_fallback(segments, radius: float) -> list[AllplanGeo.BRep3D]:
    pieces: list[tuple[hbt.Point, hbt.Point]] = []

    for seg in segments:
        if isinstance(seg, hbt.LineSeg):
            pieces.append((seg.start, seg.end))
        else:
            pts = [hbt.arc_point(seg, seg.angle * k / ARC_FALLBACK_SEGMENTS) for k in range(ARC_FALLBACK_SEGMENTS + 1)]
            pieces.extend(zip(pts[:-1], pts[1:]))

    breps = []

    for start, end in pieces:
        vec    = _sub(end, start)
        length = math.sqrt(sum(c * c for c in vec))
        if length < 1e-6:
            continue
        z_dir = tuple(c / length for c in vec)
        placement = AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*start),
                                               AllplanGeo.Vector3D(*_any_perpendicular(z_dir)),
                                               AllplanGeo.Vector3D(*z_dir))
        breps.append(AllplanGeo.BRep3D.CreateCylinder(placement, radius, length))

    for start, _ in pieces[1:]:
        breps.append(AllplanGeo.BRep3D.CreateSphere(AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*start)), radius))

    return breps


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _unit(vec):
    length = math.sqrt(sum(c * c for c in vec))
    return tuple(c / length for c in vec)


def _any_perpendicular(vec: tuple) -> tuple:
    """ a unit vector perpendicular to the unit vector vec """

    helper = (0.0, 0.0, 1.0) if abs(vec[2]) < 0.9 else (1.0, 0.0, 0.0)

    perp = (vec[1] * helper[2] - vec[2] * helper[1],
            vec[2] * helper[0] - vec[0] * helper[2],
            vec[0] * helper[1] - vec[1] * helper[0])

    return _unit(perp)
