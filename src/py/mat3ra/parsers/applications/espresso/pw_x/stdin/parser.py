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

    schema_path = "/applications/espresso/"

    def __init__(self, content, version: str = "5.4.0"):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): file version.
        """
        super().__init__(content, version=version)
        self.namelist_block_content_regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + "_regex_dict/namelist_block"
        )
        self.kv_pair_regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + "_regex_dict/kv_pair"
        )
        self.kv_pair_with_index_regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + "_regex_dict/kv_pair_with_index"
        )
        self.cell_parameters_card_regex_object = object_utils.get(
            SCHEMAS, EspressoPwxStdinParser.schema_path + "_regex_dict/cell_parameters_card"
        )

    def get_namelist(self, namelist_name: str) -> dict:
        """
        Extracts an entire namelist block and parses all key=value pairs into a dictionary.
        This handles standard keys and Fortran indexed arrays like celldm(N) or starting_magnetization(N).
        """
        matches = regex_utils.regex_search_by_schema(
            content=self.content,
            schema=self.namelist_block_content_regex_object,
            find_all=True
        )

        block_content = None
        for match in matches:
            # Group 1 captures the block name (e.g., "CONTROL" or "SYSTEM") from the build-time OR-group
            if match.group(1).upper() == namelist_name.upper():
                block_content = match.group(2) # Group 2 contains the body content
                break

        if not block_content:
            return {}

        result = {}

        # Parse standard KVs
        for kv_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.kv_pair_regex_object, find_all=True
        ):
            k = kv_match.group(1).strip().lower()
            # Strip whitespace, then strip surrounding single/double quotes
            v = kv_match.group(2).strip().strip("'\"")
            result[k] = v

        # Parse indexed array KVs
        for array_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.kv_pair_with_index_regex_object, find_all=True
        ):
            key = array_match.group(1).strip().lower()
            index = array_match.group(2).strip()
            # Strip whitespace, then strip surrounding single/double quotes
            value = array_match.group(3).strip().strip("'\"")
            result[f"{key}{index}"] = value

        return result

    @property
    def namelists(self) -> dict:
        """
        Returns all standard Quantum Espresso namelists as a nested dictionary.
        Usage: self.namelists['system']['ibrav']
        """
        result = {
            "control": self.get_namelist("CONTROL"),
            "system": self.get_namelist("SYSTEM"),
            "electrons": self.get_namelist("ELECTRONS"),
        }

        # Add optional namelists only if they are found and have content
        ions = self.get_namelist("IONS")
        if ions:
            result["ions"] = ions

        cell = self.get_namelist("CELL")
        if cell:
            result["cell"] = cell

        fcp = self.get_namelist("FCP")
        if fcp:
            result["fcp"] = fcp

        rism = self.get_namelist("RISM")
        if rism:
            result["rism"] = rism

        return result

    def get_card_cell_parameters(self, celldm1_angstrom: Optional[float] = None) -> Optional[List[List[float]]]:
        """
        Parses the CELL_PARAMETERS card and converts units to Angstrom.
        """
        match = regex_utils.regex_search_by_schema(
            content=self.content, schema=self.cell_parameters_card_regex_object
        )

        if not match:
            return None

        # match.group(1) safely captures the unit (alat, bohr, or angstrom) due to the build-time replacement
        units = match.group(1).lower() if match.group(1) else "alat"
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
            return [], []

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
