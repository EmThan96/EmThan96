""" HBT Fixture - places HBT rebend connections as Allplan precast point fixtures.

Placement modes
    1. Single element: click the reference point, then the direction point.
    2. Polyline:       click any number of points; ESC creates the elements. Every segment is filled with
                       1250 / 800 standard elements and, if needed, custom elements (catalogue limits checked).
    3. Auto row:       one click on a concrete face; the free run through the point (stops at face ends,
                       openings and recesses, keeps the edge distance) is filled like a polyline segment.

Check placed HBT (palette button)
    Every HBT fixture of the document is checked: on a concrete face, embedded leg in the concrete, free leg
    not in concrete, casing on the face. Result in the palette and the trace, optionally written to an attribute.

Version 2.4: auto row, check of placed fixtures, coplanar faces, faces with openings, fit and casing warnings.

Orientation
    Automatic face detection (default): the face of a solid under the clicked points is found; the anchor h goes
    into the solid, lü points out of it, the casing length follows the clicked direction. Flip reverses h / lü.
    No solid face at the points -> manual orientation with "Formwork face" and "Flip".

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

__author__ = "Em Than - gbc engineers"

import hashlib
import math
import re

from typing import TYPE_CHECKING, Any

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_BasisElements as AllplanBasisEle
import NemAll_Python_Geometry as AllplanGeo
import NemAll_Python_IFW_ElementAdapter as AllplanEleAdapter
import NemAll_Python_Precast as AllplanPrecast

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from CreateElementResult import CreateElementResult
from BuildingElementListService import BuildingElementListService

from ScriptObjectInteractors.OnCancelFunctionResult import OnCancelFunctionResult
from ScriptObjectInteractors.PointInteractor import PointInteractor, PointInteractorResult

from gbc_engineers.hbt_fixture import hbt_catalogue as hbt
from gbc_engineers.hbt_fixture import hbt_face as hface
from gbc_engineers.hbt_fixture import hbt_library as hlib

if TYPE_CHECKING:
    from __BuildingElementStubFiles.HBTFixtureBuildingElement import HBTFixtureBuildingElement as BuildingElement  # type: ignore
else:
    from BuildingElement import BuildingElement

print('Load HBTFixture.py')

CUSTOM_LENGTH = "Custom"
ARC_FALLBACK_SEGMENTS = 8

# raise when the fixture geometry changes, so Allplan does not reuse an old fixture definition with the same hash
# 2 = hook y along the casing length, b2 legs side by side (catalogue HBT 22-E page 12)
GEOMETRY_VERSION = 2


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
        self.face_solids: list[hface.Solid] | None = None        # solids of the document, read per input
        self.face_warnings: list[str] = []                       # fit check of the last placement / preview

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

        # repair an invalid palette selection instead of failing (e.g. a value the palette set on its own)
        rows, casing, type_text, dia, spacing = self.catalogue.first_valid(
            build_ele.Rows.value, build_ele.Casing.value, build_ele.RebarType.value,
            build_ele.Diameter.value, build_ele.Spacing.value)

        try:
            return self.catalogue.spec(rows, casing, type_text, dia, spacing,
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
            mode_name = "Auto row" if build_ele.PlacementMode.value == build_ele.MODE_AUTOROW else "Polyline"
            build_ele.InfoText.value = f"{mode_name}: elements checked per segment (Lmin = {hbt.fmt(spec.minimum_length)})"

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

        elif event_id == build_ele.CHECK_PLACED:
            self._check_placed()

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

    def start_input(self, keep_solids: bool = False):
        """ start the first point input of the current mode

        Args:
            keep_solids: keep the solids read for the face detection (next click of the same input)
        """

        build_ele = self.build_ele

        build_ele.InputMode.value = build_ele.REF_POINT
        self.poly_points = []
        if not keep_solids:
            self.face_solids = None         # re-read the solids, the model may have changed

        mode = build_ele.PlacementMode.value
        text = ("HBT: reference point (casing end on formwork face)" if mode == build_ele.MODE_SINGLE else
                "HBT auto row: click a point on the concrete face" if mode == build_ele.MODE_AUTOROW else
                "HBT polyline: first point")

        self.script_object_interactor = PointInteractor(self.pnt_result, True, text, self.draw_preview,
                                                        z_coord_input = True)


    def start_next_input(self):
        """ next input after a point was clicked """

        build_ele = self.build_ele
        point     = AllplanGeo.Point3D(self.pnt_result.input_point)

        if build_ele.PlacementMode.value == build_ele.MODE_AUTOROW:
            elements, problems = self._auto_row_elements(point)
            self._create_fixtures(elements)
            build_ele.InfoText.value = "; ".join(problems) if problems else f"Auto row: {len(elements)} elements created"
            self.start_input(keep_solids = True)
            return

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

        if build_ele.PlacementMode.value == build_ele.MODE_AUTOROW:
            elements, _ = self._auto_row_elements(AllplanGeo.Point3D(cursor))
        elif build_ele.PlacementMode.value == build_ele.MODE_POLYLINE:
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

    def _solids(self) -> list[hface.Solid]:
        """ solids of the document for the face detection (read once per input) """

        if self.face_solids is None:
            self.face_solids = _collect_solids(self.document)

        return self.face_solids


    def _face_axes(self, start: tuple, end: tuple | None, points: list[tuple]):
        """ axes on the solid face that contains the points (automatic face detection)

        Returns:
            (axes, face) or (None, None) if the detection is off or no face contains the points
        """

        build_ele = self.build_ele

        if not build_ele.AutoFace.value:
            return None, None

        face = hface.find_face(self._solids(), points,
                               prefer_horizontal = build_ele.FacePlane.value == hbt.FACE_HORIZONTAL)

        if face is None:
            return None, None

        axes = hface.face_axes(face, start, end, build_ele.FlipSide.value,
                               box_vertical = build_ele.FacePlane.value == hbt.FACE_VERTICAL_BOX_VERT)

        if axes is None:
            return None, None

        # fit check at the given points: h in the concrete, lü free (warning only)
        spec = self._spec()
        if spec is not None:
            for text in hface.fit_warnings(face, self._solids(), points, axes[2], spec.h, spec.lu,
                                           flip = build_ele.FlipSide.value):
                if text not in self.face_warnings:
                    self.face_warnings.append(text)

        return axes, face


    def _set_face_info(self, face: hface.Face | None, problems: list[str] | None = None):
        build_ele = self.build_ele
        warnings  = getattr(self, "face_warnings", [])

        if not build_ele.AutoFace.value:
            build_ele.FaceInfo.value = "Off - manual orientation (Formwork face, Flip)"
        elif problems or (face is not None and warnings):
            build_ele.FaceInfo.value = "WARNING: " + "; ".join((problems or []) + warnings)
        elif face is None:
            build_ele.FaceInfo.value = "No solid face at the point - manual orientation"
        else:
            nrm = face.normal
            build_ele.FaceInfo.value = (f"{face.solid.source if face.solid else 'Solid'}: outward normal "
                                        f"({nrm[0]:.2f}, {nrm[1]:.2f}, {nrm[2]:.2f}), h into the solid")


    def _single_matrix(self,
                       ref_point: AllplanGeo.Point3D,
                       dir_point: AllplanGeo.Point3D | None) -> AllplanGeo.Matrix3D:
        build_ele = self.build_ele

        ref = (ref_point.X, ref_point.Y, ref_point.Z)
        drp = None if dir_point is None else (dir_point.X, dir_point.Y, dir_point.Z)

        # automatic: face under both points, else under the reference point (direction point may be off the face)
        self.face_warnings = []
        axes, face = self._face_axes(ref, drp, [ref, drp] if drp is not None else [ref])
        if axes is None and drp is not None:
            self.face_warnings = []
            axes, face = self._face_axes(ref, drp, [ref])

        if face is not None:
            self._check_casing_on_face(face, ref, axes, self._spec())

        self._set_face_info(face)

        if axes is None:
            axes = hbt.placement_axes(ref, drp, build_ele.FacePlane.value, build_ele.FlipSide.value)

        return _matrix(ref, axes)


    def _check_casing_on_face(self, face: hface.Face, origin: tuple, axes, spec: hbt.HBTSpec | None):
        """ warning if the casing footprint does not lie completely on the face (edge, opening, end of the face) """

        if spec is None or axes is None:
            return

        if not hface.casing_on_face(face, origin, axes, spec.length, spec.casing_width):
            text = "casing runs off the face (edge / opening / end of face)"
            if text not in self.face_warnings:
                self.face_warnings.append(text)


    def _auto_row_elements(self, point: AllplanGeo.Point3D) -> tuple[list[tuple[hbt.HBTSpec, Any]], list[str]]:
        """ automatic row: the free run on the clicked face, filled with 1250 / 800 / custom elements

        Vertical face: horizontal row at the height of the click ("box vertical": vertical row through the click).
        Other faces:   row along the longest edge of the face.
        The run stops at the face boundary, openings and recesses; the ends keep the edge distance.
        """

        build_ele = self.build_ele
        pnt       = (point.X, point.Y, point.Z)

        self.face_warnings = []

        if not build_ele.AutoFace.value:
            return [], ["Auto row needs 'Automatic face detection'"]

        face = hface.find_face(self._solids(), [pnt], prefer_horizontal = build_ele.FacePlane.value == hbt.FACE_HORIZONTAL)

        if face is None:
            self._set_face_info(None)
            return [], ["Auto row: no concrete face at the point"]

        spec = self._spec()
        if spec is None:
            return [], ["Invalid selection"]

        direction = hface.row_direction(face, box_vertical = build_ele.FacePlane.value == hbt.FACE_VERTICAL_BOX_VERT)
        run       = hface.face_run(face, pnt, direction, spec.casing_width, build_ele.EdgeDistance.value)

        if run is None:
            self._set_face_info(face)
            return [], ["Auto row: no free run at the point (edge / opening / recess)"]

        start, end = run

        return self._polyline_elements([AllplanGeo.Point3D(*start), AllplanGeo.Point3D(*end)])


    # =================================================================================================================
    # check of the placed HBT fixtures
    # =================================================================================================================

    def _check_placed(self):
        """ check every HBT fixture of the document: on a concrete face, embedded leg in the concrete,
        free leg not in concrete, casing on the face. Result in the palette, details in the trace;
        optionally written to an attribute of each fixture.
        """

        build_ele = self.build_ele

        self.face_solids = None                     # the model may have changed
        solids  = self._solids()
        plan_id = self._attribute_ids().get("plan_text", -1)

        mark_id = -1
        if build_ele.CheckWriteAttribute.value:
            try:
                mark_id = AllplanBaseEle.AttributeService.GetAttributeID(self.document, build_ele.CheckAttributeName.value)
            except (RuntimeError, ValueError, TypeError):
                mark_id = -1

        try:
            adapters = AllplanBaseEle.ElementsSelectService.SelectAllElements(self.document)
        except (RuntimeError, TypeError, ValueError) as err:
            build_ele.CheckInfo.value = f"Cannot read the elements: {err}"
            return

        checked, flipped, problems = 0, 0, []

        for i in range(len(adapters)):
            adapter = adapters[i]
            try:
                if "PointFixture" not in str(adapter.GetElementAdapterType().GetTypeName()):
                    continue
                attrs = dict(AllplanBaseEle.ElementsAttributeService.GetAttributes(adapter))
            except (RuntimeError, TypeError, ValueError):
                continue

            parsed = _parse_designation(str(attrs.get(plan_id, "")) if plan_id > 0 else "")
            if parsed is None:
                continue

            checked += 1
            messages, is_flipped, where = self._check_fixture(adapter, solids, *parsed)
            flipped += int(is_flipped)

            if messages:
                problems.append(f"{attrs.get(plan_id)} at ({where}): " + "; ".join(messages))

            if mark_id > 0:
                text = "HBT check: OK" if not messages else "HBT check: " + "; ".join(messages)
                try:
                    lst = AllplanEleAdapter.BaseElementAdapterList()
                    lst.append(adapter)
                    AllplanBaseEle.ElementsAttributeService.ChangeAttribute(mark_id, text[:250], lst)
                except (RuntimeError, TypeError, ValueError) as err:
                    print("HBT check: cannot write the attribute:", err)

        build_ele.CheckInfo.value = (f"{checked} HBT checked: {checked - len(problems)} OK, {len(problems)} with problems"
                                     + (f", {flipped} with Flip" if flipped else ""))
        build_ele.CheckList.value = " | ".join(problems[:3]) + (" | ..." if len(problems) > 3 else "")

        print(f"HBT check: {build_ele.CheckInfo.value}")
        for text in problems:
            print("   ", text)


    def _check_fixture(self, adapter, solids: list[hface.Solid], diameter: float, h: float,
                       lu: float) -> tuple[list[str], bool, str]:
        """ check one placed HBT fixture

        Returns:
            (problem texts, flipped, position text)
        """

        try:
            geo = adapter.GetModelGeometry()
        except (RuntimeError, TypeError, ValueError):
            return ["geometry not readable"], False, "?"

        items = geo if isinstance(geo, list) else [geo]
        mpt   = next((g for g in items if isinstance(g, AllplanGeo.Point3D)), None)
        breps = [g for g in items if isinstance(g, AllplanGeo.BRep3D)]

        if mpt is None or len(breps) < 6:
            return ["geometry not readable"], False, "?"

        meas  = (mpt.X, mpt.Y, mpt.Z)
        where = f"{meas[0]:.0f}, {meas[1]:.0f}, {meas[2]:.0f}"
        cands = hface.faces_at(solids, meas, tol = 2.0)

        if not cands:
            return ["not on a concrete face"], False, where

        radius = diameter / 2
        best   = None

        for face in cands:
            nrm   = face.normal
            u_dir = hface._norm(hface._cross((0.0, 0.0, 1.0), nrm)) if abs(nrm[2]) < 0.9 else \
                    hface._norm(hface._sub((1.0, 0.0, 0.0), hface._mul(nrm, nrm[0])))
            v_dir = hface._cross(nrm, u_dir)

            # casing length axis = principal axis of the bar positions in the face plane (the casing may be rotated
            # in the face, e.g. on the top of an inclined wall)
            u_dir, v_dir = _casing_axes(breps[5:-1], meas, u_dir, v_dir, nrm)

            inv = _matrix(meas, (u_dir, v_dir, nrm))
            inv.Reverse()

            casing = _local_minmax(breps[:5], inv)
            bars   = _local_minmax(breps[5:], inv)

            if casing is None or bars is None:
                continue

            # orientation from the anchor leg h (works for straightened and delivered bars)
            if abs(-bars[0][2] - (h + radius)) < 5:
                flip = False
            elif abs(bars[1][2] - (h + radius)) < 5:
                flip = True
            else:
                result = (["bars do not match the face (orientation)"], False)
                best   = best or result
                continue

            # casing footprint on the face, centre line along the long side
            (cu0, cv0, _), (cu1, cv1, _) = casing
            long_u = (cu1 - cu0) >= (cv1 - cv0)

            def world(a: float, b: float) -> tuple:
                return tuple(meas[k] + u_dir[k] * a + v_dir[k] * b for k in range(3))

            if long_u:
                centre = [world(t, (cv0 + cv1) / 2) for t in (cu0, (cu0 + cu1) / 2, cu1)]
                corners = [world(t, s) for t in (cu0, (cu0 + cu1) / 2, cu1) for s in (cv0, cv1)]
            else:
                centre = [world((cu0 + cu1) / 2, t) for t in (cv0, (cv0 + cv1) / 2, cv1)]
                corners = [world(s, t) for t in (cv0, (cv0 + cv1) / 2, cv1) for s in (cu0, cu1)]

            z_dir    = nrm if flip else hface._mul(nrm, -1.0)
            messages = hface.fit_warnings(face, solids, centre, z_dir, h, lu, flip)

            if not all(face.on_surface(c, 2.0) for c in corners):
                messages.append("casing runs off the face (edge / opening / end of face)")

            if best is None or len(messages) < len(best[0]) or best[0] == ["bars do not match the face (orientation)"]:
                best = (messages, flip)

        if best is None:
            return ["geometry not readable"], False, where

        return best[0], best[1], where


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

        last_face  = None
        face_notes = []
        self.face_warnings = []

        for index, (p_start, p_end) in enumerate(zip(points[:-1], points[1:]), start=1):
            start = (p_start.X, p_start.Y, p_start.Z)
            end   = (p_end.X, p_end.Y, p_end.Z)
            mid   = tuple((start[k] + end[k]) / 2 for k in range(3))

            # automatic: the whole segment must lie on one solid face
            axes, face = self._face_axes(start, end, [start, mid, end])

            if face is not None:
                last_face = face
            elif build_ele.AutoFace.value:
                face_notes.append(f"segment {index}: no solid face - manual orientation")

            if axes is None:
                axes = hbt.segment_axes(start, end, build_ele.FacePlane.value, build_ele.FlipSide.value,
                                        build_ele.VerticalFaceAngle.value)

            if axes is None:
                problems.append(f"segment {index}: no valid direction")
                continue

            lengths = hbt.split_length(math.dist(start, end), is_valid)

            if lengths is None:
                problems.append(f"segment {index}: {math.dist(start, end):.0f} mm cannot be split "
                                f"within the catalogue limits")
                continue

            offset = 0.0

            for length in lengths:
                origin = tuple(start[i] + axes[0][i] * offset for i in range(3))
                result.append((spec_for(length), _matrix(origin, axes)))
                if face is not None:
                    self._check_casing_on_face(face, origin, axes, spec_for(length))
                offset += length

        self._set_face_info(last_face, face_notes)

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

        # measure points must be Symbol3DElement - a ModelElement3D(Point3D) makes Allplan reject the fixture
        measure_prop          = AllplanPrecast.FixtureSlideProperties()
        measure_prop.ViewType = AllplanPrecast.FixtureSlideViewType.eMEASURE_POINTS

        symbol_prop                  = AllplanBasisEle.Symbol3DProperties()
        symbol_prop.SymbolID         = 1
        symbol_prop.Height           = 1
        symbol_prop.Width            = 1
        symbol_prop.IsScaleDependent = False

        help_prop = AllplanBaseEle.CommonProperties(com_prop)
        help_prop.HelpConstruction = True

        slides.append(AllplanPrecast.FixtureSlideElement(
            measure_prop, [AllplanBasisEle.Symbol3DElement(help_prop, symbol_prop,
                                                           AllplanGeo.Point3D(*layout.dim_point))]))

        fixture_prop                = AllplanPrecast.FixtureProperties()
        fixture_prop.Type           = AllplanPrecast.MacroType.ePoint_Fixture
        fixture_prop.SubType        = AllplanPrecast.MacroSubType.eJointReinforcement
        fixture_prop.Name           = spec.designation
        fixture_prop.InsertionPoint = AllplanGeo.Point3D(*layout.ref_point)

        fixture = AllplanPrecast.FixtureElement(fixture_prop, slides)

        # same product + representation + geometry version -> same hash -> one fixture definition in every project
        hash_key = f"{identity}|{build_ele.BarState.value}|{build_ele.BarColor.value}|g{GEOMETRY_VERSION}"
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
# helpers for the check of placed fixtures
# =====================================================================================================================

_DESIGNATION_RE = re.compile(r"^HBT(?:-S)?\s+\d+\s+-\s+(\d+(?:\.\d+)?)/.*?h\s*=\s*(\d+(?:\.\d+)?),\s*lü\s*=\s*(\d+(?:\.\d+)?)")


def _parse_designation(text: str) -> tuple[float, float, float] | None:
    """ (diameter, h, lü) from an HBT order designation, e.g. 'HBT 85 - 10/15 - 1 - 1250, h = 170, lü = 390, y = 95' """

    match = _DESIGNATION_RE.match(text.strip())
    return None if match is None else (float(match.group(1)), float(match.group(2)), float(match.group(3)))


def _casing_axes(bars: list, origin: tuple, u_dir: tuple, v_dir: tuple, normal: tuple) -> tuple[tuple, tuple]:
    """ in-plane axes (length, width) of a placed casing from the bar positions (2D principal axis) """

    pts = []
    for bar in bars:
        try:
            res = AllplanGeo.CalcMinMax(bar)
        except (RuntimeError, TypeError, ValueError):
            continue
        box = next((r for r in (res if isinstance(res, tuple) else (res,)) if hasattr(r, "Min")), None)
        if box is None:
            continue
        ctr = ((box.Min.X + box.Max.X) / 2 - origin[0], (box.Min.Y + box.Max.Y) / 2 - origin[1],
               (box.Min.Z + box.Max.Z) / 2 - origin[2])
        pts.append((hface._dot(ctr, u_dir), hface._dot(ctr, v_dir)))

    if len(pts) < 2:
        return u_dir, v_dir

    mu = sum(p[0] for p in pts) / len(pts)
    mv = sum(p[1] for p in pts) / len(pts)
    suu = sum((p[0] - mu) ** 2 for p in pts)
    svv = sum((p[1] - mv) ** 2 for p in pts)
    suv = sum((p[0] - mu) * (p[1] - mv) for p in pts)

    angle = 0.5 * math.atan2(2 * suv, suu - svv)
    x_dir = hface._norm(hface._add(hface._mul(u_dir, math.cos(angle)), hface._mul(v_dir, math.sin(angle))))

    return x_dir, hface._cross(normal, x_dir)


def _local_minmax(breps: list, inverse: AllplanGeo.Matrix3D) -> tuple[tuple, tuple] | None:
    """ min / max of BReps in a local frame (inverse = world -> local) """

    lo, hi = [1e18] * 3, [-1e18] * 3

    for brep in breps:
        try:
            res = AllplanGeo.CalcMinMax(AllplanGeo.Transform(brep, inverse))
        except (RuntimeError, TypeError, ValueError):
            continue
        box = next((r for r in (res if isinstance(res, tuple) else (res,)) if hasattr(r, "Min")), None)
        if box is None:
            continue
        for k, (a, b) in enumerate(((box.Min.X, box.Max.X), (box.Min.Y, box.Max.Y), (box.Min.Z, box.Max.Z))):
            lo[k] = min(lo[k], a)
            hi[k] = max(hi[k], b)

    return None if lo[0] > hi[0] else (tuple(lo), tuple(hi))


# =====================================================================================================================
# solids for the automatic face detection
# =====================================================================================================================

def _collect_solids(document) -> list[hface.Solid]:
    """ planar solids of all elements with 3D volume geometry (fixtures excluded, so HBT never snaps onto HBT) """

    solids: list[hface.Solid] = []

    try:
        adapters = AllplanBaseEle.ElementsSelectService.SelectAllElements(document)
    except (RuntimeError, TypeError, ValueError) as err:
        print("HBT face detection: cannot read the elements:", err)
        return solids

    for i in range(len(adapters)):
        adapter = adapters[i]
        try:
            if "Fixture" in str(adapter.GetElementAdapterType().GetTypeName()):
                continue
            geo = adapter.GetModelGeometry()
        except (RuntimeError, TypeError, ValueError):
            continue

        for item in (geo if isinstance(geo, list) else [geo]):
            poly = _as_polyhedron(item)
            if poly is None:
                continue
            try:
                solid = _solid_from_polyhedron(poly, str(adapter.GetDisplayName()))
            except (RuntimeError, TypeError, ValueError, IndexError):
                solid = None
            if solid is not None:
                solids.append(solid)

    return solids


def _as_polyhedron(item) -> AllplanGeo.Polyhedron3D | None:
    if isinstance(item, AllplanGeo.Polyhedron3D):
        return item

    if isinstance(item, AllplanGeo.BRep3D):
        try:
            settings = AllplanGeo.ApproximationSettings(AllplanGeo.eApproximationSettingsType.ASET_BREP_TESSELATION, 1)
            err, poly = AllplanGeo.CreatePolyhedron(item, settings)
            return poly if err == AllplanGeo.eOK else None
        except (RuntimeError, TypeError, ValueError):
            return None

    return None


def _solid_from_polyhedron(poly: AllplanGeo.Polyhedron3D, source: str) -> hface.Solid | None:
    def value(res):
        return res[-1] if isinstance(res, tuple) else res

    vertices = []
    for i in range(poly.GetVerticesCount()):
        pnt = value(poly.GetVertex(i))
        vertices.append((pnt.X, pnt.Y, pnt.Z))

    # per face its oriented edges; a face with openings has several loops (chained in hbt_face)
    faces_edges = []
    for fi in range(poly.GetFacesCount()):
        edges = []
        for oriented in poly.GetFace(fi).GetEdges():
            edge = value(poly.GetEdge(oriented.EdgeHandle))
            edges.append((edge.StartIndex, edge.EndIndex) if oriented.Positive else (edge.EndIndex, edge.StartIndex))
        faces_edges.append(edges)

    return hface.make_solid(vertices, faces_edges, source)


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
