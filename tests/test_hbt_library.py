""" tests for the company library (pure Python) """

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PythonPartsScripts"))

from HBT import hbt_library as hlib  # noqa: E402


def _record(designation="HBT 85 - 10/15 - 1 - 1250, h = 170, lü = 390, y = 95", answers=("A", "", "", "", "")):
    key = hlib.identity_key(designation, 1, list(answers), 10, 4)
    return {"id": key, "designation": designation, "answers": list(answers), "rows": 1}


def test_identity_depends_on_answers_and_mandrels():
    d = "HBT 85 - 10/15 - 1 - 1250"
    base = hlib.identity_key(d, 1, ["A"], 10, 4)
    assert base == hlib.identity_key(d + " ", 1, ["A", "", "", "", ""], 10.0, 4.0)
    assert base != hlib.identity_key(d, 1, ["B"], 10, 4)
    assert base != hlib.identity_key(d, 1, ["A"], 10, 5)
    assert base != hlib.identity_key(d, 2, ["A"], 10, 4)


def test_save_reuse_and_reload(tmp_path):
    lib = hlib.HBTLibrary(str(tmp_path / "lib")).refresh()
    rec = _record()
    stored, new = lib.save(rec)
    assert new and stored["created"]
    again, new2 = lib.save(dict(rec, designation="changed"))
    assert not new2 and again["designation"] == rec["designation"]       # never overwritten

    other = hlib.HBTLibrary(str(tmp_path / "lib")).refresh()               # another user
    assert other.find(rec["id"])["designation"] == rec["designation"]
    assert other.labels() == [hlib.record_label(stored)]
    assert other.by_label(other.labels()[0])["id"] == rec["id"]
    assert not [f for f in os.listdir(tmp_path / "lib") if f.endswith(".tmp")]


def test_find_record_saved_by_someone_else(tmp_path):
    folder = tmp_path / "lib"
    lib = hlib.HBTLibrary(str(folder)).refresh()
    rec = _record(answers=("X", "", "", "", ""))
    folder.mkdir()
    (folder / f"{rec['id']}.json").write_text(json.dumps(rec), encoding="utf-8")
    assert lib.find(rec["id"]) is not None


def test_broken_file_reported(tmp_path):
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    lib = hlib.HBTLibrary(str(tmp_path)).refresh()
    assert lib.records == {} and lib.errors


def test_label_has_no_pipe():
    rec = _record(answers=("a|b", "", "", "", ""))
    assert "|" not in hlib.record_label(rec)


def test_resolve_folder(monkeypatch):
    monkeypatch.delenv(hlib.LIBRARY_ENV_VAR, raising=False)
    assert hlib.resolve_folder(r"\\srv\hbt", "C:\\usr")[0] == r"\\srv\hbt"
    assert hlib.resolve_folder("", "C:\\usr")[0] == "C:\\usr"
    monkeypatch.setenv(hlib.LIBRARY_ENV_VAR, r"\\srv\env")
    assert hlib.resolve_folder("", "C:\\usr")[0] == r"\\srv\env"
