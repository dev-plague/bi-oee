#!/bin/bash
# ============================================================
# Crea los roles de mínimo privilegio. Se ejecuta una sola vez,
# cuando el volumen de PostgreSQL está vacío.
# ============================================================
set -euo pipefail

: "${OEE_ETL_PASSWORD:?Falta OEE_ETL_PASSWORD}"
: "${OEE_BI_PASSWORD:?Falta OEE_BI_PASSWORD}"
: "${OEE_GRAFANA_PASSWORD:?Falta OEE_GRAFANA_PASSWORD}"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     -v etl_pw="$OEE_ETL_PASSWORD" \
     -v bi_pw="$OEE_BI_PASSWORD" \
     -v grafana_pw="$OEE_GRAFANA_PASSWORD" <<'EOSQL'
SELECT format('CREATE ROLE oee_etl LOGIN PASSWORD %L', :'etl_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oee_etl')\gexec

SELECT format('CREATE ROLE oee_bi LOGIN PASSWORD %L', :'bi_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oee_bi')\gexec

SELECT format('CREATE ROLE oee_grafana LOGIN PASSWORD %L', :'grafana_pw')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'oee_grafana')\gexec
EOSQL
