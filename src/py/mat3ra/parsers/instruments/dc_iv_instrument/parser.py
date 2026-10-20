import csv
from pathlib import Path

from mat3ra.parsers import BaseParser


class DcIvInstrumentParser(BaseParser):
    """
    DC I-V parser: a folder with IV_Volts.txt, IV_Amps.txt and IV_Positions.txt, one measurement per sweep row.

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
        data_folder = Path(self.content)
        lines_by_file = {
            name: (data_folder / name).read_bytes().decode().splitlines(keepends=True)
            for name in ("IV_Volts.txt", "IV_Amps.txt")
        }
        positions = csv.DictReader(
            (data_folder / "IV_Positions.txt").read_bytes().decode().splitlines(), delimiter="\t"
        )
        measurements, files = {}, {}
        for row_number, position in enumerate(positions, start=1):
            label = f"r{position['Row']}c{position['Column']}"
            measurements[label] = {
                "name": f"{data_folder.name} {label}",
                "description": f"{self.workflow['name']} at {label}",
                "status": "finished",
                "setup": {"instrument": {}},
                "workflow": self.workflow,
                "sample": {"name": label},
            }
            files[label] = {name: [lines_by_file[name][0], lines_by_file[name][row_number]] for name in lines_by_file}
        set_document = {"name": data_folder.name, "description": "", "metadata": {}}
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
