import json
from pathlib import Path

import mat3ra.fixtures
from mat3ra.esse import ESSE
from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

DATA_FOLDER = Path(mat3ra.fixtures.__file__).parent / "data/applications/dc_iv_instrument/1.0/case-001/1448 DC IV data"
VOLTAGE = get_content_by_reference_path("applications/dc_iv_instrument/v1.0/voltage")
CURRENT = get_content_by_reference_path("applications/dc_iv_instrument/v1.0/current")
WORKFLOW = json.loads(get_content_by_reference_path("applications/dc_iv_instrument/v1.0/workflow"))
EXPECTED_MEASUREMENT_NAMES = ["1448 DC IV data row1", "1448 DC IV data row2"]
EXPECTED_FIRST_ROW = {
    "name": "1448 DC IV data row1",
    "description": "DC I-V Sweep at row1",
    "status": "finished",
    "setup": {"instrument": {}},
    "sample": {"name": "row1"},
}
EXPECTED_FILES = {
    "row1/files/IV_Volts.txt": VOLTAGE,
    "row1/files/IV_Amps.txt": CURRENT,
    "row2/files/IV_Volts.txt": VOLTAGE,
    "row2/files/IV_Amps.txt": CURRENT,
}


def test_dc_iv_instrument_sweep(tmp_path):
    tmp_path = tmp_path / "folder"
    esse = ESSE()
    MeasurementSetParser(DATA_FOLDER, WORKFLOW, format="applications.dc_iv_instrument.sweep").write(tmp_path)
    measurements = [json.loads(path.read_text()) for path in sorted(tmp_path.glob("*/measurement.json"))]

    assert [measurement["name"] for measurement in measurements] == EXPECTED_MEASUREMENT_NAMES
    assert measurements[0] == {**EXPECTED_FIRST_ROW, "workflow": WORKFLOW}
    files = {path.relative_to(tmp_path).as_posix(): path.read_text() for path in tmp_path.glob("*/files/*")}
    assert files == EXPECTED_FILES
    for measurement in measurements:
        measurement.pop("sample")
        measurement_document = {**measurement, "_sample": {"_id": "sample"}}
        esse.validate(measurement_document, esse.get_schema_by_id("measurement"))
