import json
from pathlib import Path

import mat3ra.fixtures
from mat3ra.esse import ESSE
from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

RUN_FOLDER = Path(mat3ra.fixtures.__file__).parent / "data/instruments/asylum_spm/1.0/case-001"
WORKFLOW = json.loads(get_content_by_reference_path("instruments/asylum_spm/v1.0/workflow"))
PER_SITE = json.loads(get_content_by_reference_path("instruments/asylum_spm/v1.0/summary"))["recipe"]["per_site"]
EXPECTED_COUNTS = {"measurements": 2, "properties": 1, "files": 48}
EXPECTED_FILE_FOLDERS = {"r0c00/files/loops"}
EXPECTED_DESCRIPTIONS = [
    "SS-PFM hysteresis loop at site r0c00, 16 loops (8 on-field, 8 off-field)",
    "SS-PFM hysteresis loop at site r5c05, no loops",
]
EXPECTED_SETUP_KEYS = {
    "instrument": ["name"],
    "session": ["context", "instrument_directory", "n_measurements", "name", "recipe_name", "run_dir", "started_ts"],
    "settings": ["contact_feedback", "loop_settings", "pfm_excitation", "scan_settings"],
}
EXPECTED_PFM_EXCITATION_KEYS = ["dart_igain", "dart_width_hz", "drive_amplitude_v"]
EXPECTED_POINT_INDICES = [0, 1, 2, 3, 4, 5, 6, 7]
EXPECTED_FIRST_POINT = {
    "point_index": 0,
    "probe_position": {"x_m": -9.99999842279679e-07, "y_m": -1.0000001587949376e-06},
    "drive_frequency_hz": 369811.38,
    "file_path": "C:\\Users\\Asylum User\\Documents\\Asylum Research Data\\260831\\Image0231.ibw",
}
EXPECTED_WORKFLOW = {**WORKFLOW, "metadata": {"per_site": PER_SITE}}
HYSTERESIS_LOOP_SCHEMA_ID = "properties-directory/non-scalar/hysteresis-loop"
HYSTERESIS_LOOP_EXAMPLE_PATH = "properties_directory/non-scalar/hysteresis_loop"


def rounded(value):
    """The value, or every number in it, at the six significant digits of the esse example."""
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return float(f"{value:.6g}")


def points(property_document):
    """The (bias, on, off) points of a hysteresis loop, rounded."""
    return set(zip(*rounded([property_document["xDataArray"], *property_document["yDataSeries"]])))


def test_asylum_spm(tmp_path):
    tmp_path = tmp_path / "folder"
    esse = ESSE()
    MeasurementSetParser(RUN_FOLDER, WORKFLOW, format="instruments.asylum_spm").write(tmp_path)
    measurements = [json.loads(path.read_text()) for path in sorted(tmp_path.glob("*/measurement.json"))]
    properties = [document for measurement in measurements for document in measurement.get("properties", [])]
    example = next(item["data"] for item in esse.wrapped_examples if item["path"] == HYSTERESIS_LOOP_EXAMPLE_PATH)

    files = [path for path in tmp_path.glob("*/files/**/*") if path.is_file()]
    assert {"measurements": len(measurements), "properties": len(properties), "files": len(files)} == EXPECTED_COUNTS
    assert {path.parent.parent.relative_to(tmp_path).as_posix() for path in files} == EXPECTED_FILE_FOLDERS
    assert [measurement["description"] for measurement in measurements] == EXPECTED_DESCRIPTIONS
    assert measurements[0]["setup"]["points"][0] == EXPECTED_FIRST_POINT
    for measurement in measurements:
        setup = measurement["setup"]
        assert {block: sorted(setup[block]) for block in setup if block != "points"} == EXPECTED_SETUP_KEYS
        assert sorted(setup["settings"]["pfm_excitation"]) == EXPECTED_PFM_EXCITATION_KEYS
        assert [point["point_index"] for point in setup["points"]] == EXPECTED_POINT_INDICES
        assert measurement["workflow"] == EXPECTED_WORKFLOW
        assert "metadata" not in measurement
        esse.validate(measurement.pop("sample"), esse.get_schema_by_id("sample"))
        measurement_document = {**measurement, "_sample": {"_id": "sample"}}
        esse.validate(measurement_document, esse.get_schema_by_id("measurement"))
    esse.validate(properties[0], esse.get_schema_by_id(HYSTERESIS_LOOP_SCHEMA_ID))
    assert points(example) <= points(properties[0])
    assert rounded(properties[0]["parameters"]) == rounded(example["parameters"])
