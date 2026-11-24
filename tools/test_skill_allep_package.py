""" tests for the allep-package skill scripts: a new skeleton must pass the build checks """

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

import build_allep  # noqa: E402

SKILL = os.path.join(build_allep.ROOT, ".claude", "skills", "allep-package", "scripts")


def _run(script, *args, cwd):
    return subprocess.run([sys.executable, os.path.join(SKILL, script), *args], cwd=cwd,
                          capture_output=True, text=True)


def test_new_plugin_passes_build_checks_and_bump(tmp_path):
    res = _run("new_plugin.py", "Demo_Part", "Demo Part", "demo_part", "Demo", "STD", cwd=tmp_path)
    assert res.returncode == 0, res.stdout + res.stderr
    plugin = tmp_path / "plugins" / "Demo_Part"
    cfg = build_allep.check_plugin(str(plugin))
    assert cfg["installation"]["target-location"] == "STD" and cfg["plugin"]["version"] == "0.1.0"

    res = _run("bump_version.py", "Demo_Part", "minor", "--pyp", cwd=tmp_path)
    assert res.returncode == 0 and "0.1.0 -> 0.2.0" in res.stdout
    assert build_allep.check_plugin(str(plugin))["plugin"]["version"] == "0.2.0"
    assert "<Version>0.2</Version>" in (plugin / "Library" / "gbc engineers" / "Demo Part.pyp").read_text(encoding="utf-8")

    assert _run("new_plugin.py", "Demo_Part", "Demo Part", "demo_part", "Demo", cwd=tmp_path).returncode == 1
