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

    schema_path = "/applications/espresso/5.2.1/pw.x/stdin"

    def __init__(self, content, version: str = "5.4.0"):
        """
        Constructor.

        Args:
            content (str): file content.
            version (str): file version.
        """
        super().__init__(content, version=version)

        # Store the full dictionaries on the instance
        self.stdin_schema = object_utils.get(SCHEMAS, self.schema_path) or {}
        self.partials_schema = object_utils.get(SCHEMAS, "/applications/espresso/partials") or {}

    def get_namelist(self, namelist_name: str) -> dict:
        """
        Extracts an entire namelist block and parses all key=value pairs into a dictionary.
        This handles standard keys and Fortran indexed arrays like celldm(N) or starting_magnetization(N).
        """
        # Fetch the specific block schema directly by name (e.g., "control", "system")
        namelist_schema = self.stdin_schema.get(namelist_name.lower(), {})
        format_schema = namelist_schema.get("_format")

        if not format_schema:
            return {}

        matches = list(regex_utils.regex_search_by_schema(content=self.content, schema=format_schema, find_all=True))

        if not matches:
            return {}

        # Group 0 is the full matched string of the isolated block
        block_content = matches[0].group(0)

        result = {}

        # Parse standard KVs
        for kv_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.partials_schema.get("kv_pair"), find_all=True
        ):
            k = kv_match.group(1).strip().lower()
            # Strip whitespace, then strip surrounding single/double quotes
            v = kv_match.group(2).strip().strip("'\"")
            result[k] = v

        # Parse indexed array KVs
        for array_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.partials_schema.get("kv_pair_with_index"), find_all=True
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
        return {
            "control": self.get_namelist("control"),
            "system": self.get_namelist("system"),
            "electrons": self.get_namelist("electrons"),
        }

    def get_card_cell_parameters(self, celldm1_angstrom: Optional[float] = None) -> Optional[List[List[float]]]:
        """
        Parses the CELL_PARAMETERS card and converts units to Angstrom.
        """
        match = regex_utils.regex_search_by_schema(
            content=self.content, schema=self.stdin_schema.get("cell_parameters_card")
        )

        if not match:
            return None

        # match.group(1) captures the unit (alat, bohr, or angstrom)
        units = match.group(1).lower() if match.group(1) else "alat"
        rows = []
        for row_match in regex_utils.regex_search_by_schema(
            content=match.group(2),
            schema=self.partials_schema.get("cell_parameters_row"),
            find_all=True,
        ):
            row = row_match.groupdict()
            rows.append([float(row[c]) for c in ("x", "y", "z")])

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
        match = regex_utils.regex_search_by_schema(
            content=self.content, schema=self.stdin_schema.get("atomic_positions_card")
        )
        if not match:
            return [], []

        units = match.group(1).lower() if match.group(1) else "alat"
        names, positions = [], []

        for row_match in regex_utils.regex_search_by_schema(
            content=match.group(2),
            schema=self.partials_schema.get("atomic_positions_row"),
            find_all=True,
        ):
            row = row_match.groupdict()
            symbol = row["symbol"]
            coords = [float(row[c]) for c in ("x", "y", "z")]

            if units in ["crystal", "crystal_sg"]:
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
