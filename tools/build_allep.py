""" Build one Allplan Extension Package (.allep) per plugin folder.

Usage:
    python tools/build_allep.py              # all plugins in plugins/*
    python tools/build_allep.py HBT_Fixture  # one plugin

Each plugin folder (plugins/<Name>/) contains install-config.yml plus the Allplan folders
(Library, PythonPartsScripts, PythonPartsActionbar, ...). The package is written to
dist/<Name>.allep (stable download name) and dist/<Name>_<version>.allep.

Checks before packing: required config keys, UUID, semantic version, target location, all files
referenced by "tools", the script named in each .pyp, well-formed XML of each .pyp.
Text files are packed with CRLF line endings (Allplan docs warn about LF files).

Docs: https://pythonparts.allplan.com/2026/manual/for_developer/allep/
"""

from __future__ import annotations

import os
import re
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET

import yaml

ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(ROOT, "plugins")
DIST_DIR    = os.path.join(ROOT, "dist")

ALLOWED_DIRS  = {"Design", "Library", "prod", "Prod", "PythonPartsScripts", "PythonPartsActionbar", "Reports",
                 "VisualScripts"}
ALLOWED_FILES = {"install-config.yml", "requirements.in"}
TEXT_EXT      = {".py", ".pyp", ".yml", ".yaml", ".json", ".xml", ".txt", ".in", ".eng", ".deu", ".fra", ".pypsub"}
SKIP_PARTS    = {"__pycache__", ".pytest_cache"}
FIXED_TIME    = (2026, 1, 1, 0, 0, 0)
SEMVER        = re.compile(r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")


class BuildError(Exception):
    """ invalid plugin """


def _win_path(plugin_dir: str, rel: str) -> str:
    return os.path.join(plugin_dir, *rel.replace("\\", "/").split("/"))


def check_plugin(plugin_dir: str) -> dict:
    """ validate the plugin folder, return the parsed config """

    cfg_path = os.path.join(plugin_dir, "install-config.yml")

    if not os.path.isfile(cfg_path):
        raise BuildError("install-config.yml missing")

    with open(cfg_path, encoding="utf-8") as file:
        cfg = yaml.safe_load(file)

    plugin = cfg.get("plugin") or {}

    for key in ("name", "UUID", "version", "developer", "default-language", "min-allplan-version"):
        if key not in plugin:
            raise BuildError(f"plugin.{key} missing")

    uuid.UUID(str(plugin["UUID"]))

    if not SEMVER.match(str(plugin["version"])):
        raise BuildError(f"version '{plugin['version']}' is not semantic (x.y.z)")

    target = (cfg.get("installation") or {}).get("target-location")
    if target not in ("USR", "STD"):
        raise BuildError("installation.target-location must be USR or STD")

    lang = plugin["default-language"]
    ids  = set()

    for tool in cfg.get("tools") or []:
        ids.add(tool["id"])
        if lang not in (tool.get("display-name") or {}):
            raise BuildError(f"tool {tool['id']}: display-name for default language '{lang}' missing")
        for rel in [tool["pyp"]] + list((tool.get("icons") or {}).values()):
            if not os.path.isfile(_win_path(plugin_dir, rel)):
                raise BuildError(f"tool {tool['id']}: file not found: {rel}")

    for item in ((cfg.get("task-area") or {}).get("layout") or []):
        if item not in ("----", "****") and item not in ids:
            raise BuildError(f"task-area: unknown tool id '{item}'")

    # every .pyp: well-formed, script exists
    for base, _, files in os.walk(os.path.join(plugin_dir, "Library")):
        for name in files:
            if not name.endswith(".pyp"):
                continue
            path = os.path.join(base, name)
            try:
                tree = ET.parse(path)
            except ET.ParseError as err:
                raise BuildError(f"{name}: invalid XML: {err}") from err
            script = tree.findtext("Script/Name")
            if script and not os.path.isfile(_win_path(os.path.join(plugin_dir, "PythonPartsScripts"), script)):
                raise BuildError(f"{name}: script not found: PythonPartsScripts\\{script}")

    return cfg


def _files(plugin_dir: str):
    for entry in sorted(os.listdir(plugin_dir)):
        full = os.path.join(plugin_dir, entry)
        if os.path.isfile(full) and entry in ALLOWED_FILES:
            yield full, entry
        elif os.path.isdir(full) and entry in ALLOWED_DIRS:
            for base, dirs, files in os.walk(full):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_PARTS)
                for name in sorted(files):
                    if name.endswith(".pyc"):
                        continue
                    path = os.path.join(base, name)
                    yield path, os.path.relpath(path, plugin_dir).replace(os.sep, "/")


def build(plugin_name: str) -> list[str]:
    plugin_dir = os.path.join(PLUGINS_DIR, plugin_name)
    cfg        = check_plugin(plugin_dir)
    version    = cfg["plugin"]["version"]

    os.makedirs(DIST_DIR, exist_ok=True)
    outputs = [os.path.join(DIST_DIR, f"{plugin_name}.allep"),
               os.path.join(DIST_DIR, f"{plugin_name}_{version}.allep")]

    for out in outputs:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, arc in _files(plugin_dir):
                with open(path, "rb") as file:
                    data = file.read()
                if os.path.splitext(arc)[1].lower() in TEXT_EXT:
                    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                info = zipfile.ZipInfo(arc, FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, data)

    return outputs


def main(argv: list[str]) -> int:
    names = argv or sorted(d for d in os.listdir(PLUGINS_DIR)
                           if os.path.isfile(os.path.join(PLUGINS_DIR, d, "install-config.yml")))
    failed = False

    for name in names:
        try:
            for out in build(name):
                print(f"OK   {name}: {os.path.relpath(out, ROOT)}")
        except (BuildError, ValueError, KeyError, OSError) as err:
            print(f"FAIL {name}: {err}")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
