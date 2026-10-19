"""Writes the folder mat3ra-upload takes from an instrument's output, with the example workflow of its application."""

import argparse
import json
from pathlib import Path

from mat3ra.fixtures import get_content_by_reference_path
from mat3ra.parsers.entities.measurement_set import MeasurementSetParser

WORKFLOW_VERSION = "v1.0"


def main():
    """Parses the three arguments, writes the folder and prints the number of measurements."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    application = arguments.application.replace("-", "_")
    workflow = json.loads(get_content_by_reference_path(f"applications/{application}/{WORKFLOW_VERSION}/workflow"))
    unit = workflow["subworkflows"][0]["units"][0]
    parser_format = f"applications.{unit['application']['name'].replace('-', '_')}.{unit['executable']['name']}"
    count = MeasurementSetParser(arguments.input, workflow, format=parser_format).write(arguments.output)
    print(f"{count} measurements in {arguments.output}")


if __name__ == "__main__":
    main()
