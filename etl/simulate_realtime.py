"""Simulador near real-time + receptor local de alertas de Grafana.

Cada tick inserta una fila por máquina en oee.fact_produccion_hora
(1 minuto simulado). Permite inyectar anomalías para demostrar que el
tablero y la regla de alerta reaccionan.
"""
from __future__ import annotations

import argparse
import json
import random
import threading
import time
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2
from psycopg2.extras import Json

from config import DB_CONFIG


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def load_context(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT maquina_key, codigo
            FROM oee.dim_maquina
            WHERE activa
            ORDER BY maquina_key
            """
        )
        machines = cur.fetchall()
        if not machines:
            raise RuntimeError("No hay máquinas en dim_maquina. Ejecutar el ETL primero.")
        cur.execute("SELECT turno_key FROM oee.dim_turno WHERE codigo = 'T1'")
        turno = cur.fetchone()[0]
        refs = {}
        preferred = {
            "Vinilos_1": "Pintorcitos 22cc (6 col)",
            "Vinilos_2": "Parchesitos 125cc",
            "Vinilos_3": "Parchesitos 22cc (6 col)",
            "Vinilos_4": "Mis pasitos 22cc (6 col)",
        }
        for key, code in machines:
            name = preferred.get(code)
            cur.execute(
                """
                SELECT referencia_key, unidades_por_paca
                FROM oee.dim_referencia
                WHERE unidades_por_paca IS NOT NULL
                  AND (%s IS NULL OR referencia_natural = %s)
                ORDER BY referencia_key
                LIMIT 1
                """,
                (name, name),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """
                    SELECT referencia_key, unidades_por_paca
                    FROM oee.dim_referencia
                    WHERE unidades_por_paca IS NOT NULL
                    ORDER BY referencia_key
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
            refs[key] = row
    return machines, turno, refs


def reset_simulation(conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM oee.fact_produccion_hora WHERE origen = 'SIMULACION'")
        cur.execute(
            "DELETE FROM audit.alertas_recibidas WHERE recibido_en < now() - interval '7 days'"
        )
    conn.commit()


def insert_tick(conn, machines, turno, refs, state, anomaly_prob, force_anomaly, anomaly_machine):
    now = datetime.now(timezone.utc)
    tiempo_key = int(now.strftime("%Y%m%d"))
    rows = []
    for key, code in machines:
        # Estado por máquina: normal o degradado durante varios ticks.
        st = state.get(key, {"modo": "normal", "ticks": 0})
        if st["ticks"] <= 0:
            if (force_anomaly and (anomaly_machine in (None, code))) or random.random() < anomaly_prob:
                st = {"modo": random.choice(["degradado", "paro"]), "ticks": random.randint(40, 80)}
            else:
                st = {"modo": "normal", "ticks": random.randint(20, 40)}
        st["ticks"] -= 1
        state[key] = st

        ref_key, upp = refs[key]
        planned = 1.0
        if st["modo"] == "paro":
            paro = round(random.uniform(0.55, 0.85), 2)
            perf = random.uniform(0.10, 0.35)
        elif st["modo"] == "degradado":
            paro = round(random.uniform(0.30, 0.55), 2)
            perf = random.uniform(0.35, 0.60)
        else:
            paro = round(random.uniform(0.0, 0.10), 2)
            perf = random.uniform(0.78, 0.98)

        operating = max(planned - paro, 0.0)
        units = operating * 72.0 * perf
        pacas = units / upp if upp else 0.0
        rows.append(
            (
                now,
                tiempo_key,
                key,
                turno,
                ref_key,
                round(pacas, 2),
                round(units, 2),
                planned,
                round(operating, 2),
                paro,
                "SIMULACION",
            )
        )
        print(
            f"[SIM] {now:%H:%M:%S} {code:9s} modo={st['modo']:9s} "
            f"paro={paro:.2f} min op={operating:.2f} und={units:.2f} "
            f"OEE≈{units / (planned * 72):.1%}"
        )

    with conn.cursor() as cur:
        for row in rows:
            cur.execute(
                """
                INSERT INTO oee.fact_produccion_hora
                    (ts_hora, tiempo_key, maquina_key, turno_key, referencia_key,
                     pacas_producidas, unidades_producidas, minutos_planificados,
                     minutos_operacion, minutos_paro, origen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ts_hora, maquina_key) DO UPDATE
                   SET unidades_producidas = EXCLUDED.unidades_producidas,
                       pacas_producidas = EXCLUDED.pacas_producidas,
                       minutos_operacion = EXCLUDED.minutos_operacion,
                       minutos_paro = EXCLUDED.minutos_paro
                """,
                row,
            )
    conn.commit()


class AlertHandler(BaseHTTPRequestHandler):
    conn = None

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") not in ("/alerts", "/api/alerts"):
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body}

        alerts = payload.get("alerts", []) if isinstance(payload, dict) else []
        if not alerts:
            alerts = [payload]
        with self.conn.cursor() as cur:
            for alert in alerts:
                labels = alert.get("labels", {}) if isinstance(alert, dict) else {}
                value = alert.get("value", None) if isinstance(alert, dict) else None
                try:
                    value_num = float(str(value).split()[0]) if value not in (None, "") else None
                except (TypeError, ValueError):
                    value_num = None
                cur.execute(
                    """
                    INSERT INTO audit.alertas_recibidas
                        (estado, regla, maquina, valor, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        alert.get("status") or payload.get("status"),
                        labels.get("alertname") or labels.get("rulename"),
                        labels.get("maquina"),
                        value_num,
                        Json(payload),
                    ),
                )
        self.conn.commit()
        print(f"[ALERT-SINK] {len(alerts)} alerta(s) recibida(s): {payload.get('status')}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, fmt, *args):  # silenciar log HTTP
        return


def serve_alerts(port: int, conn):
    AlertHandler.conn = conn
    server = ThreadingHTTPServer(("0.0.0.0", port), AlertHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[ALERT-SINK] escuchando en http://0.0.0.0:{port}/alerts")
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulador OEE near real-time")
    parser.add_argument("--interval", type=float, default=2.0, help="segundos entre ticks")
    parser.add_argument("--anomaly-prob", type=float, default=0.05, help="probabilidad de anomalía")
    parser.add_argument("--force-anomaly", action="store_true", help="forzar anomalía")
    parser.add_argument("--anomaly-machine", default=None, help="máquina a forzar (Vinilos_2)")
    parser.add_argument("--serve-alerts", action="store_true", help="servir webhook de Grafana")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--duration", type=int, default=0, help="segundos; 0 = infinito")
    parser.add_argument("--reset", action="store_true", help="borrar simulación previa")
    args = parser.parse_args()

    conn = get_conn()
    if args.reset:
        reset_simulation(conn)
    machines, turno, refs = load_context(conn)
    print(f"[SIM] máquinas={[m[1] for m in machines]} turno={turno}")
    print(f"[SIM] referencias={ {m[1]: r for m, r in zip(machines, refs.values())} }")

    if args.serve_alerts:
        serve_alerts(args.port, conn)

    state: dict = {}
    start = time.time()
    try:
        while True:
            insert_tick(
                conn,
                machines,
                turno,
                refs,
                state,
                args.anomaly_prob,
                args.force_anomaly,
                args.anomaly_machine,
            )
            if args.duration and (time.time() - start) >= args.duration:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[SIM] detenido")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
