""" Company-wide HBT library: one JSON file per created product in a shared folder.

* identity = rows + order designation (Plan_text) + mandrel factors + Answer 1..5
* file name = <identity hash>.json, written atomically (temp file + os.replace), never overwritten
  -> several users can save at the same time without conflicts
* the same identity hash is used as the Allplan fixture hash, so identical products share one fixture
  definition in every project

Pure Python (no Allplan imports).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import tempfile

LIBRARY_ENV_VAR = "GBC_HBT_LIBRARY"
RECORD_VERSION  = 1

PRODUCT_KEYS = ("rows", "casing", "rebar_type", "diameter", "spacing_cm", "length", "h", "lu", "leg", "strip",
                "mandrel_catalogue", "mandrel_ec2")


def identity_key(designation: str, rows: int, answers: list[str], mandrel_catalogue: float,
                 mandrel_ec2: float) -> str:
    """ identity hash of a product (sha1, 40 hex characters) """

    core = {"designation": designation.strip(),
            "rows"       : int(rows),
            "answers"    : [a.strip() for a in (list(answers) + [""] * 5)[:5]],
            "mandrels"   : [round(float(mandrel_catalogue), 3), round(float(mandrel_ec2), 3)]}

    return hashlib.sha1(json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def record_label(record: dict) -> str:
    """ text for the palette list (no '|' allowed) """

    answers = [a for a in record.get("answers", []) if a]
    extra   = f" [{'; '.join(answers)}]" if answers else ""
    return f"{record['designation']}{extra} #{record['id'][:6]}".replace("|", "/")


class HBTLibrary:
    """ shared product library in a folder """

    def __init__(self, folder: str):
        self.folder  = folder
        self.records: dict[str, dict] = {}
        self.errors : list[str] = []

    # ----- reading

    def refresh(self) -> HBTLibrary:
        """ read all records of the folder (unreadable files are reported, not fatal) """

        self.records = {}
        self.errors  = []

        if not os.path.isdir(self.folder):
            return self

        for name in sorted(os.listdir(self.folder)):
            if not name.endswith(".json") or name.startswith("~"):
                continue
            try:
                with open(os.path.join(self.folder, name), encoding="utf-8") as file:
                    record = json.load(file)
                if record.get("id") and record.get("designation"):
                    self.records[record["id"]] = record
            except (OSError, ValueError) as err:
                self.errors.append(f"{name}: {err}")

        return self

    def find(self, key: str) -> dict | None:
        record = self.records.get(key)

        if record is None and os.path.isfile(self._file(key)):       # saved by someone else meanwhile
            try:
                with open(self._file(key), encoding="utf-8") as file:
                    record = json.load(file)
                self.records[key] = record
            except (OSError, ValueError):
                record = None

        return record

    def labels(self) -> list[str]:
        return sorted(record_label(r) for r in self.records.values())

    def by_label(self, label: str) -> dict | None:
        for record in self.records.values():
            if record_label(record) == label:
                return record
        return None

    # ----- writing

    def save(self, record: dict) -> tuple[dict, bool]:
        """ save a record if its identity does not exist yet

        Returns:
            (stored record, True if newly written / False if an existing record was reused)
        """

        existing = self.find(record["id"])

        if existing is not None:
            return existing, False

        os.makedirs(self.folder, exist_ok=True)

        record = dict(record)
        record.setdefault("version", RECORD_VERSION)
        record.setdefault("created", datetime.date.today().isoformat())

        fd, tmp = tempfile.mkstemp(prefix="~hbt_", suffix=".tmp", dir=self.folder)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(record, file, indent=1, ensure_ascii=False)

            if os.path.exists(self._file(record["id"])):              # another user was faster
                os.remove(tmp)
                return self.find(record["id"]) or record, False

            os.replace(tmp, self._file(record["id"]))
        except OSError:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

        self.records[record["id"]] = record
        return record, True

    def _file(self, key: str) -> str:
        return os.path.join(self.folder, f"{key}.json")


def resolve_folder(palette_value: str, fallback: str) -> tuple[str, str]:
    """ library folder: palette/pyp value, else environment variable, else fallback (Allplan Usr)

    Returns:
        (folder, source text)
    """

    if palette_value.strip():
        return palette_value.strip(), "palette"

    env = os.environ.get(LIBRARY_ENV_VAR, "").strip()

    if env:
        return env, f"environment variable {LIBRARY_ENV_VAR}"

    return fallback, "local fallback (no company path set)"
