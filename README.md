# HBT Fixture – Allplan 2026 PythonPart

Places HALFEN HBT rebend connections as **Allplan precast point fixtures**, with catalogue checks,
correct bends, attributes and a company-wide product library.
Script type: Script Object, based on the official
[PythonParts examples](https://github.com/NemetschekAllplan/PythonPartsExamples) and the
[PythonParts 2026 API](https://pythonparts.allplan.com/2026/).

> **Data source:** `PythonPartsScripts/HBT/HBT_Catalogue.json` was typed from *HALFEN HBT Rebend Connections –
> Technical Product Information HBT 22-E* (file `Halfen_HBT_Leviat_22_v_2026-03-EN.pdf`), pages 10–13 and 22.
> Re-check against the current catalogue before project use.

## Files

| File | Purpose |
|---|---|
| `Library/HBT/HBT Fixture.pyp` | Palette (start file in the Allplan library); default company library path goes here |
| `PythonPartsScripts/HBT/HBTFixture.py` | Script object: palette, input modes, preview, fixtures, attributes, library |
| `PythonPartsScripts/HBT/hbt_catalogue.py` | Catalogue, limits, bar layout, bend (fillet) algorithm, length split (pure Python) |
| `PythonPartsScripts/HBT/hbt_library.py` | Company library: one JSON file per product (pure Python) |
| `PythonPartsScripts/HBT/HBT_Catalogue.json` | Product data, min. lengths, mandrels, attribute names |
| `tests/` | pytest tests, run without Allplan: `python -m pytest tests` |

## Installation

1. Copy `Library/HBT` to `<Allplan Std or Usr>\Library\`.
2. Copy `PythonPartsScripts/HBT` to `<Allplan Std or Usr>\PythonPartsScripts\`.
3. Set the company library folder: in `HBT Fixture.pyp`, parameter `LibraryPath`, `<Value>` =
   e.g. `\\server\Allplan\HBT_Library`. Empty = `<Usr>\HBT_Library` (local; the palette shows it).
   The environment variable `GBC_HBT_LIBRARY` is used when the palette value is empty.
4. Allplan: Library → `HBT` → `HBT Fixture`.

## Palette

**Page HBT**
- *Product*: rows → casing → rebar type → Ø → spacing → element length (1250 / 800 / Custom) → HBT Strip.
- *Rebar dimensions*: standard values (h = 170, lü*, y/b) or own values; hmin, lü,max, Lmin shown.
- *Bends*: D/Ø where the catalogue states D = 10Ø (legs b / b1 of types 2, 7, 23) and D/Ø for all
  other bends (EC2 default 4, user can change).
- *Catalogue data*: B, H2, b, number of rebars, end spacing a, **Check** (shows BLOCKED reasons).

**Page Placement**
- *Placement*: single element (2 clicks) or polyline; formwork face; flip side; bar state; casing cut.
- *Attributes*: Plan_text (automatic = catalogue order designation), Answer 1–5 (user input).
- *Company library*: folder in use, status (new / existing product), saved products list, Load, Refresh.

## Placement modes

1. **Single element**: click reference point (casing end on the formwork face), then direction point.
2. **Polyline**: click points, ESC creates. Each segment is split into elements:
   - 1250 and 800 standard elements first, then custom element(s) for the rest;
   - ranking: fewest custom elements → fewest elements → most 1250 elements;
   - every element must pass all catalogue limits; a segment that cannot be split is reported and skipped.
   - Vertical segments (e.g. wall joints) take the face normal from *Face normal for vertical segments*.

## Catalogue limits (hard block – the element is not created)

- h < hmin; lü > lü,max; stirrup lü < 60 mm; type 4 b outside its range; type 4 for single-row HBT 120.
- lü,max column: L ≥ 1250 → "L = 1250 mm", 800 ≤ L < 1250 → "L ≥ 800 mm".
- Custom length < 800 mm only for straight connection types with lü ≤ lü standard (320/390/460) and
  L ≥ minimum casing length of page 22. Custom length > 1250 mm: on request (blocked).
- Bars of custom lengths: n = floor((L − 2·25)/s) + 1, symmetric end spacing a ≥ 25 mm.
  Standard lengths use the catalogue table.

## Bends

Centre line corners are replaced by arcs: R = (D + Ø)/2, tangent length t = R·tan(θ/2), both straight
parts shortened by t. If two bends do not fit on one straight part, both radii are reduced proportionally.
The bar solid is a circle swept along the line/arc path (`CreateSweptBRep3D`); if Allplan rejects the
sweep, cylinders with arc approximation are used.

## Company library

- One JSON file per product, named by the identity hash, in the shared folder. Written atomically and
  never overwritten, so several users can save at the same time.
- Identity = rows + order designation + mandrels + Answer 1–5. If all of these match an existing record,
  the record is reused (status "Existing product") and the fixture gets the same hash, so Allplan uses one
  fixture definition.
- "Load selected" fills the palette from a saved product.

## Attributes

Attribute IDs are looked up by name (`AttributeService.GetAttributeID`). Names to try are in the JSON
(`attributes`): Plan_text, Answer 1..5 (also `Answer_1`, `Answer1`). Missing attributes are reported in the
Allplan trace window and skipped.

## Not yet tested in Allplan

Written without an Allplan installation; 59 tests run with stubbed Allplan modules. Test first:
- combo boxes with value lists from hidden string parameters;
- `CreateSweptBRep3D` with a line/arc `Path3D` (fallback exists);
- attribute names in your project (Plan_text, Answer 1..5) and writing them on the fixture placement;
- `eMEASURE_POINTS` slide with a `Point3D`; casing volume cut in precast elements;
- ESC behaviour of the polyline mode.

## Modelling limits

- Anchor shapes of types 2, 4, 7, 8, 22, 23 are schematic (leg direction); stirrup end width b − 3Ø not modelled.
- Bent-in-casing state is schematic. H1 = 12 mm is stored, not drawn.
