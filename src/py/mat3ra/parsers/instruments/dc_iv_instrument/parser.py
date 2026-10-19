from pathlib import Path

from mat3ra.parsers import BaseParser


class DcIvInstrumentParser(BaseParser):
    """
    DC I-V parser: a folder with IV_Volts.txt and IV_Amps.txt, one measurement per sweep row.

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
        lines = {
            name: (data_folder / name).read_text().splitlines(keepends=True) for name in ("IV_Volts.txt", "IV_Amps.txt")
        }
        measurements, files = {}, {}
        for row_number in range(1, len(lines["IV_Volts.txt"])):
            label = f"row{row_number}"
            measurements[label] = {
                "name": f"{data_folder.name} {label}",
                "description": f"{self.workflow['name']} at {label}",
                "status": "finished",
                "setup": {"instrument": {}},
                "workflow": self.workflow,
                "sample": {"name": label},
            }
            files[label] = {name: [lines[name][0], lines[name][row_number]] for name in lines}
        set_document = {"name": data_folder.name, "description": "", "metadata": {}}
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
