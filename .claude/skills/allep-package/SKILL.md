---
name: allep-package
description: Package Allplan 2026 PythonParts of gbc engineers as Allplan Extension Packages (.allep) - create a new plugin skeleton, raise the version, run the checks and tests, build dist/<Name>.allep, update the README and push. Use whenever a PythonPart in this repository is created or changed, or the user asks to "package", "đóng gói", "build allep", "make an installer", "release" or "drag-and-drop install" a PythonPart. Author: Em Than - gbc engineers.
---

# Package a PythonPart as .allep

Author: Em Than - gbc engineers. Repository rules: `CLAUDE.md` (structure, author, packaging, README template).
Allplan docs: https://pythonparts.allplan.com/2026/manual/for_developer/allep/

## What to confirm with the user (and what not)

Ask only what cannot be derived. Put all open questions into ONE question round (AskUserQuestion),
each with a recommended default.

| Situation | Ask the user | Default to propose |
|---|---|---|
| **New plugin** | plugin folder name, Title (Library/Actionbar name) | derived from the PythonPart name, e.g. `Corbel_Fixture`, `Corbel Fixture` |
| **New plugin** | install location **USR** (each user, no admin) or **STD** (whole office, admin must install) | USR |
| New plugin with shared paths / attributes | values the user did not give (e.g. company network folder) | leave empty, explain the fallback |
| Existing plugin, change is a **breaking** change | major version? | - |
| **Before `git push`, a tag or a GitHub release** | show branch, commit list, version, `.allep` file; wait for "yes" (organization rule: anything sent out needs a preview and a yes) | - |

Never ask, decide yourself and state it in one line:
- UUID: new `uuid4` for a new plugin; NEVER change an existing UUID (Allplan uses it to update the plugin).
- Author `Em Than - gbc engineers`, Actionbar task area `Em Than - gbc engineers`, `developer: gbc-engineers`,
  `min-allplan-version: 2026` (fixed by CLAUDE.md). Company name always lowercase (organization rule),
  even if asked for "Gbc" / "GBC" - say so in one line.
- Version level for an existing plugin: **patch** = bug fix, **minor** = new feature / new palette control.
  Raise the `.pyp <Version>` (`--pyp`) whenever the PythonPart itself changed.
- Icons: placeholder icons from the skeleton unless the user gives real ones.

## Steps

Run everything from the repository root.

1. **New plugin only** - after the questions above:
   `python .claude/skills/allep-package/scripts/new_plugin.py <Name> "<Title>" <snake_name> "<short>" [USR|STD]`
   Then write the real script, palette and tests into the created folders. Add the plugin to the table in the
   root `README.md` (columns: PythonPart, Author, Package, Instructions).
2. **Changed plugin** - raise the version:
   `python .claude/skills/allep-package/scripts/bump_version.py <Name> patch|minor|major [--pyp]`
3. **Checks** (all must pass; fix, never skip):
   - `python -m pyflakes plugins/<Name>/PythonPartsScripts tools`
   - every `build_ele.X` used in the scripts exists as `<Name>X</Name>` in the .pyp
   - .pyp against the XSD when the network allows:
     https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd (+ PythonPartParameter.xsd), e.g. with `lxml`
   - `python -m pytest -q plugins/<Name>/tests tools`
4. **Build**: `python tools/build_allep.py <Name>` -> `dist/<Name>.allep` and `dist/<Name>_<version>.allep`.
   The build itself fails on: missing author (pyp comment, AboutExp/AuthorText, `# Author:` in the config,
   `__author__` in every module), bad UUID / version / target, missing tool files, script named in the .pyp
   not found, invalid XML. Read the FAIL line and fix the cause.
5. **README** of the plugin: keep the CLAUDE.md template complete (install, office install, setup, update,
   uninstall, manual install, troubleshooting, usage, limits, developers). Update version-dependent text.
6. **Commit** source + `dist/<Name>.allep` together (versioned `dist/*_x.y.z.allep` is git-ignored).
7. **Preview and push** - show the user: branch, commits, new version, package path; push only after "yes".
   Releases: a pushed tag starts `.github/workflows/build-allep.yml` (tests, build, release draft).
8. **Report** to the user: version, download link of `dist/<Name>.allep` on GitHub, how to install
   (drag into Allplan, restart), what was not tested in Allplan.

## Known Allplan pitfalls (seen in Allplan 2026 traces)

- `StringComboBox` `<ValueList>` with a dynamic list: use `str(MyList)` where `MyList` is a hidden String
  parameter `"a|b|c"`. A bare name is split into characters; a formula returning a Python list fails
  (`'list' object has no attribute 'split'`).
- Fixture measure points (`eMEASURE_POINTS` slide) must be `Symbol3DElement`, not `ModelElement3D(Point3D)`.
- Raise a geometry version in the fixture hash when fixture geometry changes, or Allplan reuses the old definition.
- Python requires `from __future__ import ...` first; put `__author__` after it.
- Do not put `__init__.py` directly into `PythonPartsScripts/gbc_engineers/` (shared by several plugins).
- Text files are packed with CRLF by the build script; do not edit the zip by hand.
