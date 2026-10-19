from pathlib import Path

from mat3ra.parsers import BaseParser


class DcIvInstrumentSweepParser(BaseParser):
    """
    DC I-V parser: a folder with IV_Volts.txt and IV_Amps.txt, one measurement per sweep row.

    Args:
        content (str): data folder path.
        workflow (dict): workflow document of the measurements.
        version (str): application version.
    """

    def __init__(self, content, workflow, version: str = "1.0"):
        super().__init__(content, version=version)
        self.workflow = workflow

    def parse(self):
        data_folder = Path(self.content)
        voltage_lines = (data_folder / "IV_Volts.txt").read_text().splitlines()[1:]
        measurements, files = {}, {}
        for row_number in range(1, len(voltage_lines) + 1):
            label = f"row{row_number}"
            measurements[label] = {
                "name": f"{data_folder.name} {label}",
                "description": f"{self.workflow['name']} at {label}",
                "status": "finished",
                "setup": {"instrument": {}},
                "workflow": self.workflow,
                "sample": {"name": label},
            }
            files[label] = {file_name: data_folder / file_name for file_name in ("IV_Volts.txt", "IV_Amps.txt")}
        set_document = {"name": data_folder.name, "description": "", "metadata": {}}
        return {"content": {"set": set_document, "measurements": measurements, "files": files}, "version": self.version}
