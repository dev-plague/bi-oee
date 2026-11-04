"""Catálogos, normalización y seudonimización."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from typing import Any

import openpyxl

from config import (
    CODE_DIM,
    IDEAL_UNITS_PER_MINUTE,
    PII_SALT,
    SHIFT_MAP,
    SUBCODE_CATALOG,
)


def strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c)
    )


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def canonical_ref(raw: Any) -> str:
    """Normaliza el nombre de referencia para que empate con el catálogo."""
    if is_blank(raw):
        return "SIN_REF"
    s = str(raw).strip()
    if strip_accents(s).lower() in {"no aplica", "no", "sin referencia", "nan"}:
        return "SIN_REF"
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\(\s*(\d+)\s*col\s*\)", r"(\1 col)", s, flags=re.IGNORECASE)
    s = re.sub(r"(\d+)\s*col\b", r"\1 col", s, flags=re.IGNORECASE)
    s = re.sub(r"(\d+)\s*cc", r"\1cc", s, flags=re.IGNORECASE)
    s = s.replace("Alocdor", "Alocolor").replace("Stilo Kids", "Estilo Kids")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def derive_reference(name: str) -> dict[str, Any]:
    """Deriva unidades/paca y unidades/display cuando no está en el catálogo."""
    if name == "SIN_REF":
        return {
            "num_colores": None,
            "unidades_por_display": None,
            "unidades_por_paca": None,
            "unidades_por_minuto_ideal": IDEAL_UNITS_PER_MINUTE,
            "origen": "ETL",
        }

    m = re.search(r"\((\d+)\s*col", name, flags=re.IGNORECASE)
    colors = int(m.group(1)) if m else None
    if colors is None and name.startswith("Vinilos x 30"):
        colors = 6
        origin_hint = "SUPUESTO"
    else:
        origin_hint = "REGLA_FORMATO"

    display: int | None = None
    if "125cc" in name:
        colors = 1
        display = 45
        origin_hint = "CATALOGO"
    elif name.startswith("Vinilos x 30"):
        display = 56
    elif colors:
        if "15cc" in name:
            display = 120 if colors == 6 else (60 if colors == 12 else 120)
        elif "22cc" in name:
            display = 100 if colors == 6 else 50
        elif "30cc" in name:
            display = 56 if colors == 6 else (28 if colors == 12 else 36)
        elif "70cc" in name:
            display = 36

    upp = colors * display if (colors and display) else None
    return {
        "num_colores": colors,
        "unidades_por_display": display,
        "unidades_por_paca": upp,
        "unidades_por_minuto_ideal": IDEAL_UNITS_PER_MINUTE,
        "origen": origin_hint if upp else "SIN_DATO",
    }


def read_reference_catalog(path) -> dict[str, dict[str, Any]]:
    """Lee la tabla de referencias de 'Tablas Desplegables' (columnas W..AB)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_vba=False)
    ws = wb["Tablas Desplegables"]
    catalog: dict[str, dict[str, Any]] = {}
    for row in ws.iter_rows(
        min_row=36, max_row=120, min_col=23, max_col=28, values_only=True
    ):
        name, colors, _pacas, display, upp, speed = row
        if is_blank(name) or is_blank(upp):
            continue
        try:
            upp_int = int(upp)
            if upp_int <= 0:
                continue
        except (TypeError, ValueError):
            continue
        key = canonical_ref(name)
        if key in catalog:
            continue
        catalog[key] = {
            "num_colores": int(colors) if not is_blank(colors) else None,
            "unidades_por_display": int(display) if not is_blank(display) else None,
            "unidades_por_paca": upp_int,
            "unidades_por_minuto_ideal": float(speed) if not is_blank(speed) else IDEAL_UNITS_PER_MINUTE,
            "origen": "CATALOGO",
        }
    wb.close()
    return catalog


