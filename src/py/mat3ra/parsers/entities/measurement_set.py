import json
import shutil
from pathlib import Path

from mat3ra.parsers import BaseParser
from mat3ra.parsers.factory import ParserFactory


class MeasurementSetParser(BaseParser):
    """
    Measurement set parser class: turns an instrument's delivered output into the folder mat3ra-upload reads.

    Args:
        content (str or Path): path to the delivered output: a run folder, a table or a data folder.
        workflow (dict): workflow document of the measurements.
        format (str): application parser, e.g. applications.asylum_spm.loop.
        version (str): application version.
    """

    def __init__(self, content, workflow, format: str = "", version: str = ""):
        super().__init__(content, format=format, version=version)
        self.workflow = workflow

    @property
    def pre_parser(self):
        parser_name = self.format
        return ParserFactory.get_class_by_name(parser_name)(self.content, self.workflow, version=self.version)

    def write(self, folder):
        """Writes set.json, <measurement>/measurement.json and <measurement>/files/ into the folder."""
        content = self.pre_parser.parse()["content"]
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "set.json").write_text(json.dumps(content["set"], indent=4))
        for name, measurement in content["measurements"].items():
            (folder / name).mkdir(exist_ok=True)
            (folder / name / "measurement.json").write_text(json.dumps(measurement, indent=4))
            for relative_path, source in content["files"][name].items():
                destination = folder / name / "files" / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
