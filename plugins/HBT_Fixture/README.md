# HBT Fixture – Allplan 2026 PythonPart

Places HALFEN HBT rebend connections as **Allplan precast point fixtures**: catalogue selection and
checks, correct bends, attributes (Plan_text, Answer 1–5) and a company-wide product library.

| | |
|---|---|
| Author | Em Than - gbc engineers |
| Package | [`dist/HBT_Fixture.allep`](../../dist/HBT_Fixture.allep) |
| Plugin version | see `install-config.yml` → `plugin.version` |
| Allplan | 2026 or newer |
| Install location | USR (current user) – change to STD for the whole office, see below |
| Library entry | `gbc engineers` → `HBT Fixture` |
| Actionbar | tab *Plug-ins* → task area *gbc HBT* |

> **Data source:** `HBT_Catalogue.json` was typed from *HALFEN HBT Rebend Connections – Technical Product
> Information HBT 22-E* (file `Halfen_HBT_Leviat_22_v_2026-03-EN.pdf`), pages 10–13 and 22.
> Re-check against the current catalogue before project use.

---

## 1. Installation (normal user)

1. Download **`HBT_Fixture.allep`**:
   - from the repository: `dist/HBT_Fixture.allep` (button *Download raw file*), or
   - from a GitHub release (file `HBT_Fixture_<version>.allep`), or
   - from the company share, if IT puts it there.
2. Start Allplan 2026 and open any drawing file.
3. **Drag the `.allep` file with the mouse into the Allplan window** and drop it.
4. Confirm the installation dialog. Restart Allplan if Allplan asks for it.
5. Check:
   - Library palette → `Office` / `Private` → **gbc engineers → HBT Fixture**, and
   - Actionbar → tab **Plug-ins** → task area **gbc HBT** (icon "HBT").

## 2. Installation for the whole office (STD)

Use this when Allplan uses a shared office (STD) folder on a server, so every user gets the same version.

1. In `install-config.yml` set `installation: target-location: STD`, raise `plugin.version`, rebuild
   (`python tools/build_allep.py`).
2. A user **with administrator rights** drags the `.allep` into Allplan once (Allplan docs: in a workgroup
   only administrators can install plugins into STD).
3. All users restart Allplan.

## 3. First-time setup (once per office)

| Setting | Where | What to enter |
|---|---|---|
| Company library folder | `Library/gbc engineers/HBT Fixture.pyp`, parameter `LibraryPath`, `<Value>` (before building), or palette page *Placement* → *Company library folder* | shared network folder, e.g. `\\server\Allplan\HBT_Library`; all users need write access |
| Alternative | Windows environment variable `GBC_HBT_LIBRARY` | same folder; used when the palette value is empty |
| Attributes | Allplan project attributes | `Plan_text` and `Answer 1` … `Answer 5` must exist in the project. Other names: edit `attributes` in `HBT_Catalogue.json` |

If no folder is set, products are saved in `<Allplan Usr>\HBT_Library` (only for this user). The palette
shows the folder in use.

## 4. Update

1. Get the newer `HBT_Fixture.allep`.
2. Drag it into Allplan again – the plugin manager replaces the old version.
3. Saved library records (JSON files in the company folder) are not touched.

## 5. Uninstall

Allplan → **Plugin manager** → select *HBT Fixture* → *Uninstall*.
The company library folder is not deleted.

## 6. Manual installation (without .allep)

Only if drag-and-drop is not possible. Copy, keeping the folder structure:

| From this plugin folder | To |
|---|---|
| `Library/gbc engineers/` | `<Allplan Usr or Std>\Library\gbc engineers\` |
| `PythonPartsScripts/gbc_engineers/hbt_fixture/` | `<Allplan Usr or Std>\PythonPartsScripts\gbc_engineers\hbt_fixture\` |
| `PythonPartsActionbar/gbc_engineers/` | `<Allplan Usr or Std>\PythonPartsActionbar\gbc_engineers\` (icons, optional) |

## 7. Troubleshooting

| Problem | Check |
|---|---|
| Not in the Library after installation | Restart Allplan; check *Plugin manager*; for STD: installed with admin rights? |
| Palette shows `Catalogue error` | `HBT_Catalogue.json` damaged or the *Catalogue file* field points to a wrong file |
| `Check: BLOCKED …` | The selection breaks a catalogue limit (text says which); the element is not created |
| Attributes empty on the fixture | Attribute names missing in the project; see Allplan trace window ("attribute not found") |
| Library status "save failed" | No write access to the company folder |
| Any Python error | Allplan → trace window: copy the full text and send it to the developer |

---

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

## Features waiting for the Allplan-tested script

The palette already has *Auto row on face*, *Automatic face detection* and *Check placed HBT*. The pure Python
part (`hbt_face.py`) is in the repository and tested; the Allplan part is in the locally tested
`HBTFixture.py`, which is not in the repository yet. Until it is merged, these controls show
"not in this build" and Auto row places a single element.

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

## For developers

| Task | Command / file |
|---|---|
| Run tests (no Allplan needed) | `python -m pytest plugins/HBT_Fixture/tests` |
| Build package | `python tools/build_allep.py HBT_Fixture` → `dist/HBT_Fixture.allep` |
| New release | raise `plugin.version` in `install-config.yml` (and `<Version>` in the .pyp if the PythonPart changed), build, commit, push a tag → GitHub Action creates a release draft with the `.allep` |
| Plugin UUID | `install-config.yml` → `plugin.UUID`; **never change it** (Allplan uses it to update the plugin) |

Folder structure:

```
plugins/HBT_Fixture/
├─ install-config.yml
├─ Library/gbc engineers/HBT Fixture.pyp (+ .png preview)
├─ PythonPartsActionbar/gbc_engineers/HBTFixture_24/_128(_dark).png
├─ PythonPartsScripts/gbc_engineers/hbt_fixture/
│  ├─ HBTFixture.py        script object (Allplan)
│  ├─ hbt_catalogue.py     catalogue, limits, bends, length split (pure Python)
│  ├─ hbt_library.py       company library (pure Python)
│  └─ HBT_Catalogue.json   product data
├─ tests/                  not packed into the .allep
└─ README.md               not packed into the .allep
```