def reference_info(name: str, catalog: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if name in catalog:
        return catalog[name]
    return derive_reference(name)


def normalize_shift(raw: Any) -> tuple[str, str]:
    if is_blank(raw):
        return "SD", "Sin turno / no aplica"
    key = strip_accents(str(raw)).strip().lower()
    key = re.sub(r"\s+", " ", key)
    if key in SHIFT_MAP:
        return SHIFT_MAP[key]
    return "SD", "Sin turno / no aplica"


def normalize_area(raw: Any) -> str | None:
    if is_blank(raw):
        return None
    key = strip_accents(str(raw)).strip().lower()
    key = re.sub(r"\s+", " ", key)
    mapping = {
        "personal_de_mantenimiento": "Mantenimiento",
        "personal de mantenimiento": "Mantenimiento",
        "mantenimiento": "Mantenimiento",
        "operarios": "Producción",
        "operario": "Producción",
        "produccion": "Producción",
        "auxiliar de piso": "Auxiliar de piso",
        "personal de despachos": "Personal de despachos",
        "personal de calidad": "Personal de calidad",
        "supervisor": "Supervisor",
        "no aplica": None,
    }
    if key in mapping:
        return mapping[key]
    return str(raw).strip().title()


def normalize_subcode(raw: Any, codigo: int) -> str:
    """Normaliza un subcódigo a la forma canónica x.y o x.y.z."""
    if codigo not in (1, 3, 5) or is_blank(raw):
        return "SIN_ESP"
    s = strip_accents(str(raw)).strip().upper()
    s = re.sub(r"\s+", " ", s)
    if s in {"SIN ESPECIFICAR", "NO APLICA", "NAN", "N/A", "NO"}:
        return "SIN_ESP"

    # El catálogo tiene un typo: 1.4.3 Sensor -> 1.4.C Sensor.
    if re.match(r"^1\.4\.3\b", s):
        return "1.4.C"

    # Subcódigos heredados 4.x que en el formato nuevo son 5.x.
    if s.startswith("4."):
        return map_old_subcode(s) or "SIN_ESP"

    # La letra solo cuenta si está pegada al número (1.2D) o tras un punto
    # (1.2.D); no debe tomar la inicial de la palabra siguiente (1.1 SISTEMA).
    m = re.match(r"^(\d)\.(\d+)(?:\.?([A-Z]))?(?=\s|$|[.)])", s)
    if not m:
        return "SIN_ESP"
    code, num, letter = m.groups()
    base = f"{code}.{num}"
    return f"{base}.{letter}" if letter else base


def map_old_subcode(text: str) -> str | None:
    """Mapea los subcódigos 4.x (numeración vieja) a 5.x (numeración nueva)."""
    t = strip_accents(text).upper()
    rules = [
        ("ALIMENTACION", "5.1"),
        ("ENVASE", "5.1"),
        ("DOSIFICADOR", "5.2"),
        ("DOSIFICACION", "5.2"),
        ("BANDA", "5.3"),
        ("TRANSPORTADORA", "5.3"),
        ("TRANSFER", "5.5"),
        ("PISADOR", "5.5"),
        ("ALIMENTADOR", "5.6"),
        ("TOBOGAN", "5.6"),
        ("VIDEO", "5.7"),
        ("SUJECION", "5.8"),
        ("ROSCADOR", "5.8"),
        ("ETIQUET", "5.9"),
        ("PURGA", "5.10"),
        ("LAVADO", "5.11"),
    ]
    for token, target in rules:
        if token in t:
            # "BANDA DE SUJECION" debe ir a 5.8, no a 5.3
            if token == "BANDA" and "SUJECION" in t:
                return "5.8"
            return target
    return None


def subcode_catalog_map() -> dict[tuple[int, str], str]:
    return {(c, s): n for c, s, n in SUBCODE_CATALOG}


def subcode_display_name(codigo: int, subcodigo: str, raw: Any) -> str:
    catalog = subcode_catalog_map()
    if (codigo, subcodigo) in catalog:
        return catalog[(codigo, subcodigo)]
    if subcodigo == "SIN_ESP":
        return "Sin especificar"
    text = "" if is_blank(raw) else str(raw).strip()
    text = re.sub(r"^\d+(\.\d+)*\.?\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" .-")
    if not text:
        return f"Subcódigo {subcodigo}"
    return text[:1].upper() + text[1:].lower()


def code_dim_map() -> dict[int, dict[str, Any]]:
    return {
        c: {
            "codigo": c,
            "nombre": n,
            "area_impacto": a,
            "categoria": cat,
            "es_programado": prog,
            "documentado_pmto22": doc,
        }
        for c, n, a, cat, prog, doc in CODE_DIM
    }


def pseudonym(raw: Any, prefix: str, salt: str = PII_SALT) -> tuple[str | None, str | None]:
    """Devuelve (seudónimo, hash). No conserva el nombre original."""
    if is_blank(raw):
        return None, None
    name = re.sub(r"\s+", " ", str(raw).strip()).lower()
    if strip_accents(name) in {"no aplica", "no", "nan", "sin nombre"}:
        return None, None
    digest = hashlib.sha256(f"{salt}|{name}".encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:8].upper()}", digest


def stable_hash(*parts: Any) -> str:
    payload = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
