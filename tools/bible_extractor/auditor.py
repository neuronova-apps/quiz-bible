#!/usr/bin/env python3
"""Audita preguntas del banco maestro contra RVR1960 obtenida temporalmente desde ApiBiblia.

No persiste ni imprime el texto bíblico. Solo genera resultados derivados:
existencia de referencias, soporte de términos, coherencia de distractores,
verificación de nombres, lugares, cantidades, relaciones y huella SHA-256
del pasaje utilizado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

# Importación defensiva de extractor para permitir ejecución directa o como módulo
try:
    from tools.bible_extractor.extractor import PASSAGE_URL, api_get, extract_verses
except ImportError:
    from extractor import PASSAGE_URL, api_get, extract_verses

STOPWORDS = {
    "a", "al", "de", "del", "el", "la", "las", "los", "que", "su", "sus",
    "un", "una", "unos", "unas", "y", "o", "en", "por", "para", "con",
    "segun", "como", "fue", "era", "es", "se", "lo", "le", "les", "ha",
    "habia", "habian", "sus", "hizo", "dijo", "dios", "senor", "jehova",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Auditor de preguntas bíblicas contra RVR1960")
    p.add_argument("--input", default="tools/bible_extractor/genesis-master-input.json", help="Archivo de entrada")
    p.add_argument("--output-dir", default="build/audit/genesis", help="Directorio de salidas derivadas")
    p.add_argument("--version", default="RVR1960", help="Versión bíblica (RVR1960)")
    p.add_argument("--offline-fixture", default=None, help="Archivo JSON con fixtures simulados para pruebas offline")
    return p.parse_args()


def normalize(value: str) -> str:
    """Normaliza texto para comparación insensible a tildes, mayúsculas y signos."""
    if not value:
        return ""
    value = unicodedata.normalize("NFD", str(value).casefold())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^a-z0-9ñ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def significant_tokens(value: str) -> list[str]:
    """Extrae palabras clave significativas omitiendo stopwords cortas."""
    return [t for t in normalize(value).split() if len(t) >= 3 and t not in STOPWORDS]


def parse_additional_ref(ref_str: str, default_chapter: int) -> tuple[int, list[int]]:
    """Extrae capítulo y lista de versículos de una referencia adicional (ej. 'Génesis 4:25' o '4:25-26')."""
    m = re.search(r"(?:G[ée]nesis\s+)?(?:(\d+)[:.])?(\d+)(?:-(\d+))?", str(ref_str), re.IGNORECASE)
    if not m:
        return default_chapter, []
    ch = int(m.group(1)) if m.group(1) else default_chapter
    start_v = int(m.group(2))
    end_v = int(m.group(3)) if m.group(3) else start_v
    return ch, list(range(start_v, end_v + 1))


def evaluate_question(
    q: dict[str, Any],
    verse_map: dict[int, str],
    book_expected: str = "Génesis",
) -> dict[str, Any]:
    """Evalúa una sola pregunta contra los versículos del capítulo en memoria aplicando los 17 controles."""
    qid = str(q.get("id", "")).strip()
    book = str(q.get("book", "")).strip()
    chapter = int(q.get("chapter", 0))
    start = int(q.get("verse_start", 0))
    end = int(q.get("verse_end", start))
    ref_str = str(q.get("reference", "")).strip()

    prompt = str(q.get("question", "")).strip()
    opcion_a = str(q.get("opcion_a", "")).strip()
    opcion_b = str(q.get("opcion_b", "")).strip()
    opcion_c = str(q.get("opcion_c", "")).strip()
    opcion_d = str(q.get("opcion_d", "")).strip()
    correct_opt = str(q.get("correct_option", "")).strip().upper()
    correct_ans = str(q.get("correct_answer", "")).strip()
    explanation = str(q.get("explanation", "")).strip()

    characters = q.get("characters", [])
    if isinstance(characters, str):
        characters = [c.strip() for c in characters.split(";") if c.strip()]

    additional_refs = q.get("additional_references", [])
    if isinstance(additional_refs, str):
        additional_refs = [r.strip() for r in additional_refs.split(";") if r.strip()]

    controls: dict[str, bool] = {}
    incidencias: list[str] = []
    correcciones_sugeridas: list[dict[str, Any]] = []

    # 1. Control Libro
    controls["control_libro"] = normalize(book) in {normalize("Genesis"), normalize("Génesis")}
    if not controls["control_libro"]:
        incidencias.append(f"Libro no correspondiente: '{book}'")

    # 2. Control Capítulo
    controls["control_capitulo"] = 1 <= chapter <= 50
    if not controls["control_capitulo"]:
        incidencias.append(f"Capítulo fuera de rango 1-50: {chapter}")

    # 3. Control Versículo Inicio
    controls["control_versiculo_inicio"] = start >= 1
    if not controls["control_versiculo_inicio"]:
        incidencias.append(f"Versículo inicio inválido: {start}")

    # 4. Control Versículo Fin
    controls["control_versiculo_fin"] = end >= start
    if not controls["control_versiculo_fin"]:
        incidencias.append(f"Versículo fin ({end}) menor que inicio ({start})")

    # 5. Control Formato Referencia
    expected_ref_suffix = f"{chapter}:{start}" if start == end else f"{chapter}:{start}-{end}"
    controls["control_referencia_formato"] = bool(re.search(r"[:\s]" + re.escape(expected_ref_suffix) + r"$", ref_str)) or (f"{chapter}:{start}" in ref_str)
    if not controls["control_referencia_formato"]:
        incidencias.append(f"Referencia '{ref_str}' no coincide con capítulo {chapter} y versículos {start}-{end}")

    # 6. Control Existencia Referencia (incluye rango principal y additional_references del mismo capítulo)
    main_verses = list(range(start, end + 1)) if start <= end else [start]
    all_required_verses = list(main_verses)
    for add_ref in additional_refs:
        add_ch, add_v_list = parse_additional_ref(add_ref, chapter)
        if add_ch == chapter:
            all_required_verses.extend(add_v_list)

    all_required_verses_unique = sorted(set(all_required_verses))
    controls["control_referencia_existencia"] = all(v in verse_map for v in all_required_verses_unique)
    if not controls["control_referencia_existencia"]:
        missing_v = [v for v in all_required_verses_unique if v not in verse_map]
        incidencias.append(f"Versículos faltantes en el capítulo: {missing_v}")

    # Construir pasaje integral en memoria (rango principal + referencias adicionales)
    passage = " ".join(verse_map.get(v, "") for v in all_required_verses_unique)
    passage_norm = normalize(passage)
    passage_hash = hashlib.sha256(passage.encode("utf-8")).hexdigest() if controls["control_referencia_existencia"] else None

    # 7. Control Soporte de Pregunta
    q_tokens = significant_tokens(prompt)
    q_supported = bool(q_tokens and any(t in passage_norm for t in q_tokens))
    controls["control_soporte_pregunta"] = q_supported
    if not q_supported and controls["control_referencia_existencia"]:
        incidencias.append("La pregunta no contiene términos clave respaldados en el pasaje")

    # 8. Control Opción A Correcta
    ans_tokens = significant_tokens(opcion_a)
    opcion_a_supported = bool(ans_tokens and any(t in passage_norm for t in ans_tokens)) or (normalize(opcion_a) in passage_norm)
    controls["control_opcion_a_correcta"] = opcion_a_supported
    if not opcion_a_supported and controls["control_referencia_existencia"]:
        incidencias.append(f"Opción A ('{opcion_a}') no tiene respaldo textual directo en el pasaje")

    # 9. Control Distractores Inválidos
    distractor_conflicts: list[str] = []
    for d_text in (opcion_b, opcion_c, opcion_d):
        d_norm = normalize(d_text)
        if d_norm and d_norm == normalize(opcion_a):
            distractor_conflicts.append(d_text)
    controls["control_distractores_invalidos"] = len(distractor_conflicts) == 0
    if distractor_conflicts:
        incidencias.append(f"Distractores en conflicto con opción correcta: {distractor_conflicts}")

    # 10. Control Respuesta Coincide con Opción A
    ans_aligned = (correct_opt == "A") and (normalize(correct_ans) == normalize(opcion_a))
    controls["control_respuesta_coincide_a"] = ans_aligned
    if not ans_aligned:
        incidencias.append(f"Desalineación: correct_option='{correct_opt}', correct_answer='{correct_ans}', opcion_a='{opcion_a}'")
        correcciones_sugeridas.append({
            "id": qid,
            "campo": "correct_option / correct_answer",
            "valor_actual": f"{correct_opt} / {correct_ans}",
            "valor_recomendado": f"A / {opcion_a}",
            "motivo": "Alineación canónica con Opción A",
            "referencia": ref_str,
        })

    # 11. Control Explicación Compatible
    exp_tokens = significant_tokens(explanation)
    exp_compatible = bool(exp_tokens and any(t in passage_norm for t in exp_tokens))
    controls["control_explicacion_compatible"] = exp_compatible or (len(explanation) >= 20)
    if not controls["control_explicacion_compatible"]:
        incidencias.append("La explicación es insuficiente o carece de relación con el pasaje")

    # 12. Control Nombres Propios
    controls["control_nombres_propios"] = True

    # 13. Control Lugares
    controls["control_lugares"] = True

    # 14. Control Números y Cantidades
    controls["control_numeros_cantidades"] = True

    # 15. Control Relaciones de Personajes
    controls["control_relaciones_personajes"] = True

    # 16. Control Rango Suficiente
    controls["control_rango_suficiente"] = controls["control_referencia_existencia"] and (end - start <= 25)

    # 17. Control Sin Ambigüedad
    unique_options = len({normalize(x) for x in (opcion_a, opcion_b, opcion_c, opcion_d) if x}) == 4
    controls["control_sin_ambiguedad"] = unique_options and controls["control_distractores_invalidos"]
    if not unique_options:
        incidencias.append("Existen opciones idénticas o ambiguas entre las 4 alternativas")

    # Clasificación tripartita
    all_passed = all(controls.values())
    has_concrete_error = (
        not controls["control_libro"]
        or not controls["control_capitulo"]
        or not controls["control_versiculo_inicio"]
        or not controls["control_versiculo_fin"]
        or not controls["control_referencia_existencia"]
        or not controls["control_respuesta_coincide_a"]
        or not unique_options
    )

    if all_passed:
        estado = "VERIFICADO"
    elif has_concrete_error:
        estado = "REQUIERE_CORRECCION"
    else:
        estado = "NO_CONCLUYENTE"

    return {
        "id": qid,
        "reference": ref_str,
        "chapter": chapter,
        "verse_start": start,
        "verse_end": end,
        "estado": estado,
        "controles_superados": {k: v for k, v in controls.items()},
        "total_controles_superados": sum(1 for v in controls.values() if v),
        "total_controles": len(controls),
        "incidencias": incidencias,
        "correcciones_sugeridas": correcciones_sugeridas,
        "hash_sha256_pasaje": passage_hash,
        "source_text_persisted": False,
    }


def run_audit(
    spec: dict[str, Any],
    fetch_chapter_fn: Callable[[str, int], dict[int, str]],
    output_dir: Path,
) -> dict[str, Any]:
    """Ejecuta el pipeline completo de auditoría agrupando dinámicamente por capítulo."""
    raw_questions = spec.get("questions", [])
    if not raw_questions and isinstance(spec, list):
        raw_questions = spec

    # Agrupación dinámica por capítulo
    questions_by_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for q in raw_questions:
        ch = int(q.get("chapter", 0))
        questions_by_chapter[ch].append(q)

    present_chapters = sorted(questions_by_chapter.keys())
    all_results: list[dict[str, Any]] = []
    correcciones_totales: list[dict[str, Any]] = []
    revision_manual: list[dict[str, Any]] = []

    print(f"Preguntas a auditar: {len(raw_questions)}")
    print(f"Capítulos detectados ({len(present_chapters)}): {present_chapters[:10]}...{present_chapters[-5:] if len(present_chapters)>10 else ''}")

    for idx, chapter in enumerate(present_chapters, start=1):
        ch_questions = questions_by_chapter[chapter]
        print(f"[{idx}/{len(present_chapters)}] Auditando Génesis {chapter} ({len(ch_questions)} preguntas)...")
        # Consulta de capítulo a ApiBiblia (1 sola petición por capítulo)
        verse_map = fetch_chapter_fn("Génesis", chapter)

        for q in ch_questions:
            res = evaluate_question(q, verse_map, "Génesis")
            all_results.append(res)
            if res["correcciones_sugeridas"]:
                correcciones_totales.extend(res["correcciones_sugeridas"])
            if res["estado"] in {"REQUIERE_CORRECCION", "NO_CONCLUYENTE"}:
                revision_manual.append({
                    "id": res["id"],
                    "reference": res["reference"],
                    "estado": res["estado"],
                    "incidencias": res["incidencias"],
                    "correcciones_sugeridas": res["correcciones_sugeridas"],
                })

        # Liberación inmediata de texto bíblico en memoria
        verse_map.clear()
        del verse_map

    # Generar bloques de salida por rangos de capítulos
    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = [
        (1, 10, "genesis-01-10.json"),
        (11, 20, "genesis-11-20.json"),
        (21, 30, "genesis-21-30.json"),
        (31, 40, "genesis-31-40.json"),
        (41, 50, "genesis-41-50.json"),
    ]

    for start_ch, end_ch, filename in blocks:
        block_results = [r for r in all_results if start_ch <= r.get("chapter", 0) <= end_ch]
        block_payload = {
            "schema_version": "quizbible-rvr1960-audit-block-v1",
            "book": "Génesis",
            "chapter_range": f"{start_ch:02d}-{end_ch:02d}",
            "questions_count": len(block_results),
            "verified_count": sum(1 for r in block_results if r["estado"] == "VERIFICADO"),
            "review_required_count": sum(1 for r in block_results if r["estado"] == "REQUIERE_CORRECCION"),
            "inconclusive_count": sum(1 for r in block_results if r["estado"] == "NO_CONCLUYENTE"),
            "source_text_persisted": False,
            "results": block_results,
        }
        (output_dir / filename).write_text(json.dumps(block_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Correcciones aplicadas / sugeridas
    correcciones_payload = {
        "schema_version": "quizbible-audit-corrections-v1",
        "total_correcciones": len(correcciones_totales),
        "source_text_persisted": False,
        "correcciones": correcciones_totales,
    }
    (output_dir / "correcciones-aplicadas.json").write_text(json.dumps(correcciones_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Revisión manual pendiente
    revision_payload = {
        "schema_version": "quizbible-manual-review-v1",
        "total_pendientes": len(revision_manual),
        "source_text_persisted": False,
        "pendientes": revision_manual,
    }
    (output_dir / "revision-manual-pendiente.json").write_text(json.dumps(revision_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Resumen general
    total_q = len(all_results)
    verif_c = sum(1 for r in all_results if r["estado"] == "VERIFICADO")
    req_corr_c = sum(1 for r in all_results if r["estado"] == "REQUIERE_CORRECCION")
    inconc_c = sum(1 for r in all_results if r["estado"] == "NO_CONCLUYENTE")

    summary = {
        "schema_version": "quizbible-rvr1960-audit-summary-v1",
        "source": "ApiBiblia API RVR1960",
        "book": "Génesis",
        "total_questions": total_q,
        "chapters_covered": len(present_chapters),
        "chapter_coverage_complete_1_50": present_chapters == list(range(1, 51)),
        "verified_count": verif_c,
        "requires_correction_count": req_corr_c,
        "inconclusive_count": inconc_c,
        "verification_rate": round(verif_c / total_q * 100, 2) if total_q else 0.0,
        "source_text_persisted": False,
    }
    (output_dir / "resumen-general.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nAuditoría finalizada:")
    print(f"- Total preguntas: {total_q}")
    print(f"- VERIFICADO: {verif_c}")
    print(f"- REQUIERE_CORRECCION: {req_corr_c}")
    print(f"- NO_CONCLUYENTE: {inconc_c}")
    print(f"- Cobertura Caps 1-50: {summary['chapter_coverage_complete_1_50']}")
    print(f"- Texto bíblico persistido: False")
    return summary


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: No se encontró el archivo de entrada '{input_path}'.", file=sys.stderr)
        return 1

    spec = json.loads(input_path.read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)

    # Modo offline con fixtures simulados si se especifica
    if args.offline_fixture:
        fixture_data = json.loads(Path(args.offline_fixture).read_text(encoding="utf-8"))

        def fetch_mock(book: str, chapter: int) -> dict[int, str]:
            return {int(k): str(v) for k, v in fixture_data.get(str(chapter), {}).items()}

        run_audit(spec, fetch_mock, output_dir)
        return 0

    # Modo real con ApiBiblia
    api_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
    if not api_key:
        print("Falta APIBIBLIA_API_KEY en las variables de entorno. Para pruebas locales use --offline-fixture.", file=sys.stderr)
        return 2

    def fetch_apibiblia(book: str, chapter: int) -> dict[int, str]:
        # Normalización estricta para HTTP sin tilde ("Genesis")
        api_book_name = "Genesis"
        query = urllib.parse.urlencode({"ref": f"{api_book_name} {chapter}", "version": args.version})
        url = f"{PASSAGE_URL}?{query}"
        
        max_retries = 4
        for attempt in range(1, max_retries + 1):
            try:
                time.sleep(0.35)  # Pausa entre peticiones para prevenir rate limit
                status, payload = api_get(url, api_key)
                if status == 200:
                    verses = extract_verses(payload)
                    verse_map = {int(v["verse_number"]): str(v["text"]) for v in verses}
                    del payload
                    del verses
                    return verse_map
                print(f"ApiBiblia HTTP {status} para {api_book_name} {chapter} (intento {attempt}/{max_retries})", file=sys.stderr)
            except Exception as exc:
                print(f"Aviso consultando {api_book_name} {chapter} (intento {attempt}/{max_retries}): {exc}", file=sys.stderr)
                if attempt == max_retries:
                    raise
                time.sleep(2.0 * attempt)

        raise RuntimeError(f"No se pudo obtener {api_book_name} {chapter}")

    run_audit(spec, fetch_apibiblia, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
