"""Configuración central del ETL."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ETL_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ETL_DIR.parent

DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_DIR / "data")))
SOURCE_XLSM = Path(
    os.getenv(
        "SOURCE_XLSM",
        str(DATA_DIR / "raw" / "SEGUIMIENTO TEMPERAS Y VINILOS Actividad.xlsm"),
    )
)
SOURCE_SHEET = os.getenv("SOURCE_SHEET", "Base De Datos")
SOURCE_HEADER_ROW = int(os.getenv("SOURCE_HEADER_ROW", "8"))  # 0-indexed
PII_SALT = os.getenv("PII_SALT", "dev-salt-change-me")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "oee_bi")),
    "user": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "oee_admin")),
    "password": os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
}

IDEAL_UNITS_PER_MINUTE = float(os.getenv("IDEAL_UNITS_PER_MINUTE", "72"))
OEE_TARGET = float(os.getenv("OEE_TARGET", "0.75"))
OEE_ALERT_THRESHOLD = float(os.getenv("OEE_ALERT_THRESHOLD", "0.60"))

# Mapa de turnos: texto libre del Excel -> código canónico.
SHIFT_MAP = {
    "6am-2pm (turno 1)": ("T1", "Turno 1 (6am-2pm)"),
    "6am-2pm": ("T1", "Turno 1 (6am-2pm)"),
    "2pm-10pm (turno 2)": ("T2", "Turno 2 (2pm-10pm)"),
    "2pm-10pm": ("T2", "Turno 2 (2pm-10pm)"),
    "10pm-6am (turno 3)": ("T3", "Turno 3 (10pm-6am)"),
    "10pm-6am": ("T3", "Turno 3 (10pm-6am)"),
    "6am-4:30pm": ("T1E", "Turno extendido (6am-4:30pm)"),
    "6am-6pm": ("T12", "Doble turno diurno (6am-6pm)"),
    "6pm-6am": ("T23", "Doble turno nocturno (6pm-6am)"),
    "no aplica": ("SD", "Sin turno / no aplica"),
    "": ("SD", "Sin turno / no aplica"),
}

SHIFT_DIM = [
    ("T1", "Turno 1 (6am-2pm)", "06:00", "14:00", 8.0, False, True),
    ("T2", "Turno 2 (2pm-10pm)", "14:00", "22:00", 8.0, False, True),
    ("T3", "Turno 3 (10pm-6am)", "22:00", "06:00", 8.0, True, True),
    ("T1E", "Turno extendido (6am-4:30pm)", "06:00", "16:30", 10.5, False, True),
    ("T12", "Doble turno diurno (6am-6pm)", "06:00", "18:00", 12.0, False, True),
    ("T23", "Doble turno nocturno (6pm-6am)", "18:00", "06:00", 12.0, True, True),
    ("SD", "Sin turno / no aplica", None, None, None, False, False),
]

MACHINE_DIM = [
    ("Vinilos_1", "Línea de envasado Vinilos 1", 1.10, True),
    ("Vinilos_2", "Línea de envasado Vinilos 2", 1.16, True),
    ("Vinilos_3", "Línea de envasado Vinilos 3", 1.00, True),
    ("Vinilos_4", "Línea de envasado Vinilos 4", 1.00, True),
]

# Códigos de paro del P-MTO-22 (1..17) + código 18 heredado del formato.
# (codigo, nombre, area_impacto, categoria, es_programado, documentado_pmto22)
CODE_DIM = [
    (1, "Falla del sistema electromecánico y/o de control", "Mantenimiento", "Mantenimiento", False, True),
    (2, "Espera de soporte de mantenimiento", "Mantenimiento", "Mantenimiento", False, True),
    (3, "Novedad en los sistemas de potencia (Aire, energía, vapor)", "Mantenimiento", "Mantenimiento", False, True),
    (4, "Mantenimiento preventivo", "Mantenimiento", "Programado", True, True),
    (5, "Ajuste operativo", "Producción", "Producción", False, True),
    (6, "Limpieza por derrame operativo", "Producción", "Producción", False, True),
    (7, "Alistamiento de máquina / Cambio de referencia", "Producción", "Producción", False, True),
    (8, "Capacitación / Reunión", "Producción", "Producción", False, True),
    (9, "Falta de operario", "Producción", "Producción", False, True),
    (10, "Paro por ventaja/evacuación", "Producción", "Producción", False, True),
    (11, "Reproceso", "Producción", "Producción", False, True),
    (12, "Materia prima defectuosa", "Calidad", "Calidad", False, True),
    (13, "En espera por el aval del laboratorio de microbiología", "Calidad", "Calidad", False, True),
    (14, "Falta de materia prima", "Almacén de materias primas", "Suministro", False, True),
    (15, "Cambio de insumos (Roscadores, O'ring, Etiquetas)", "Paro programado", "Programado", True, True),
    (16, "Alimentación y aseo de la zona de trabajo y la máquina", "Paro programado", "Programado", True, True),
    (17, "Pausa activa", "Paro programado", "Programado", True, True),
    (18, "Desinfección (código heredado, no documentado en P-MTO-22)", "Producción", "Otro", False, False),
]

# Subcódigos del catálogo. (codigo, subcodigo, nombre)
SUBCODE_CATALOG = [
    # Código 01
    (1, "1.1", "Falla mecánica"),
    (1, "1.1.A", "Banda"),
    (1, "1.1.B", "Motor"),
    (1, "1.1.C", "Sensor"),
    (1, "1.2", "Sistema de dosificación"),
    (1, "1.2.A", "Cambio de racores"),
    (1, "1.2.B", "Ajuste de sensor"),
    (1, "1.2.C", "Cambio de válvula"),
    (1, "1.2.D", "Retenedores / O'ring"),
    (1, "1.2.E", "O'ring"),
    (1, "1.3", "Sistema de banda de entrada"),
    (1, "1.3.A", "Banda"),
    (1, "1.3.B", "Motor"),
    (1, "1.4", "Sistema de tapado"),
    (1, "1.4.A", "Motor del transfer"),
    (1, "1.4.B", "Pisador de tapa"),
    (1, "1.4.C", "Sensor"),
    (1, "1.5", "Sistema de alimentación de tapa"),
    (1, "1.5.A", "Banda"),
    (1, "1.5.B", "Motor"),
    (1, "1.5.C", "Sensor"),
    (1, "1.6", "Sistema Video Jet"),
    (1, "1.6.A", "Fotocelda"),
    (1, "1.6.B", "Sensor"),
    (1, "1.7", "Sistema de sujeción y roscadores"),
    (1, "1.7.A", "Banda de sujeción"),
    (1, "1.7.B", "Roscadores"),
    (1, "1.8", "Sistema etiquetadora"),
    (1, "1.8.A", "Banda"),
    (1, "1.8.B", "Motor"),
    (1, "1.8.C", "Sensor"),
    # Código 03
    (3, "3.1", "Fallo en la subestación"),
    (3, "3.2", "Fallo en la red pública"),
    (3, "3.3", "Falla en la red neumática o el compresor"),
    (3, "3.4", "Falla en la red de enfriamiento o el chiller"),
    (3, "3.5", "Falla en la red de vapor o la caldera"),
    # Código 05
    (5, "5.1", "Sistema alimentador de envases"),
    (5, "5.2", "Sistema de dosificación de pintura, frontal posterior"),
    (5, "5.3", "Banda transportadora de entrada"),
    (5, "5.4", "Banda transportadora de salida"),
    (5, "5.5", "Transfer y pisador de tapa"),
    (5, "5.6", "Sistema alimentador de tapa y tobogán"),
    (5, "5.7", "Video Jet"),
    (5, "5.8", "Banda de sujeción y roscadores"),
    (5, "5.9", "Sistema de etiquetado"),
    (5, "5.10", "Purga de color"),
    (5, "5.11", "Lavado de boquilla"),
]

AREA_TIPO = {
    "Mantenimiento": "Mantenimiento",
    "Producción": "Producción",
    "Calidad": "Calidad",
    "Almacén de materias primas": "Suministro",
    "Paro programado": "Programado",
    "Auxiliar de piso": "Otro",
    "Personal de despachos": "Otro",
    "Personal de calidad": "Otro",
    "Supervisor": "Otro",
    "No aplica": "Otro",
}
