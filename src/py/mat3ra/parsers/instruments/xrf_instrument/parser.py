import csv
from pathlib import Path

from mat3ra.parsers import BaseParser


class XrfInstrumentParser(BaseParser):
    """
    XRF parser: a folder with a tab-separated table, one measurement per row.

    Args:
        content (str or Path): data folder path.
        workflow (dict): workflow document of the measurements.
        version (str): instrument version.
    """

    def __init__(self, content, workflow, version: str = "1.0"):
        super().__init__(content, version=version)
        self.workflow = workflow

    def parse(self):
        """Returns {"content": {"set", "measurements", "files"}, "version"}."""
        data_folder = Path(self.content).resolve()
        [table] = data_folder.glob("*.txt")
        lines = table.read_bytes().decode().splitlines(keepends=True)
        measurements, files = {}, {}
        for line, row in zip(lines[1:], csv.DictReader(lines, delimiter="\t")):
            label = f"r{row['Row']}c{row['Column']}"
            position = {"coordinates": [float(row["x_mm"]), float(row["y_mm"])], "units": "mm"}
            measurements[label] = {
                "name": f"{data_folder.name} {label}",
                "description": f"{self.workflow['name']} at site {label}",
                "status": "finished",
                "setup": {"instrument": {}},
                "workflow": self.workflow,
                "sample": {"name": label, "metadata": {"position": position}},
            }
            files[label] = {table.name: [lines[0], line]}
        set_document = {"name": data_folder.name, "description": "", "metadata": {}}
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
