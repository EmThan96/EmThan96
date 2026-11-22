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
