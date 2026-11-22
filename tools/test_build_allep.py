""" tests for the .allep build script """

import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))

import build_allep  # noqa: E402


def test_all_plugins_build():
    assert build_allep.main([]) == 0
    for name in os.listdir(build_allep.PLUGINS_DIR):
        path = os.path.join(build_allep.DIST_DIR, f"{name}.allep")
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        assert "install-config.yml" in names                                  # config in the root
        assert all(n.split("/")[0] in build_allep.ALLOWED_DIRS | build_allep.ALLOWED_FILES for n in names)
        assert not any("__pycache__" in n or n.endswith(".pyc") or "/tests/" in n for n in names)


def test_missing_author_fails(tmp_path):
    import shutil
    import pytest
    src = os.path.join(build_allep.PLUGINS_DIR, "HBT_Fixture")
    dst = tmp_path / "HBT_Fixture"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "tests"))
    pyp = dst / "Library" / "gbc engineers" / "HBT Fixture.pyp"
    pyp.write_text(pyp.read_text(encoding="utf-8").replace("<!-- Author: Em Than - gbc engineers -->", ""),
                   encoding="utf-8")
    with pytest.raises(build_allep.BuildError, match="author"):
        build_allep.check_plugin(str(dst))
