import re
from typing import List, Optional, Tuple

from mat3ra.parsers import BaseParser
from mat3ra.regex.data.schemas import SCHEMAS
from mat3ra.utils import object as object_utils
from mat3ra.utils import regex as regex_utils
from mat3ra.utils.constants import COEFFICIENTS


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
        # Extract the block content using a robust boundary regex
        # This safely captures everything between &NAME and / regardless of the keys inside
        match = re.search(rf"&{namelist_name}\s*([\s\S]*?)\/", self.content, re.IGNORECASE)

        if not match:
            return {}

        # group(1) contains the internal block text, excluding the &NAME and /
        block_content = match.group(1)
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

    def get_card_cell_parameters(self, celldm1_angstrom: Optional[float] = None) -> Optional[List[List[float]]]:
        """
        Parses the CELL_PARAMETERS card and converts units to Angstrom.
        """
        match = re.search(
            r"CELL_PARAMETERS\s*[{(]?\s*(\w+)\s*[)}]?\s*\n"
            r"((?:[ \t]*[-\d.eEdD+]+[ \t]+[-\d.eEdD+]+[ \t]+[-\d.eEdD+]+[ \t]*\n?){3})",
            self.content,
            re.IGNORECASE,
        )
        if not match:
            return None  # Return None if card is missing (e.g., ibrav != 0)

        units = match.group(1).lower()
        rows = [list(map(float, line.split())) for line in match.group(2).strip().splitlines()]

        if units == "bohr":
            rows = [[v * COEFFICIENTS["BOHR_TO_ANGSTROM"] for v in row] for row in rows]
        elif units == "alat":
            if not celldm1_angstrom:
                raise ValueError("alat units require celldm(1)")
            rows = [[v * celldm1_angstrom for v in row] for row in rows]

        return rows

    def get_card_atomic_positions(
        self, cell: List[List[float]], celldm1_angstrom: Optional[float] = None
    ) -> Tuple[List[str], List[List[float]]]:
        """
        Parses the ATOMIC_POSITIONS card and converts coordinates to Cartesian Angstroms.
        """
        match = re.search(
            r"ATOMIC_POSITIONS\s*[{(]?\s*(\w+)\s*[)}]?\s*\n"
            r"((?:[ \t]*\w+[ \t]+[-\d.eEdD+]+[ \t]+[-\d.eEdD+]+[ \t]+[-\d.eEdD+]+.*\n?)+)",
            self.content,
            re.IGNORECASE,
        )
        if not match:
            return [], []  # Or raise an error, depending on strictness

        units = match.group(1).lower()
        names, positions = [], []

        for line in match.group(2).strip().splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            symbol = parts[0]
            coords = list(map(float, parts[1:4]))

            if units == "crystal":
                if not cell:
                    raise ValueError("crystal units require a parsed cell to convert to Cartesian")
                coords = [sum(coords[i] * cell[i][j] for i in range(3)) for j in range(3)]
            elif units == "bohr":
                coords = [v * COEFFICIENTS["BOHR_TO_ANGSTROM"] for v in coords]
            elif units == "alat":
                if not celldm1_angstrom:
                    raise ValueError("alat units require celldm(1)")
                coords = [v * celldm1_angstrom for v in coords]

            names.append(symbol)
            positions.append(coords)

        return names, positions
