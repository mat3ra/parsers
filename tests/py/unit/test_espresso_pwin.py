from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.applications.espresso.pwin import EspressoPwinParser


def test_espresso_pwx_stdin():
    file_content = get_content_by_reference_path("applications/espresso/v5.4.0/stdin")
    parser = EspressoPwinParser(content=file_content)

    namelist_control = parser.namelists.get("control", {})
    calculation_value = namelist_control.get("calculation")

    assert calculation_value == "scf"


def test_get_namelist_parses_indexed_fortran_keys():
    content = """
&SYSTEM
    ibrav = 1
    celldm(1) = 15.9018255
    starting_magnetization(2) = 0.5
/
"""
    parser = EspressoPwinParser(content=content)
    system = parser.get_namelist("SYSTEM")

    assert system["ibrav"] == "1"
    assert system["celldm1"] == "15.9018255"
    assert system["starting_magnetization2"] == "0.5"
