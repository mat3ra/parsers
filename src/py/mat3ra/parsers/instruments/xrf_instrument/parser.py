import csv
from pathlib import Path

from mat3ra.parsers import BaseParser


class XrfInstrumentParser(BaseParser):
    """
    XRF parser: a tab-separated table, one measurement per row.

    Args:
        content (str or Path): table path.
        workflow (dict): workflow document of the measurements.
        version (str): instrument version.
    """

    def __init__(self, content, workflow, version: str = "1.0"):
        super().__init__(content, version=version)
        self.workflow = workflow

    def parse(self):
        """Returns {"content": {"set", "measurements", "files"}, "version"}."""
        table = Path(self.content)
        lines = table.read_bytes().decode().splitlines(keepends=True)
        measurements, files = {}, {}
        for line, row in zip(lines[1:], csv.DictReader(lines, delimiter="\t")):
            label = f"r{row['Row']}c{row['Column']}"
            position = {"coordinates": [float(row["x_mm"]), float(row["y_mm"])], "units": "mm"}
            measurements[label] = {
                "name": f"{table.stem} {label}",
                "description": f"{self.workflow['name']} at site {label}",
                "status": "finished",
                "setup": {"instrument": {}},
                "workflow": self.workflow,
                "sample": {"name": label, "metadata": {"position": position}},
            }
            files[label] = {table.name: [lines[0], line]}
        set_document = {"name": table.stem, "description": "", "metadata": {}}
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
