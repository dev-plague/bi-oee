"""Orquestador del ETL: extract -> clean -> transform -> load -> audit."""
from __future__ import annotations

import sys
import traceback
import uuid

from clean import clean_source
from config import SOURCE_SHEET, SOURCE_XLSM
from extract import extract_catalog, extract_source
import load
import quality
import reconcile
from transform import build_dimensions, build_facts, build_staging


def _print_summary(stats: dict, recon: list[dict], checks: list[dict]) -> None:
    print("\n" + "=" * 68)
    print("RESUMEN ETL")
    print("=" * 68)
    for key in (
        "filas_leidas",
        "duplicados_exactos",
        "filas_tras_dedup",
        "registros_produccion",
        "eventos_paro",
        "pacas_produccion",
        "horas_produccion",
        "paro_h_total",
        "produccion_sin_referencia",
        "outliers",
        "incompletos",
    ):
        if key in stats:
            print(f"  {key:28s}: {stats[key]}")
    print("-" * 68)
    print("  CONCILIACIÓN")
    for r in recon:
        flag = "OK " if r["concilia"] else "DIF"
        print(
            f"  [{flag}] {r['metrica']:28s} fuente={r['valor_fuente']:>14,.2f} "
            f"cargado={r['valor_cargado']:>14,.2f} dif={r['diferencia']:>10,.2f}"
        )
    print("-" * 68)
    warn = sum(1 for c in checks if c["severidad"] == "WARN")
    err = sum(1 for c in checks if c["severidad"] == "ERROR")
    print(f"  Calidad: {len(checks)} reglas, {warn} WARN, {err} ERROR")
    for c in checks:
        if c["severidad"] in ("WARN", "ERROR"):
            print(f"   - {c['severidad']:5s} {c['regla']}: {c['filas_afectadas']} ({c['detalle']})")
    print("=" * 68 + "\n")


def main() -> int:
    run_id = str(uuid.uuid4())
    print(f"[ETL] Inicio run_id={run_id}")
    print(f"[ETL] Fuente: {SOURCE_XLSM}")
    conn = load.connect()
    load.start_run(conn, run_id)
    conn.commit()

    stats: dict = {}
    recon: list[dict] = []
    checks: list[dict] = []
    try:
        raw = extract_source(SOURCE_XLSM)
        catalog = extract_catalog(SOURCE_XLSM)
        clean = clean_source(raw, catalog)
        stats = clean.stats
        print(
            f"[ETL] Leídas {stats['filas_leidas']} filas; "
            f"{stats['duplicados_exactos']} duplicados exactos."
        )

        dims = build_dimensions(clean, catalog)
        facts = build_facts(clean, dims)
        staging = build_staging(clean, str(SOURCE_XLSM), SOURCE_SHEET)

        with conn:
            load.truncate_all(conn)
            dim_counts = load.insert_dimensions(conn, dims)
            fact_counts = load.insert_facts(conn, facts)
            load.insert_staging(conn, staging)
            load.reset_sequences(conn)
            checks = quality.run_checks(clean, dims, facts, conn)
            load.insert_quality(conn, run_id, checks)
            recon = reconcile.build(clean, conn)
            load.insert_reconciliation(conn, run_id, recon)

            criticos = [r for r in recon if r["critico"] and not r["concilia"]]
            if criticos:
                detalle = "; ".join(
                    f"{r['metrica']} dif={r['diferencia']:.2f}" for r in criticos
                )
                raise RuntimeError(f"Conciliación fallida: {detalle}")

        load.finish_run(
            conn,
            run_id,
            "OK",
            stats,
            f"Dimensiones={dim_counts}; hechos={fact_counts}; staging={len(staging)}",
        )
        conn.commit()
        _print_summary(stats, recon, checks)
        print(f"[ETL] Fin OK run_id={run_id}")
        return 0

    except Exception as exc:
        conn.rollback()
        load.finish_run(conn, run_id, "ERROR", stats, traceback.format_exc()[:4000])
        conn.commit()
        print(f"[ETL] ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
