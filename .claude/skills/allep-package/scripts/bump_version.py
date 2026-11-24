""" Raise the version of a plugin: install-config.yml (semver) and optionally the .pyp <Version>.

Usage (from the repository root):
    python .claude/skills/allep-package/scripts/bump_version.py <Name> patch|minor|major [--pyp]

    --pyp   also raise <Version> of every .pyp of the plugin by 0.1 (use when the PythonPart changed)
Prints old -> new versions. Changes only the version lines.
"""

from __future__ import annotations

__author__ = "Em Than - gbc engineers"

import glob
import os
import re
import sys


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("patch", "minor", "major"):
        print(__doc__)
        return 2

    name, level = argv[0], argv[1]
    plugin = os.path.join(os.getcwd(), "plugins", name)
    cfg    = os.path.join(plugin, "install-config.yml")

    with open(cfg, encoding="utf-8") as file:
        text = file.read()

    match = re.search(r"^(\s*version:\s*)(\d+)\.(\d+)\.(\d+)", text, re.M)
    if not match:
        print("plugin.version not found"); return 1

    major, minor, patch = (int(match.group(i)) for i in (2, 3, 4))
    new = {"major": (major + 1, 0, 0), "minor": (major, minor + 1, 0), "patch": (major, minor, patch + 1)}[level]
    new_text = f"{new[0]}.{new[1]}.{new[2]}"

    text = text[:match.start(2)] + new_text + text[match.end(4):]
    with open(cfg, "w", encoding="utf-8") as file:
        file.write(text)
    print(f"plugin.version {major}.{minor}.{patch} -> {new_text}")

    if "--pyp" in argv:
        for pyp in glob.glob(os.path.join(plugin, "Library", "**", "*.pyp"), recursive=True):
            with open(pyp, encoding="utf-8") as file:
                ptext = file.read()
            pmatch = re.search(r"<Version>([\d.]+)</Version>", ptext)
            if pmatch:
                old = float(pmatch.group(1))
                ptext = ptext.replace(pmatch.group(0), f"<Version>{old + 0.1:.1f}</Version>", 1)
                with open(pyp, "w", encoding="utf-8") as file:
                    file.write(ptext)
                print(f"{os.path.basename(pyp)} <Version> {old} -> {old + 0.1:.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
