# HBT Fixture – Allplan 2026 PythonPart

Places HBT rebend connection boxes as **Allplan precast point fixtures**.
Script type: Script Object (`create_script_object`, `PointInteractor`), based on the official
[PythonParts examples](https://github.com/NemetschekAllplan/PythonPartsExamples) and the
[PythonParts 2026 API](https://pythonparts.allplan.com/2026/).

> **Warning – catalogue values are placeholders.** The manufacturer's website was not reachable when
> this was written. Every number in `PythonPartsScripts/HBT/HBT_Catalogue.json` must be checked
> against the current official HBT technical product information before project use.

## Files

| File | Purpose |
|---|---|
| `Library/HBT/HBT Fixture.pyp` | Palette definition (start file in the Allplan library) |
| `PythonPartsScripts/HBT/HBTFixture.py` | Script object: palette logic, 2-click input, preview, fixture creation |
| `PythonPartsScripts/HBT/hbt_catalogue.py` | Pure Python: catalogue access, bar layout, placement axes (tested) |
| `PythonPartsScripts/HBT/HBT_Catalogue.json` | Product data (types, diameters, spacings, box sizes, lengths) |
| `tests/` | pytest tests (run without Allplan: `python -m pytest tests`) |

## Installation

1. Copy `Library/HBT` to `<Allplan Usr or Std>\Library\` (or any PythonParts library folder).
2. Copy `PythonPartsScripts/HBT` to `<Allplan Usr or Std>\PythonPartsScripts\`.
3. In Allplan: Library palette → `HBT` → `HBT Fixture`.

## Use

1. Palette **Product**: choose Type → Bar diameter → Bar spacing → Box length.
   The lists depend on each other and come from the JSON file. **Catalogue data** shows the resulting values.
2. Palette **Placement**: formwork face (horizontal / vertical with box horizontal / vertical with box vertical),
   flip anchor side, bar state (straightened or bent in box), optional box-volume cut.
3. Click 1 = **reference point** (box end on the formwork face, centre of box width).
4. Click 2 = **direction** of the box length (in plan). The fixture is created; input restarts.
   ESC in step 4 goes back to step 3, ESC in step 3 ends.

## Fixture definition

- Object: `FixturePlacementElement`, type `ePoint_Fixture`, subtype `eJointReinforcement`.
- Name: e.g. `HBT-1R D12-150 L=1250` (pattern in JSON → `article_pattern`).
- **Reference point** = fixture insertion point = box end on the face.
- **Dimensioning point** = centre of the box on the face, stored in an `eMEASURE_POINTS` slide.
- Slides: `e3D_VIEW` (box + bars), `e3D_VIEW_OUTLINE_VOLUME` (box volume), `eMEASURE_POINTS`.
- Same product + state → same hash → Allplan reuses one fixture definition.

Local axes: x = box length, y = box width, z = into the first pour (anchor side).

## Snapping

Point input uses Allplan's standard coordinate input, so the user's **point snap settings** apply:
end points, mid points, edges, intersections and the points of existing fixtures.
For "mid point / edge first", enable those snap options in Allplan (Options → Point snap / Track tracing).
The script does not override the snap priority; the PythonParts API does not offer this in `PointInteractor`.

## Extending the catalogue

Add a type to `types` in the JSON. Supported: `rows` 1 or 2; `anchor_shape` `straight`, `hook90`, `u`.
The JSON is validated on load; errors appear in the palette **Info** field.
A different JSON file can be set in **Catalogue file**.

## Not yet tested in Allplan

This was written without an Allplan installation. Test these first:
- `StringComboBox` with `<ValueList>TypeList</ValueList>` (list taken from a hidden string parameter "a|b|c").
- `eMEASURE_POINTS` slide with a `Point3D` as dimensioning point.
- Box-volume cut (`eBUILTIN_OUTLINE_TYPE_MINUS`) inside a precast element.
