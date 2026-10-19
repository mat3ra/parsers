import json
from pathlib import Path

import mat3ra.fixtures
from mat3ra.esse import ESSE
from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

GRID_PATH = (
    Path(mat3ra.fixtures.__file__).parent / "data/applications/xrf_instrument/1.0/case-001/com5_1448_xrf_grid.txt"
)
GRID = get_content_by_reference_path("applications/xrf_instrument/v1.0/grid")
WORKFLOW = json.loads(get_content_by_reference_path("applications/xrf_instrument/v1.0/workflow"))
EXPECTED_MEASUREMENT_NAMES = ["com5_1448_xrf_grid r1c1", "com5_1448_xrf_grid r1c2"]
EXPECTED_FIRST_SITE = {
    "name": "com5_1448_xrf_grid r1c1",
    "description": "XRF Grid Map at site r1c1",
    "status": "finished",
    "setup": {"instrument": {}},
    "sample": {"name": "r1c1", "metadata": {"position": {"coordinates": [5.4000001, 6.6500001], "units": "mm"}}},
}
EXPECTED_FILES = {"r1c1/files/com5_1448_xrf_grid.txt": GRID, "r1c2/files/com5_1448_xrf_grid.txt": GRID}


def test_xrf_instrument_map(tmp_path):
    tmp_path = tmp_path / "folder"
    esse = ESSE()
    MeasurementSetParser(GRID_PATH, WORKFLOW, format="applications.xrf_instrument.map").write(tmp_path)
    measurements = [json.loads(path.read_text()) for path in sorted(tmp_path.glob("*/measurement.json"))]

    assert [measurement["name"] for measurement in measurements] == EXPECTED_MEASUREMENT_NAMES
    assert measurements[0] == {**EXPECTED_FIRST_SITE, "workflow": WORKFLOW}
    files = {path.relative_to(tmp_path).as_posix(): path.read_text() for path in tmp_path.glob("*/files/*")}
    assert files == EXPECTED_FILES
    for measurement in measurements:
        measurement.pop("sample")
        measurement_document = {**measurement, "_sample": {"_id": "sample"}}
        esse.validate(measurement_document, esse.get_schema_by_id("measurement"))
