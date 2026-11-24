""" Create the skeleton of a new Allplan PythonPart plugin that passes tools/build_allep.py.

Usage (from the repository root):
    python .claude/skills/allep-package/scripts/new_plugin.py <Name> "<Title>" <snake_name> "<short>" [USR|STD]

    Name        plugin folder, PascalCase_With_Underscores        e.g. Corbel_Fixture
    Title       Library / Actionbar name of the PythonPart          e.g. "Corbel Fixture"
    snake_name  Python package under PythonPartsScripts/gbc_engineers e.g. corbel_fixture
    short       short label for the placeholder icon                e.g. "Corbel"
                (the Actionbar task area is always named "Em Than - gbc engineers")
    USR|STD     install location (default USR)

Creates plugins/<Name>/ with install-config.yml (new uuid4), .pyp (author comment + About/Author),
a script object skeleton, icons (24/128 px, light/dark), library preview, README template and a test.
Refuses to overwrite an existing plugin folder.
"""

from __future__ import annotations

__author__ = "Em Than - gbc engineers"

import os
import re
import sys
import uuid

AUTHOR = "Em Than - gbc engineers"
ROOT   = os.getcwd()


def _icon(path: str, size: int, dark: bool, label: str):
    """ simple placeholder icon (replace with a real one later) """

    from PIL import Image, ImageDraw, ImageFont

    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    drw = ImageDraw.Draw(img)
    fg  = (230, 235, 240, 255) if dark else (40, 60, 80, 255)
    drw.rounded_rectangle([big * 0.08, big * 0.08, big * 0.92, big * 0.92], radius=big // 8,
                          outline=(90, 160, 220, 255), width=big // 14)
    if size >= 128:
        font = ImageFont.load_default(size=int(big * 0.18)) if hasattr(ImageFont, "load_default") else None
        drw.text((big / 2, big / 2), label[:6], fill=fg, anchor="mm", font=font)
    img.resize((size, size), Image.LANCZOS).save(path)


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(__doc__)
        return 2

    name, title, snake, short = argv[:4]
    target = (argv[4] if len(argv) > 4 else "USR").upper()

    if not re.fullmatch(r"[A-Z][A-Za-z0-9]*(_[A-Z0-9][A-Za-z0-9]*)*", name):
        print("Name must be PascalCase_With_Underscores, e.g. Corbel_Fixture"); return 2
    if not re.fullmatch(r"[a-z][a-z0-9_]*", snake):
        print("snake_name must be lower case with underscores, e.g. corbel_fixture"); return 2
    if target not in ("USR", "STD"):
        print("target must be USR or STD"); return 2

    plugin = os.path.join(ROOT, "plugins", name)
    if os.path.exists(plugin):
        print(f"plugins/{name} exists already - nothing changed"); return 1

    script_cls = "".join(p.capitalize() for p in snake.split("_"))
    tool_id    = snake.replace("_", "-")
    lib_dir    = os.path.join(plugin, "Library", "gbc engineers")
    py_dir     = os.path.join(plugin, "PythonPartsScripts", "gbc_engineers", snake)
    icon_dir   = os.path.join(plugin, "PythonPartsActionbar", "gbc_engineers")
    for folder in (lib_dir, py_dir, icon_dir, os.path.join(plugin, "tests")):
        os.makedirs(folder)

    files = {
        os.path.join(plugin, "install-config.yml"): f"""# Allplan Extension Package (.allep) configuration
# Docs: https://pythonparts.allplan.com/2026/manual/for_developer/allep/
# Author: {AUTHOR}
plugin:
  name: {title}
  UUID: {uuid.uuid4()}          # never change this value
  version: 0.1.0       # semantic versioning; raise for every release
  developer: gbc-engineers
  default-language: en
  min-allplan-version: 2026

installation:
  target-location: {target}   # USR = current user only; STD = whole office (needs admin rights to install)

tools:
  - id: {tool_id}
    pyp: Library\\gbc engineers\\{title}.pyp
    display-name:
      en: {title}
      de: {title}
    icons:
      small: PythonPartsActionbar\\gbc_engineers\\{script_cls}_24.png
      large: PythonPartsActionbar\\gbc_engineers\\{script_cls}_128.png

task-area:
  display-name:
    en: {AUTHOR}
    de: {AUTHOR}
  layout:
    - {tool_id}
""",
        os.path.join(lib_dir, f"{title}.pyp"): f"""<?xml version="1.0" encoding="utf-8"?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
    <Script>
        <Name>gbc_engineers\\{snake}\\{script_cls}.py</Name>
        <Title>{title}</Title>
        <Version>0.1</Version>
        <ReadLastInput>True</ReadLastInput>
    </Script>
    <!-- Author: {AUTHOR} -->
    <Page>
      <Name>MainPage</Name>
      <Text>{title}</Text>
      <Parameters>
        <Parameter>
          <Name>CommonProp</Name>
          <Text></Text>
          <Value></Value>
          <ValueType>CommonProperties</ValueType>
        </Parameter>
        <Parameter>
          <Name>AboutExp</Name>
          <Text>About</Text>
          <ValueType>Expander</ValueType>
          <Parameters>
            <Parameter>
              <Name>AuthorText</Name>
              <Text>Author</Text>
              <Value>{AUTHOR}</Value>
              <ValueType>Text</ValueType>
            </Parameter>
          </Parameters>
        </Parameter>
      </Parameters>
    </Page>
</Element>
""",
        os.path.join(py_dir, "__init__.py"): f'""" {title} PythonPart package """\n\n__author__ = "{AUTHOR}"\n',
        os.path.join(py_dir, f"{script_cls}.py"): f'''""" {title} - Allplan 2026 PythonPart (script object) """

from __future__ import annotations

__author__ = "{AUTHOR}"

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from CreateElementResult import CreateElementResult

print("Load {script_cls}.py")


def check_allplan_version(_build_ele, _version) -> bool:
    """ support all versions """

    return True


def create_script_object(build_ele, script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    """ creation of the script object """

    return {script_cls}(build_ele, script_object_data)


class {script_cls}(BaseScriptObject):
    """ {title} """

    def __init__(self, build_ele, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele

    def execute(self) -> CreateElementResult:
        """ TODO: create the elements """

        return CreateElementResult()
''',
        os.path.join(plugin, "tests", f"test_{snake}.py"): f'''""" tests for {title} (pure Python parts, no Allplan needed) """

import os


def test_plugin_files_exist():
    root = os.path.join(os.path.dirname(__file__), "..")
    assert os.path.isfile(os.path.join(root, "install-config.yml"))
    assert os.path.isfile(os.path.join(root, "Library", "gbc engineers", "{title}.pyp"))
''',
        os.path.join(plugin, "README.md"): f"""# {title} – Allplan 2026 PythonPart

TODO: one paragraph on what the PythonPart does.

| | |
|---|---|
| Author | {AUTHOR} |
| Package | [`dist/{name}.allep`](../../dist/{name}.allep) |
| Plugin version | see `install-config.yml` → `plugin.version` |
| Allplan | 2026 or newer |
| Install location | {target} |
| Library entry | `gbc engineers` → `{title}` |
| Actionbar | tab *Plug-ins* → task area *{AUTHOR}* |

## 1. Installation (normal user)
1. Download **`{name}.allep`**. 2. Drag it into the Allplan window. 3. Confirm, restart Allplan if asked.
4. Library → **gbc engineers → {title}**, or Actionbar → **Plug-ins** → **{AUTHOR}**.

## 2. Installation for the whole office (STD)
Set `target-location: STD`, raise the version, rebuild; an administrator drags the `.allep` into Allplan once.

## 3. First-time setup
TODO (shared paths, attributes, data files).

## 4. Update
Drag the newer `.allep` into Allplan.

## 5. Uninstall
Allplan → Plugin manager → {title} → Uninstall.

## 6. Manual installation (without .allep)
| From | To |
|---|---|
| `Library/gbc engineers/` | `<Allplan Usr or Std>\\Library\\gbc engineers\\` |
| `PythonPartsScripts/gbc_engineers/{snake}/` | `<Allplan Usr or Std>\\PythonPartsScripts\\gbc_engineers\\{snake}\\` |
| `PythonPartsActionbar/gbc_engineers/` | `<Allplan Usr or Std>\\PythonPartsActionbar\\gbc_engineers\\` |

## 7. Troubleshooting
| Problem | Check |
|---|---|
| Not in the Library | restart Allplan, Plugin manager |
| Python error | Allplan trace window: send the full text to the developer |

## 8. Usage
TODO.

## 9. Not yet tested in Allplan / limits
TODO.

## 10. For developers
- Tests: `python -m pytest plugins/{name}/tests`
- Build: `python tools/build_allep.py {name}`
- Plugin UUID in `install-config.yml`: never change it.
""",
    }

    for path, text in files.items():
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)

    for size in (24, 128):
        for dark in (False, True):
            _icon(os.path.join(icon_dir, f"{script_cls}_{size}{'_dark' if dark else ''}.png"), size, dark, short)
    _icon(os.path.join(lib_dir, f"{title}.png"), 128, False, short)

    print(f"created plugins/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
