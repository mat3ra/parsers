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
            version (str): Quantum ESPRESSO version.
        """
        super().__init__(content, version=version)
        self.stdin_schema = object_utils.get(SCHEMAS, self.schema_path) or {}
        self.partials_schema = object_utils.get(SCHEMAS, "/applications/espresso/partials") or {}

    def get_namelist(self, namelist_name: str) -> dict:
        """
        Extracts an entire namelist block and parses all key=value pairs into a dictionary.
        This handles standard keys and Fortran indexed arrays like celldm(N) or starting_magnetization(N).
        """
        namelist_schema = self.stdin_schema.get(namelist_name.lower(), {}).get("_format")

        matches = list(regex_utils.regex_search_by_schema(content=self.content, schema=namelist_schema, find_all=True))

        if not matches:
            return {}

        block_content = matches[0].group(0)
        result = {}

        for kv_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.partials_schema.get("kv_pair"), find_all=True
        ):
            k = kv_match.group(1).strip().lower()
            v = kv_match.group(2).strip().strip("'\"")
            result[k] = v

        for array_match in regex_utils.regex_search_by_schema(
            content=block_content, schema=self.partials_schema.get("kv_pair_with_index"), find_all=True
        ):
            key = array_match.group(1).strip().lower()
            index = array_match.group(2).strip()
            value = array_match.group(3).strip().strip("'\"")
            result[f"{key}{index}"] = value

        return result

    @property
    def celldm1_angstrom(self) -> Optional[float]:
        """
        Helper property to extract celldm(1) from the SYSTEM namelist and convert it to Angstroms.
        """
        system_nl = self.get_namelist("system")
        celldm1_bohr = system_nl.get("celldm1")
        return float(celldm1_bohr) * COEFFICIENTS["BOHR_TO_ANGSTROM"] if celldm1_bohr else None

    def get_card_cell_parameters(self) -> Optional[List[List[float]]]:
        """
        Parses the CELL_PARAMETERS card and converts coordinates to Cartesian Angstroms.
        """
        match = regex_utils.regex_search_by_schema(
            content=self.content, schema=self.stdin_schema.get("cell_parameters_card")
        )

        if not match:
            return None

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
            alat = self.celldm1_angstrom
            if not alat:
                raise ValueError("alat units require celldm(1)")
            rows = [[v * alat for v in row] for row in rows]

        return rows

    def get_card_atomic_positions(self, cell: List[List[float]]) -> Tuple[List[str], List[List[float]]]:
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
                alat = self.celldm1_angstrom
                if not alat:
                    raise ValueError("alat units require celldm(1)")
                coords = [v * alat for v in coords]

            names.append(symbol)
            positions.append(coords)

        return names, positions

    @property
    def parsed_content(self) -> dict:
        """
        Returns the entire parsed input file as a flat dictionary containing both namelists and cards.
        Aligns directly with the ESSE pw.x.json schema.
        """
        result = {
            "control": self.get_namelist("control"),
            "system": self.get_namelist("system"),
            "electrons": self.get_namelist("electrons"),
        }

        cell_params = self.get_card_cell_parameters()
        if cell_params:
            result["cell_parameters"] = cell_params

        names, positions = self.get_card_atomic_positions(cell_params or [])
        if names:
            result["atomic_positions"] = {"names": names, "positions": positions}

        return result
