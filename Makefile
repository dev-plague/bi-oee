SHELL := /bin/bash

.PHONY: help env up down reset etl sim sim-stop logs psql adminer test dashboard

help:
	@echo "Targets disponibles:"
	@echo "  make env       Copia .env.example a .env si no existe"
	@echo "  make up        Levanta PostgreSQL y Grafana"
	@echo "  make etl       Ejecuta el ETL completo (contenedor)"
	@echo "  make sim       Levanta el simulador near real-time + receptor de alertas"
	@echo "  make sim-stop  Detiene el simulador"
	@echo "  make reset     Baja todo y borra volúmenes (reconstrucción desde cero)"
	@echo "  make psql      Abre psql como oee_admin"
	@echo "  make adminer   Levanta Adminer en http://localhost:8081"
	@echo "  make test      Ejecuta pruebas unitarias del ETL"
	@echo "  make dashboard Regenera el JSON del tablero de Grafana"

env:
	@test -f .env || cp .env.example .env
	@echo "Archivo .env listo. Revisar y cambiar credenciales."

up: env
	docker compose up -d postgres grafana
	@echo "Grafana: http://localhost:$${GRAFANA_PORT:-3000}"

down:
	docker compose down

reset:
	docker compose --profile sim --profile tools down -v

etl:
	docker compose run --rm etl

sim:
	docker compose --profile sim up -d --build simulator
	@echo "Simulador y webhook de alertas en http://localhost:8080/alerts"

sim-stop:
	docker compose --profile sim stop simulator

logs:
	docker compose logs -f --tail=200

psql:
	docker compose exec postgres psql -U $${POSTGRES_USER:-oee_admin} -d $${POSTGRES_DB:-oee_bi}

adminer:
	docker compose --profile tools up -d adminer
	@echo "Adminer: http://localhost:8081 (servidor: postgres, usuario: oee_admin)"

test:
	docker compose run --rm --entrypoint pytest etl -q

dashboard:
	python3 scripts/build_grafana_dashboard.py
