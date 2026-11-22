""" HBT Fixture - places HBT rebend connection boxes as Allplan precast point fixtures.

Workflow
    1. Select type, bar diameter, spacing and box length in the property palette.
    2. Click the reference point (box end on the formwork face). Allplan point snap is active
       (end points, mid points, edges and the points of existing fixtures).
    3. Click a second point for the box direction.
    4. The fixture is created; the input restarts for the next box. ESC ends the input.

Created object
    AllplanPrecast.FixturePlacementElement (point fixture) with
      * slide e3D_VIEW               - steel box and bars
      * slide e3D_VIEW_OUTLINE_VOLUME - box volume (optional cut in the precast element)
      * slide eMEASURE_POINTS        - dimensioning point (centre of the box on the face)
    The fixture insertion point is the reference point (box end on the face).
"""

from __future__ import annotations

import hashlib
import math

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from __BuildingElementStubFiles.HBTFixtureBuildingElement import HBTFixtureBuildingElement as BuildingElement  # type: ignore
else:
    from BuildingElement import BuildingElement

print('Load HBTFixture.py')


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

        self.catalogue: hbt.HBTCatalogue | None = None
        self.catalogue_error = ""

        try:
            self.catalogue = hbt.HBTCatalogue.load(self._catalogue_path())
        except (OSError, ValueError, KeyError, hbt.CatalogueError) as err:
            self.catalogue_error = str(err)
            print("HBT catalogue error:", err)

        self._update_palette_lists()


    # -----------------------------------------------------------------------------------------------------------------
    # palette
    # -----------------------------------------------------------------------------------------------------------------

    def _catalogue_path(self) -> str:
        """ catalogue file: palette value if set, else the JSON file next to this script """

        path = self.build_ele.CatalogueFile.value.strip()

        return path if path else hbt.DEFAULT_CATALOGUE


    def _update_palette_lists(self):
        """ make the selection valid and fill the dependent combo box lists and info fields """

        build_ele = self.build_ele
        cat       = self.catalogue

        if cat is None:
            build_ele.InfoText.value = f"Catalogue error: {self.catalogue_error}"
            return

        code, dia, spacing, box_length = cat.first_valid(build_ele.ProductType.value, build_ele.Diameter.value,
                                                         build_ele.Spacing.value, build_ele.BoxLength.value)

        build_ele.ProductType.value = code
        build_ele.Diameter.value    = dia
        build_ele.Spacing.value     = spacing
        build_ele.BoxLength.value   = box_length

        build_ele.TypeList.value      = "|".join(cat.type_codes())
        build_ele.DiameterList.value  = "|".join(cat.diameters(code))
        build_ele.SpacingList.value   = "|".join(cat.spacings(code, dia))
        build_ele.BoxLengthList.value = "|".join(cat.box_lengths(code))

        spec = cat.spec(code, dia, spacing, box_length)

        build_ele.TypeName.value         = spec.type_name
        build_ele.Article.value          = spec.article
        build_ele.BoxWidth.value         = spec.box_width
        build_ele.BoxDepth.value         = spec.box_depth
        build_ele.AnchorLength.value     = spec.anchor_length
        build_ele.ConnectionLength.value = spec.connection_length
        build_ele.RowDistance.value      = spec.row_distance
        build_ele.BarCount.value         = spec.bar_count * spec.rows

        warnings = spec.check()
        build_ele.InfoText.value = "; ".join(warnings) if warnings else "Catalogue values: PLACEHOLDER - verify!"


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
            try:
                self.catalogue       = hbt.HBTCatalogue.load(self._catalogue_path())
                self.catalogue_error = ""
            except (OSError, ValueError, KeyError, hbt.CatalogueError) as err:
                self.catalogue       = None
                self.catalogue_error = str(err)

        self._update_palette_lists()

        self.draw_preview()

        return True


    # -----------------------------------------------------------------------------------------------------------------
    # input
    # -----------------------------------------------------------------------------------------------------------------

    def start_input(self):
        """ start the input with the reference point """

        build_ele = self.build_ele

        build_ele.InputMode.value = build_ele.REF_POINT

        self.script_object_interactor = PointInteractor(self.pnt_result, True,
                                                        "HBT: reference point (box end on formwork face)",
                                                        self.draw_preview, z_coord_input = True)


    def start_next_input(self):
        """ start the next input after a point was clicked """

        build_ele = self.build_ele

        if build_ele.InputMode.value == build_ele.REF_POINT:
            self.ref_point = AllplanGeo.Point3D(self.pnt_result.input_point)

            build_ele.InputMode.value = build_ele.DIR_POINT

            self.script_object_interactor = PointInteractor(self.pnt_result, False,
                                                            "HBT: direction point (box length direction)",
                                                            self.draw_preview, z_coord_input = True,
                                                            start_point = self.ref_point)
            return

        # second point: create the fixture and restart for the next box

        fixture = self._create_fixture(self.ref_point, self.pnt_result.input_point)

        if fixture is not None:
            AllplanBaseEle.CreateElements(self.document, AllplanGeo.Matrix3D(), [fixture], [], None)

        self.start_input()


    def execute(self) -> CreateElementResult:
        """ execute the script (elements are created in start_next_input)

        Returns:
            empty result
        """

        return CreateElementResult()


    def on_cancel_function(self) -> OnCancelFunctionResult:
        """ ESC: back to the reference point input, or end the input

        Returns:
            cancel result
        """

        build_ele = self.build_ele

        BuildingElementListService.write_to_default_favorite_file([build_ele])

        if build_ele.InputMode.value == build_ele.DIR_POINT:
            return OnCancelFunctionResult.RESTART           # back to the reference point input

        return OnCancelFunctionResult.CANCEL_INPUT


    def draw_preview(self):
        """ draw the fixture preview at the cursor """

        build_ele = self.build_ele

        if build_ele.InputMode.value == build_ele.DIR_POINT:
            ref_point, dir_point = self.ref_point, self.pnt_result.input_point
        else:
            ref_point, dir_point = self.pnt_result.input_point, None

        result = self._build_geometry(ref_point, dir_point)

        if result is None:
            return

        matrix, elements, _, _ = result

        AllplanBaseEle.DrawElementPreview(self.document, matrix, elements, False, None)


    # -----------------------------------------------------------------------------------------------------------------
    # geometry and fixture
    # -----------------------------------------------------------------------------------------------------------------

    def _current_spec(self) -> hbt.HBTSpec | None:
        build_ele = self.build_ele

        if self.catalogue is None:
            return None

        return self.catalogue.spec(build_ele.ProductType.value, build_ele.Diameter.value,
                                   build_ele.Spacing.value, build_ele.BoxLength.value)


    def _placement_matrix(self,
                          ref_point: AllplanGeo.Point3D,
                          dir_point: AllplanGeo.Point3D | None) -> AllplanGeo.Matrix3D:
        """ local -> world matrix of the fixture """

        build_ele = self.build_ele

        ref = (ref_point.X, ref_point.Y, ref_point.Z)
        drp = None if dir_point is None else (dir_point.X, dir_point.Y, dir_point.Z)

        x_dir, _, z_dir = hbt.placement_axes(ref, drp, build_ele.FacePlane.value, build_ele.FlipSide.value)

        placement = AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(ref_point),
                                               AllplanGeo.Vector3D(*x_dir),
                                               AllplanGeo.Vector3D(*z_dir))

        return placement.GetTransformationMatrix()


    def _build_geometry(self,
                        ref_point: AllplanGeo.Point3D,
                        dir_point: AllplanGeo.Point3D | None):
        """ build the local geometry

        Returns:
            (placement matrix, all 3D elements, outline elements, layout) or None
        """

        spec = self._current_spec()

        if spec is None or spec.bar_count < 1:
            return None

        layout = hbt.compute_layout(spec, self.build_ele.BarState.value)

        box_prop = AllplanBaseEle.CommonProperties(self.build_ele.CommonProp.value)
        bar_prop = AllplanBaseEle.CommonProperties(self.build_ele.CommonProp.value)
        bar_prop.Color = self.build_ele.BarColor.value

        elements = [AllplanBasisEle.ModelElement3D(box_prop, _cuboid(pmin, pmax)) for pmin, pmax in layout.box_plates]

        radius = spec.diameter / 2

        for bar in layout.bars:
            elements.extend(AllplanBasisEle.ModelElement3D(bar_prop, brep) for brep in _bar_breps(bar, radius))

        outline = [AllplanBasisEle.ModelElement3D(box_prop, _cuboid(*layout.box_outline))]

        return self._placement_matrix(ref_point, dir_point), elements, outline, layout


    def _create_fixture(self,
                        ref_point: AllplanGeo.Point3D,
                        dir_point: AllplanGeo.Point3D) -> AllplanPrecast.FixturePlacementElement | None:
        """ create the precast point fixture """

        result = self._build_geometry(ref_point, dir_point)

        if result is None:
            return None

        matrix, elements, outline, layout = result
        build_ele = self.build_ele
        spec      = layout.spec

        com_prop = AllplanBaseEle.CommonProperties(build_ele.CommonProp.value)

        # ----- slides

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
        measure_pnt           = AllplanGeo.Point3D(*layout.dim_point)
        slides.append(AllplanPrecast.FixtureSlideElement(measure_prop,
                                                         [AllplanBasisEle.ModelElement3D(com_prop, measure_pnt)]))

        # ----- fixture definition (local coordinates, insertion point = reference point)

        fixture_prop                = AllplanPrecast.FixtureProperties()
        fixture_prop.Type           = AllplanPrecast.MacroType.ePoint_Fixture
        fixture_prop.SubType        = AllplanPrecast.MacroSubType.eJointReinforcement
        fixture_prop.Name           = spec.article
        fixture_prop.InsertionPoint = AllplanGeo.Point3D(*layout.ref_point)

        fixture = AllplanPrecast.FixtureElement(fixture_prop, slides)

        # same type and state -> same hash -> Allplan reuses the fixture definition
        hash_key = repr((spec, build_ele.BarState.value, build_ele.BarColor.value))
        fixture.SetHash(hashlib.sha224(hash_key.encode("utf-8")).hexdigest())

        # ----- placement

        placement_prop             = AllplanPrecast.FixturePlacementProperties()
        placement_prop.Name        = spec.article
        placement_prop.OutlineType = AllplanPrecast.OutlineType.eBUILTIN_OUTLINE_TYPE_MINUS \
                                     if build_ele.CutBoxVolume.value else \
                                     AllplanPrecast.OutlineType.eBUILTIN_OUTLINE_TYPE_NO_AFFECT
        placement_prop.OutlineShape = AllplanPrecast.OutlineShape.eBUILTIN_OUTLINE_SHAPE_RECTANGLE
        placement_prop.Matrix      = matrix

        return AllplanPrecast.FixturePlacementElement(com_prop, placement_prop, fixture)


