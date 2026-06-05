import re

from mat3ra.parsers import BaseParser
from mat3ra.regex.data.schemas import SCHEMAS
from mat3ra.utils import object as object_utils
from mat3ra.utils import regex as regex_utils


class EspressoPwxStdinParser(BaseParser):
    """
    Espresso PWX stdin parser class.
    """

    schema_path = "/applications/espresso/5.2.1/pw.x/"

    def __init__(self, content, version: str = "5.4.0"):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): file version.
        """
        super().__init__(content, version=version)
        self.namelist_regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + "control/_format/namelist"
        )
        self.namelist_regex = self.namelist_regex_object["regex"]
        self.namelist_flags = self.namelist_regex_object["flags"]
        self.namelist_regex_control = self.namelist_regex.replace("{{BLOCK_NAME}}", "CONTROL")
        self.namelist_regex_electrons = self.namelist_regex.replace("{{BLOCK_NAME}}", "ELECTRONS")

    def get_namelist_as_dict(self, namelist_name: str) -> dict:
        """
        Extracts an entire namelist block and parses all key=value pairs into a dictionary.
        This handles standard keys and Fortran arrays like celldm(N).
        """
        # Get the regex for the specific namelist block from schemas
        block_regex_str = self.namelist_regex.replace("{{BLOCK_NAME}}", namelist_name.upper())
        block_regex = re.compile(
            block_regex_str.encode().decode("unicode_escape"),
            regex_utils.convert_js_flags_to_python(self.namelist_flags),
        )

        # Extract the block content
        match = block_regex.search(self.content)
        if not match:
            return {}

        block_content = match.group(0)
        result = {}

        # Parse standard key=value pairs
        for k, v in re.findall(r"(\w+)\s*=\s*([^,\n/=]+)", block_content):
            result[k.strip().lower()] = v.strip()

        # Parse Fortran array syntax (e.g., celldm(1)=10.0)
        for n, v in re.findall(r"celldm\s*\(\s*(\d+)\s*\)\s*=\s*([^,\n/]+)", block_content, re.IGNORECASE):
            result[f"celldm{n}"] = v.strip()

        return result

    @staticmethod
    def get_value_from_namelist_by_key(namelist_content: str, namelist_name: str, key: str):
        regex_object = object_utils.get(SCHEMAS, EspressoPwxStdinParser.schema_path + f"{namelist_name}/{key}")
        regex = re.compile(
            regex_object["regex"],
            regex_utils.convert_js_flags_to_python(regex_object["flags"]),
        )
        matches = list(regex.finditer(namelist_content))
        line, value = (None, None)
        if len(matches) > 0:
            line, value = matches[0].group(0), matches[0].group(1)
        return line, value

    @property
    def namelist_control(self):
        control_block_regex = re.compile(
            self.namelist_regex_control.encode().decode("unicode_escape"),
            regex_utils.convert_js_flags_to_python(self.namelist_flags),
        )
        control_blocks_match = control_block_regex.match(self.content)
        control_block = control_blocks_match[0] if control_blocks_match else None

        _ = lambda x: self.get_value_from_namelist_by_key(control_block, "control", x)[1]  # noqa

        return {
            "calculation": _("calculation"),
            "title": _("title"),
            "restart_mode": _("restart_mode"),
        }

    @property
    def namelists(self) -> dict:
        """
        Returns all standard Quantum Espresso namelists as a nested dictionary.
        Usage: self.namelists['system']['ibrav']
        """
        return {
            "control": self.get_namelist("CONTROL"),
            "system": self.get_namelist("SYSTEM"),
            "electrons": self.get_namelist("ELECTRONS"),
            "ions": self.get_namelist("IONS"),
            "cell": self.get_namelist("CELL"),
        }
