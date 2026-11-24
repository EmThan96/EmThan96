# Rules for this repository (Allplan PythonParts of gbc engineers)

These rules apply to every PythonPart created or changed in this repository.

## Structure: one plugin per PythonPart

```
plugins/<Name>/                      Name in PascalCase_With_Underscores, e.g. HBT_Fixture
├─ install-config.yml                Allep config (plugin, installation, tools, task-area)
├─ Library/gbc engineers/<Title>.pyp (+ <Title>.png library preview, 128 px)
├─ PythonPartsActionbar/gbc_engineers/<Tool>_24.png, _24_dark.png, _128.png, _128_dark.png
├─ PythonPartsScripts/gbc_engineers/<snake_name>/   __init__.py + scripts + data
├─ tests/                            pytest, runnable without Allplan (stub Allplan modules)
└─ README.md                         full user + developer guide (template below)
```

- Do NOT put an `__init__.py` directly in `PythonPartsScripts/gbc_engineers/` (namespace package):
  several plugins install into this folder; uninstalling one must not break the others.
- In the .pyp: `<Script><Name>gbc_engineers\<snake_name>\<Script>.py</Name>`.
- Imports inside scripts: `from gbc_engineers.<snake_name> import <module>`.
- Keep Allplan-independent logic in pure Python modules so it can be tested.

## Author (always)

Every PythonPart carries the author **Em Than - gbc engineers** in all of these places (the build fails otherwise):
- `.pyp`: comment `<!-- Author: Em Than - gbc engineers -->` after `</Script>` and an expander `AboutExp` with a
  `Text` parameter `AuthorText` = `Em Than - gbc engineers` (the .pyp schema has no author tag).
- `install-config.yml`: comment line `# Author: Em Than - gbc engineers`.
- every Python module: `__author__ = "Em Than - gbc engineers"` after the module docstring and after `from __future__ import ...` (Python requires that import first).
- plugin README info table: row `| Author | Em Than - gbc engineers |`; root README table: column Author.
- Company name in lowercase (gbc engineers) - organization writing rule.

## Packaging (always)

Use the project skill `.claude/skills/allep-package` (scripts for a new plugin skeleton and version bumps,
confirmation rules, checks, known Allplan pitfalls).


- Every new PythonPart gets an `install-config.yml` with a NEW `uuid4` (never change it later),
  `developer: gbc-engineers`, `min-allplan-version: 2026`, `target-location: USR` unless the user says STD,
  one `tools` entry with icons, and a task area named `gbc <short name>`.
- After every change: raise `plugin.version` (semver) and the .pyp `<Version>` if the PythonPart changed,
  run `python tools/build_allep.py`, run all tests, and commit `dist/<Name>.allep` together with the source.
- Add the PythonPart to the table in the root `README.md`.
- Validate each .pyp against https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd when the network allows.

## README template for each plugin (`plugins/<Name>/README.md`)

1. Title, one-paragraph purpose, info table (package link, version, Allplan version, install location,
   Library entry, Actionbar location), data sources.
2. Installation (normal user): download `.allep` → drag into Allplan → confirm → where to find it.
3. Installation for the whole office (STD), incl. admin-rights note.
4. First-time setup (shared paths, attributes, catalogue files).
5. Update. 6. Uninstall (Plugin manager). 7. Manual installation without .allep (folder table).
8. Troubleshooting table.
9. Usage: palette, input modes, rules/limits.
10. Not yet tested in Allplan / modelling limits (be honest).
11. For developers: tests, build, release, UUID rule, folder tree.

Write in plain English (readers are often non-native speakers). Company name always lowercase: gbc engineers.
