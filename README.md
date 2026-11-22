# gbc engineers – Allplan PythonParts

Each PythonPart is a separate Allplan plugin in `plugins/<Name>/` and is delivered as an
**Allplan Extension Package (`.allep`)**: download the file and drag it into Allplan.

| PythonPart | Author | Package (download) | Instructions |
|---|---|---|---|
| HBT Fixture – HALFEN HBT rebend connections as precast fixtures | Em Than - gbc engineers | [`dist/HBT_Fixture.allep`](dist/HBT_Fixture.allep) | [plugins/HBT_Fixture/README.md](plugins/HBT_Fixture/README.md) |

## Install a PythonPart (short version)

1. Download the `.allep` file from the table above (*Download raw file*) or from a GitHub release.
2. Drag the file into the Allplan 2026 window and confirm.
3. Find it in the Library under **gbc engineers**, or on the Actionbar tab **Plug-ins**.

Details (office-wide installation, update, uninstall, first-time setup, troubleshooting) are in the
README of each PythonPart.

## For developers

| Task | Command |
|---|---|
| Build all packages | `python tools/build_allep.py` → `dist/<Name>.allep` and `dist/<Name>_<version>.allep` |
| Run all tests | `python -m pytest plugins/*/tests tools` (no Allplan needed) |
| Release | raise `plugin.version` in the plugin's `install-config.yml`, push a tag → GitHub Action `.github/workflows/build-allep.yml` builds, tests and creates a release draft with the `.allep` files |

Rules for new PythonParts: see [CLAUDE.md](CLAUDE.md).
Allplan documentation: [Allep packaging](https://pythonparts.allplan.com/2026/manual/for_developer/allep/),
[delivery](https://pythonparts.allplan.com/2026/manual/for_developer/delivery/).
