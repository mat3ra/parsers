import json
from pathlib import Path

import mat3ra.fixtures
from mat3ra.esse import ESSE
from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

DATA_FOLDER = Path(mat3ra.fixtures.__file__).parent / "data/instruments/dc_iv_instrument/1.0/case-001/1448 DC IV data"
VOLTAGE_LINES = get_content_by_reference_path("instruments/dc_iv_instrument/v1.0/voltage").splitlines(keepends=True)
CURRENT_LINES = get_content_by_reference_path("instruments/dc_iv_instrument/v1.0/current").splitlines(keepends=True)
WORKFLOW = json.loads(get_content_by_reference_path("instruments/dc_iv_instrument/v1.0/workflow"))
EXPECTED_MEASUREMENT_NAMES = ["1448 DC IV data r1c1", "1448 DC IV data r1c2"]
EXPECTED_FIRST_ROW = {
    "name": "1448 DC IV data r1c1",
    "description": "DC I-V Sweep at site r1c1",
    "status": "finished",
    "setup": {"instrument": {}},
    "sample": {"name": "r1c1"},
}
EXPECTED_FILES = {
    "r1c1/files/IV_Volts.txt": VOLTAGE_LINES[0] + VOLTAGE_LINES[1],
    "r1c1/files/IV_Amps.txt": CURRENT_LINES[0] + CURRENT_LINES[1],
    "r1c2/files/IV_Volts.txt": VOLTAGE_LINES[0] + VOLTAGE_LINES[2],
    "r1c2/files/IV_Amps.txt": CURRENT_LINES[0] + CURRENT_LINES[2],
}


def test_dc_iv_instrument(tmp_path):
    tmp_path = tmp_path / "folder"
    esse = ESSE()
    MeasurementSetParser(DATA_FOLDER, WORKFLOW, format="instruments.dc_iv_instrument").write(tmp_path)
    measurements = [json.loads(path.read_text()) for path in sorted(tmp_path.glob("*/measurement.json"))]

    assert [measurement["name"] for measurement in measurements] == EXPECTED_MEASUREMENT_NAMES
    assert measurements[0] == {**EXPECTED_FIRST_ROW, "workflow": WORKFLOW}
    files = {path.relative_to(tmp_path).as_posix(): path.read_text() for path in tmp_path.glob("*/files/*")}
    assert files == EXPECTED_FILES
    for measurement in measurements:
        measurement.pop("sample")
        measurement_document = {**measurement, "_sample": {"_id": "sample"}}
        esse.validate(measurement_document, esse.get_schema_by_id("measurement"))
