# HBT Fixture – Allplan 2026 PythonPart

Places HBT rebend connection boxes as **Allplan precast point fixtures**.
Script type: Script Object (`create_script_object`, `PointInteractor`), based on the official
[PythonParts examples](https://github.com/NemetschekAllplan/PythonPartsExamples) and the
[PythonParts 2026 API](https://pythonparts.allplan.com/2026/).

> **Data source:** `PythonPartsScripts/HBT/HBT_Catalogue.json` was typed from the official
> *HALFEN HBT Rebend Connections – Technical Product Information HBT 22-E* (file
> `Halfen_HBT_Leviat_22_v_2026-03-EN.pdf`), pages 10–13. Re-check against the current catalogue before project use.

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

1. Palette **Product**: Rebar rows (single / double) → Casing type (HBT 55/85/120 or HBT 80/120/150/190/220)
   → Rebar type (1–4 or 5, 11, 22, 23, 33, 6–9) → Rebar Ø (8/10/12) → spacing s (10/15/20/25 cm)
   → element length (1250 / 800). Option HBT Strip (HBT-S) for double-row stirrup types.
2. Palette **Rebar dimensions**: with *Standard dimensions* on, h, lü and the leg (y, b, b1, b2) take the
   catalogue values (h = 170, lü = standard lü*, stirrups: lü,max). Turn it off to type own values;
   the **Check** field warns when h < hmin, lü > lü,max, stirrup lü < 60, or type 4 b outside its range.
3. Palette **Catalogue data** shows B, H2, b, number of rebars and end spacing a (from the catalogue table).
4. Palette **Placement**: formwork face, flip side, bar state (straightened / bent in casing), box-volume cut.
5. Click 1 = **reference point** (casing end on the formwork face, centre of casing width).
6. Click 2 = **direction** of the casing length (in plan). The fixture is created; input restarts.
   ESC in step 6 goes back to step 5, ESC in step 5 ends.

Fixture name = catalogue order designation, e.g. `HBT 85 - 10/10 - 2 - 1250, h = 170, lü = 430, b = 100`.

## Modelling limits

- Bend radii (D = 10Ø etc.) are not modelled; bends are sharp corners with a sphere.
- Anchor shapes of types 2, 4, 7, 8, 22, 23 are schematic (direction of the leg y / b / b1 / b2 only).
- Bent-in-casing state is schematic (legs drawn along the casing).
- H1 = 12 mm is stored but not drawn; the casing is drawn with depth H2.

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
