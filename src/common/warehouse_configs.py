from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from common.coordinate import Coordinate


@dataclass(frozen=True)
class Warehouses:
    bng_coordinates: Dict[str, Coordinate]
    latlon_coordinates: Dict[str, Tuple[float, float]]

    @staticmethod
    def london_default() -> "Warehouses":
        return Warehouses(
            bng_coordinates={
                "DBR1": Coordinate(180193.93, 550041.28),
                "DBR2": Coordinate(167766.96, 546937.62),
                "DCR1": Coordinate(164142.21, 530990.34),
                "DCR2": Coordinate(165727.01, 530631.31),
                "DCR3": Coordinate(165418.73, 530850.99),
                "DHA1": Coordinate(185648.81, 520386.09),
                "DHA2": Coordinate(185658.7, 520531.03),
                "DIG1": Coordinate(196826.63, 536790.04),
                "DRM4": Coordinate(182781.49, 546601.21),
                "DXE1": Coordinate(182049.78, 538402.03),
                "DXN1": Coordinate(179513.55, 507871.84),
                "EHU2": Coordinate(182097.0, 538419.42),
                "MLN2": Coordinate(182084.59, 533269.42),
                "MLN3": Coordinate(179908.41, 533781.95),
            },
            latlon_coordinates={
                "DBR1": (51.500773, 0.160277),
                "DBR2": (51.389926, 0.110440),
                "DCR1": (51.361253, -0.119953),
                "DCR2": (51.375578, -0.124525),
                "DCR3": (51.372757, -0.121484),
                "DHA1": (51.556886, -0.264871),
                "DHA2": (51.556944, -0.262778),
                "DIG1": (51.653594, -0.024036),
                "DRM4": (51.524925, 0.111827),
                "DXE1": (51.520417, -0.006570),
                "DXN1": (51.504271, -0.447186),
                "EHU2": (51.520837, -0.006301),
                "MLN2": (51.521963, -0.080489),
                "MLN3": (51.502286, -0.073931),
            },
        )
