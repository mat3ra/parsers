import json
import sys
from pathlib import Path

import mat3ra.fixtures
from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.cli import parse
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

CASE_FOLDER = Path(mat3ra.fixtures.__file__).parent / "data/applications/asylum_spm/1.0/case-001"
WORKFLOW = json.loads(get_content_by_reference_path("applications/asylum_spm/v1.0/workflow"))


def test_main(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mat3ra-parse", "asylum-spm", str(CASE_FOLDER), str(tmp_path / "command")])
    parse.main()
    MeasurementSetParser(CASE_FOLDER, WORKFLOW, format="applications.asylum_spm.loop").write(tmp_path / "entity")

    documents = [
        json.loads((tmp_path / folder / "r0c00" / "measurement.json").read_text()) for folder in ("command", "entity")
    ]
    assert documents[0] == documents[1]
