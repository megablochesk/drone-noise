from dataclasses import dataclass
from typing import Dict, Tuple, List

import pandas as pd


@dataclass(frozen=True)
class CachedMSOA:
    polygons: Dict[str, object]
    bounds: Dict[str, Tuple[float, float, float, float]]
    areas: Dict[str, float]
    counts: Dict[str, Dict[int, float]]
    codes: List[int]


def prepare_msoa_caches(pivot: pd.DataFrame, msoa_index: Dict[str, object]) -> CachedMSOA:
    valid = pivot.index.intersection(pd.Index(msoa_index.keys()))
    pivot_f = pivot.loc[valid]
    polygons = {c: msoa_index[c] for c in valid}
    return CachedMSOA(
        polygons=polygons,
        bounds={c: p.bounds for c, p in polygons.items()},
        areas={c: p.area for c, p in polygons.items()},
        counts=pivot_f.to_dict(orient="index"),
        codes=[int(c) for c in pivot_f.columns],
    )
