"""Extracción de la fuente Excel (.xlsm)."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from catalogs import read_reference_catalog
from config import SOURCE_HEADER_ROW, SOURCE_SHEET


def extract_source(path: Path, sheet: str = SOURCE_SHEET, header: int = SOURCE_HEADER_ROW) -> pd.DataFrame:
    """Lee la hoja 'Base De Datos' sin ejecutar macros."""
    if not Path(path).exists():
        raise FileNotFoundError(
            f"No se encontró el archivo fuente: {path}. "
            "Copiarlo a data/raw/ o ajustar SOURCE_XLSM."
        )
    df = pd.read_excel(path, sheet_name=sheet, header=header, engine="openpyxl")
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    # Fila Excel 1-indexada: header (0-indexed) + 2 = primera fila de datos.
    df.insert(0, "origen_fila", range(header + 2, header + 2 + len(df)))
    return df


def extract_catalog(path: Path) -> dict[str, dict]:
    return read_reference_catalog(path)
