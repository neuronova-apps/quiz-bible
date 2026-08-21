#!/usr/bin/env python3
"""Generador de informe oficial a partir de los artefactos JSON producidos por el auditor RVR1960.

Lee directamente:
- build/audit/genesis/resumen-general.json
- build/audit/genesis/revision-manual-pendiente.json
- build/audit/genesis/correcciones-aplicadas.json
- build/audit/genesis/genesis-XX-XX.json

Escribe:
- build/audit/genesis/informe-oficial.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo '{path}'.")
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report(output_dir: Path, master_input_path: Path) -> dict[str, Any]:
    summary_path = output_dir / "resumen-general.json"
    revision_path = output_dir / "revision-manual-pendiente.json"
    corrections_path = output_dir / "correcciones-aplicadas.json"

    summary = load_json(summary_path)
    revision = load_json(revision_path) if revision_path.exists() else {"total_pendientes": 0, "pendientes": []}
    corrections = load_json(corrections_path) if corrections_path.exists() else {"total_correcciones": 0, "correcciones": []}
    master = load_json(master_input_path)

    # Validaciones de integridad obligatorias
    master_questions = master.get("questions", []) if isinstance(master, dict) else master
    master_map = {q["id"]: q for q in master_questions}

    total_q = summary.get("total_questions", 0)
    verif_c = summary.get("verified_count", 0)
    req_corr_c = summary.get("requires_correction_count", 0)
    inconc_c = summary.get("inconclusive_count", 0)
    persisted = summary.get("source_text_persisted", True)

    chapters_in_bank = summary.get("chapters_present_in_bank", summary.get("chapters_covered", 0))
    successful_fetches = summary.get("successful_chapter_fetches", summary.get("chapters_covered", 0))
    failed_fetches_count = summary.get("failed_chapter_fetches", 0)
    failed_chapters = summary.get("failed_chapters", [])
    http_attempts = summary.get("http_request_attempts_total", chapters_in_bank)
    rate_retries = summary.get("rate_limit_retries", 0)
    textual_coverage_complete = summary.get("textual_coverage_complete", (successful_fetches == 50 and len(failed_chapters) == 0))

    if total_q != (verif_c + req_corr_c + inconc_c):
        raise ValueError(f"Inconsistencia matemática en resumen: total ({total_q}) != verif ({verif_c}) + req_corr ({req_corr_c}) + inconc ({inconc_c})")

    if total_q != len(master_questions):
        raise ValueError(f"Discrepancia en cantidad de preguntas: summary ({total_q}) vs master ({len(master_questions)})")

    # Recopilar todos los resultados individuales de los bloques
    block_files = sorted(output_dir.glob("genesis-*.json"))
    all_block_results = []
    for bf in block_files:
        b_data = load_json(bf)
        all_block_results.extend(b_data.get("results", []))

    # Validar coincidencia de IDs y referencias con el master canónico
    for r in all_block_results:
        qid = r.get("id")
        if qid not in master_map:
            raise ValueError(f"ID desconocido en resultados: '{qid}'")
        expected_ref = master_map[qid].get("reference")
        actual_ref = r.get("reference")
        if expected_ref != actual_ref:
            raise ValueError(f"Discrepancia de referencia para {qid}: esperado '{expected_ref}', obtenido '{actual_ref}'")

    requires_correction_items = [p for p in revision.get("pendientes", []) if p.get("estado") == "REQUIERE_CORRECCION"]
    inconclusive_items = [p for p in revision.get("pendientes", []) if p.get("estado") == "NO_CONCLUYENTE"]

    official_report = {
        "run_schema_version": "quizbible-official-audit-report-v1",
        "total_questions": total_q,
        "verified_count": verif_c,
        "requires_correction_count": req_corr_c,
        "inconclusive_count": inconc_c,
        "verification_rate": summary.get("verification_rate", round(verif_c / total_q * 100, 2) if total_q else 0.0),
        "chapters_present_in_bank": chapters_in_bank,
        "successful_chapter_fetches": successful_fetches,
        "failed_chapter_fetches": failed_fetches_count,
        "failed_chapters": failed_chapters,
        "textual_coverage_complete": textual_coverage_complete,
        "http_request_attempts_total": http_attempts,
        "rate_limit_retries": rate_retries,
        "source_text_persisted": persisted,
        "controls_distribution": summary.get("controls_distribution", {}),
        "requires_correction_items": requires_correction_items,
        "inconclusive_items": inconclusive_items,
        "total_blocks": len(block_files),
    }

    # Escribir informe-oficial.json directamente
    informe_path = output_dir / "informe-oficial.json"
    informe_path.write_text(json.dumps(official_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return official_report


def print_markdown_report(report: dict[str, Any]) -> None:
    print("================================================================================")
    print("                    INFORME OFICIAL DE AUDITORÍA RVR1960                       ")
    print("================================================================================")
    print(f"Total preguntas procesadas      : {report['total_questions']}")
    print(f"VERIFICADO                      : {report['verified_count']} ({report['verification_rate']}%)")
    print(f"REQUIERE_CORRECCION             : {report['requires_correction_count']}")
    print(f"NO_CONCLUYENTE                  : {report['inconclusive_count']}")
    print(f"Capítulos en banco maestro      : {report['chapters_present_in_bank']}")
    print(f"Capítulos obtenidos con éxito   : {report['successful_chapter_fetches']}/50")
    print(f"Capítulos fallidos              : {report['failed_chapters']}")
    print(f"Cobertura textual completa      : {report['textual_coverage_complete']}")
    print(f"Intentos HTTP totales           : {report['http_request_attempts_total']}")
    print(f"Reintentos por rate limit (429) : {report['rate_limit_retries']}")
    print(f"source_text_persisted           : {report['source_text_persisted']}")
    print("--------------------------------------------------------------------------------")
    print("Distribución de los 17 Controles:")
    for c_name, counts in report["controls_distribution"].items():
        print(f"  - {c_name:<32}: PASS={counts.get('PASS', 0):<3} FAIL={counts.get('FAIL', 0):<3} UNKNOWN={counts.get('UNKNOWN', 0):<3} NOT_APPLICABLE={counts.get('NOT_APPLICABLE', 0):<3}")
    print("--------------------------------------------------------------------------------")

    if report["requires_correction_items"]:
        print(f"Lista de Casos REQUIERE_CORRECCION ({len(report['requires_correction_items'])}):")
        for item in report["requires_correction_items"]:
            print(f"  * [{item['id']}] {item['reference']}: {'; '.join(item.get('incidencias', []))}")
    else:
        print("Lista de Casos REQUIERE_CORRECCION: Ninguno (0).")

    if report["inconclusive_items"]:
        print(f"\nLista de Casos NO_CONCLUYENTE ({len(report['inconclusive_items'])}):")
        for item in report["inconclusive_items"]:
            print(f"  * [{item['id']}] {item['reference']}: {'; '.join(item.get('incidencias', []))}")
    else:
        print("\nLista de Casos NO_CONCLUYENTE: Ninguno (0).")

    print("================================================================================\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera informe oficial de auditoría desde artefactos JSON")
    parser.add_argument("--output-dir", default="build/audit/genesis", help="Directorio de salidas de auditoría")
    parser.add_argument("--master-input", default="tools/bible_extractor/genesis-master-input.json", help="Ruta de genesis-master-input.json")
    args = parser.parse_args()

    try:
        report = generate_report(Path(args.output_dir), Path(args.master_input))
        print_markdown_report(report)
        return 0
    except Exception as exc:
        print(f"Error generando reporte oficial: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
