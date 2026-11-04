import sys
from pathlib import Path

# Permite importar los módulos del ETL (catalogs, clean, transform, ...)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