# ---------------------------------------------------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------------------------------------------------

def _cuboid(pmin: hbt.Point, pmax: hbt.Point) -> AllplanGeo.BRep3D:
    """ axis parallel cuboid from min / max corner """

    return AllplanGeo.BRep3D.CreateCuboid(AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*pmin)),
                                          pmax[0] - pmin[0], pmax[1] - pmin[1], pmax[2] - pmin[2])


def _bar_breps(polyline: list[hbt.Point], radius: float) -> list[AllplanGeo.BRep3D]:
    """ bar as cylinders per segment plus spheres at the bends """

    breps = []

    for start, end in zip(polyline[:-1], polyline[1:]):
        vec    = (end[0] - start[0], end[1] - start[1], end[2] - start[2])
        length = math.sqrt(sum(c * c for c in vec))

        if length < 1e-6:
            continue

        z_dir = tuple(c / length for c in vec)
        x_dir = _any_perpendicular(z_dir)

        placement = AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*start),
                                               AllplanGeo.Vector3D(*x_dir), AllplanGeo.Vector3D(*z_dir))
        breps.append(AllplanGeo.BRep3D.CreateCylinder(placement, radius, length))

    for pnt in polyline[1:-1]:
        breps.append(AllplanGeo.BRep3D.CreateSphere(AllplanGeo.AxisPlacement3D(AllplanGeo.Point3D(*pnt)), radius))

    return breps


def _any_perpendicular(vec: tuple) -> tuple:
    """ a unit vector perpendicular to the unit vector vec """

    helper = (0.0, 0.0, 1.0) if abs(vec[2]) < 0.9 else (1.0, 0.0, 0.0)

    perp   = (vec[1] * helper[2] - vec[2] * helper[1],
              vec[2] * helper[0] - vec[0] * helper[2],
              vec[0] * helper[1] - vec[1] * helper[0])
    length = math.sqrt(sum(c * c for c in perp))

    return tuple(c / length for c in perp)
