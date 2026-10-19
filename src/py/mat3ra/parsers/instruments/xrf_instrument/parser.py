import csv
from pathlib import Path

from mat3ra.parsers import BaseParser


class XrfInstrumentParser(BaseParser):
    """
    XRF grid parser: a tab-separated table, one measurement per row.

    Args:
        content (str or Path): grid table path.
        workflow (dict): workflow document of the measurements.
        version (str): instrument version.
    """

    def __init__(self, content, workflow, version: str = "1.0"):
        super().__init__(content, version=version)
        self.workflow = workflow

    def parse(self):
        """Returns {"content": {"set", "measurements", "files"}, "version"}."""
        grid = Path(self.content)
        lines = grid.read_text().splitlines(keepends=True)
        measurements, files = {}, {}
        for line, row in zip(lines[1:], csv.DictReader(lines, delimiter="\t")):
            label = f"r{row['Row']}c{row['Column']}"
            position = {"coordinates": [float(row["x_mm"]), float(row["y_mm"])], "units": "mm"}
            measurements[label] = {
                "name": f"{grid.stem} {label}",
                "description": f"{self.workflow['name']} at site {label}",
                "status": "finished",
                "setup": {"instrument": {}},
                "workflow": self.workflow,
                "sample": {"name": label, "metadata": {"position": position}},
            }
            files[label] = {grid.name: [lines[0], line]}
        set_document = {"name": grid.stem, "description": "", "metadata": {}}
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
