import math
from collections import Counter
from functools import reduce
from typing import List, Tuple

import numpy as np

from mat3ra.esse.models.properties_directory.structural.lattice import LatticeSchema
from mat3ra.made.cell.primitive_cell import get_primitive_lattice_vectors_from_config
from mat3ra.utils.constants import COEFFICIENTS

from .parser import EspressoPwxStdinParser

# Maps QE ibrav codes → made/esse Bravais type strings
# fmt: off
IBRAV_TO_LATTICE_TYPE = {
    1:  "CUB",
    2:  "FCC",
    3:  "BCC",  -3: "BCC",
    4:  "HEX",
    5:  "RHL",  -5: "RHL",
    6:  "TET",
    7:  "BCT",
    8:  "ORC",
    9:  "ORCC", -9: "ORCC",
    10: "ORCF",
    11: "ORCI",
    12: "MCL",  -12: "MCL",
    13: "MCLC",
    14: "TRI",
}
# fmt: on


class EspressoPwxStdinMaterial(EspressoPwxStdinParser):
    """
    Translates Espresso PWX stdin syntax intermediate configs into MADE material domain configs.
    """

    def _round(self, values, precision=6):
        if isinstance(values, list):
            return [round(v, precision) for v in values]
        return round(values, precision)

    def _get_cell_from_ibrav(
        self, system: dict
    ) -> Tuple[str, float, float, float, float, float, float, List[List[float]]]:
        """
        Parses system parameters and uses `made` to calculate the 3x3 primitive matrix.
        """
        ibrav = int(system.get("ibrav", 0))
        lattice_type = IBRAV_TO_LATTICE_TYPE.get(ibrav)
        if lattice_type is None:
            raise ValueError(f"Unsupported ibrav={ibrav}")

        has_celldm = "celldm1" in system

        if has_celldm:
            a = float(system["celldm1"]) * COEFFICIENTS["BOHR_TO_ANGSTROM"]
            b = a * float(system.get("celldm2", 1))
            c = a * float(system.get("celldm3", 1))
            alpha = math.degrees(math.acos(float(system.get("celldm4", 0))))
            beta = math.degrees(math.acos(float(system.get("celldm5", 0))))
            gamma = math.degrees(math.acos(float(system.get("celldm6", 0))))
        else:
            a = float(system.get("a", 1))
            b = float(system.get("b", a))
            c = float(system.get("c", a))
            alpha = (
                math.degrees(math.acos(float(system["cosbc"])))
                if "cosbc" in system
                else float(system.get("alpha", 90))
            )
            beta = (
                math.degrees(math.acos(float(system["cosac"]))) if "cosac" in system else float(system.get("beta", 90))
            )
            gamma = (
                math.degrees(math.acos(float(system["cosab"])))
                if "cosab" in system
                else float(system.get("gamma", 90))
            )

        # Leverage the exact schema and primitive generator from `made`
        lattice_config = LatticeSchema(type=lattice_type, a=a, b=b, c=c, alpha=alpha, beta=beta, gamma=gamma)
        vectors = get_primitive_lattice_vectors_from_config(lattice_config)

        return lattice_type, a, b, c, alpha, beta, gamma, vectors

    def _get_lattice_params_from_matrix(
        self, matrix: List[List[float]]
    ) -> Tuple[float, float, float, float, float, float]:
        """
        Extracts a, b, c, alpha, beta, gamma from a 3x3 Cartesian matrix when explicitly defined.
        """
        v1, v2, v3 = np.array(matrix[0]), np.array(matrix[1]), np.array(matrix[2])
        a = np.linalg.norm(v1)
        b = np.linalg.norm(v2)
        c = np.linalg.norm(v3)
        # Clip to [-1.0, 1.0] to prevent floating-point errors in arccos
        alpha = np.degrees(np.arccos(np.clip(np.dot(v2, v3) / (b * c), -1.0, 1.0)))
        beta = np.degrees(np.arccos(np.clip(np.dot(v1, v3) / (a * c), -1.0, 1.0)))
        gamma = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / (a * b), -1.0, 1.0)))
        return a, b, c, alpha, beta, gamma

    @property
    def lattice(self) -> dict:
        system = self.get_namelist("system")
        ibrav = int(system.get("ibrav", 0))

        if ibrav == 0:
            cell_card = self.get_card_cell_parameters()
            if not cell_card:
                raise ValueError("ibrav is 0 but CELL_PARAMETERS card is missing.")

            matrix = [cell_card["values"]["v1"], cell_card["values"]["v2"], cell_card["values"]["v3"]]
            units = cell_card.get("card_option", "alat").lower()

            # Apply alat scale if the vectors are strictly in Bohr units
            if units == "alat" and self.celldm1_angstrom:
                matrix = [[val * self.celldm1_angstrom for val in row] for row in matrix]

            lattice_type = "TRI"  # Defaulting to Triclinic when explicitly defined (without symmetry engine)
            a, b, c, alpha, beta, gamma = self._get_lattice_params_from_matrix(matrix)
            vectors = matrix
        else:
            lattice_type, a, b, c, alpha, beta, gamma, vectors = self._get_cell_from_ibrav(system)

        return {
            "type": lattice_type,
            "a": self._round(float(a), 6),
            "b": self._round(float(b), 6),
            "c": self._round(float(c), 6),
            "alpha": self._round(float(alpha), 4),
            "beta": self._round(float(beta), 4),
            "gamma": self._round(float(gamma), 4),
            "units": {"length": "angstrom", "angle": "degree"},
            "vectors": {
                "a": self._round(vectors[0], 6),
                "b": self._round(vectors[1], 6),
                "c": self._round(vectors[2], 6),
                "alat": 1.0,
            },
        }

    @property
    def basis(self) -> dict:
        atomic_positions = self.get_card_atomic_positions()
        if not atomic_positions:
            return {}

        elements = []
        coordinates = []
        card_option = atomic_positions.get("card_option", "crystal").lower()

        for i, site in enumerate(atomic_positions["values"]):
            elements.append({"id": i, "value": site["X"]})
            coords = [site["x"], site["y"], site["z"]]

            # Apply alat scale if coordinates are given in alat
            if card_option == "alat" and self.celldm1_angstrom:
                coords = [c * self.celldm1_angstrom for c in coords]
                units = "cartesian"
            elif card_option == "angstrom":
                units = "cartesian"
            else:
                units = "crystal"

            coordinates.append({"id": i, "value": self._round(coords, 6)})

        return {"units": units, "elements": elements, "coordinates": coordinates}

    @property
    def formula(self) -> str:
        """
        Creates a raw standard formula (e.g. Si4O8)
        """
        atomic_positions = self.get_card_atomic_positions()
        if not atomic_positions:
            return ""

        species = [site["X"] for site in atomic_positions["values"]]
        counts = Counter(species)
        return "".join([f"{el}{cnt}" if cnt > 1 else el for el, cnt in counts.items()])

    @property
    def name(self) -> str:
        """
        Creates a reduced formula acting as the material name (e.g. SiO2)
        """
        atomic_positions = self.get_card_atomic_positions()
        if not atomic_positions:
            return ""

        species = [site["X"] for site in atomic_positions["values"]]
        counts = Counter(species)

        if not counts:
            return ""

        # Greatest Common Divisor to reduce the formula
        divisor = reduce(math.gcd, counts.values())
        return "".join([f"{el}{count//divisor}" if count // divisor > 1 else el for el, count in counts.items()])
