#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/runtime_export/export_runtime.py

Exportador determinista de bancos canónicos auditados a formato Runtime JSON v1
para Quiz Bible (Android/App).

Transforma los bancos canónicos estructurados (*-master-input.json) al contrato
definido en data/runtime/quiz_bible_runtime_v1.schema.json, preservando la
totalidad de la información editorial, trazabilidad, categorías, dificultades y
modos elegibles sin persistir texto bíblico RVR1960.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Esquema de validación predeterminado
DEFAULT_SCHEMA_PATH = REPO_ROOT / "data" / "runtime" / "quiz_bible_runtime_v1.schema.json"

# Claves prohibidas que indicarían persistencia no autorizada de texto bíblico
FORBIDDEN_SCRIPTURE_KEYS = {
    "verse_text",
    "versetext",
    "scripture_text",
    "scripturetext",
    "texto_biblico",
    "texto_bíblico",
    "textobiblico",
    "pasaje",
    "passage",
    "raw_verse",
    "biblical_text",
    "biblicaltext",
}

OLD_TESTAMENT_BOOKS = {
    "génesis", "genesis", "éxodo", "exodo", "levítico", "levitico",
    "números", "numeros", "deuteronomio", "josué", "josue", "jueces",
    "rut", "ruth", "1 samuel", "1samuel", "2 samuel", "2samuel",
    "1 reyes", "1kings", "2 reyes", "2kings", "1 crónicas", "1cronicas",
    "1chronicles", "2 crónicas", "2cronicas", "2chronicles",
    "esdras", "nehemías", "nehemias", "ester", "job", "salmos",
    "proverbios", "eclesiastés", "eclesiastes", "cantares", "cantar de los cantares",
    "isaías", "isaias", "jeremías", "jeremias", "lamentaciones",
    "ezequiel", "daniel", "oseas", "joel", "amós", "amos", "abdías", "abdias",
    "jonás", "jonas", "miqueas", "nahúm", "nahum", "habacuc",
    "sofonías", "sofonias", "hageo", "zacarías", "zacarias", "malaquías", "malaquias"
}


def normalize_difficulty(diff_str: str) -> str:
    """Normaliza la dificultad canónica a la enumeración técnica de runtime."""
    s = str(diff_str).strip().lower()
    s_clean = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    if s_clean in {"basico", "basic", "beginner", "facil"}:
        return "BASIC"
    if s_clean in {"intermedio", "intermediate", "medio"}:
        return "INTERMEDIATE"
    if s_clean in {"avanzado", "advanced", "dificil"}:
        return "ADVANCED"
    if s_clean in {"experto", "expert", "dificilismo"}:
        return "EXPERT"
    raise ValueError(f"Dificultad no reconocida: '{diff_str}'")


def normalize_question_type(qtype_str: str) -> str:
    """Normaliza el tipo de pregunta a la enumeración técnica de runtime."""
    s = str(qtype_str).strip().lower()
    s_clean = s.replace("é", "e").replace("ó", "o").replace("ú", "u")
    if "seleccion" in s_clean or "multiple" in s_clean or s_clean == "mc":
        return "MULTIPLE_CHOICE"
    return "MULTIPLE_CHOICE"


def determine_testament(q: dict[str, Any]) -> str:
    """Determina el testamento canónico (OT / NT) a partir del ID o del libro."""
    qid = str(q.get("id", "")).upper()
    if "-AT-" in qid:
        return "OT"
    if "-NT-" in qid:
        return "NT"
    book_name = str(q.get("book", "")).strip().lower()
    if book_name in OLD_TESTAMENT_BOOKS:
        return "OT"
    return "OT"


def assert_no_forbidden_keys(obj: Any, path: str = "$") -> None:
    """Valida recursivamente que ningún objeto contenga claves de texto bíblico persistido."""
    if isinstance(obj, dict):
        # A nivel de pregunta o raíz, 'text' suelto no está permitido (solo permitido dentro de options[])
        if not path.endswith("options") and not re.search(r"options\[\d+\]$", path):
            if "text" in obj:
                raise ValueError(
                    f"Violación de no persistencia de texto bíblico: clave 'text' encontrada fuera de options en {path}.text"
                )
        for k, v in obj.items():
            k_lower = str(k).lower()
            if k_lower in FORBIDDEN_SCRIPTURE_KEYS:
                raise ValueError(
                    f"Violación de no persistencia de texto bíblico: clave prohibida '{k}' encontrada en {path}.{k}"
                )
            assert_no_forbidden_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            assert_no_forbidden_keys(item, f"{path}[{idx}]")


def export_question_to_runtime(
    canonical_q: dict[str, Any],
    audit_status: str = "VERIFIED",
    human_review_status: str = "PENDING"
) -> dict[str, Any]:
    """Transforma una pregunta canónica al modelo de runtime V1."""
    qid = str(canonical_q["id"]).strip()
    book = str(canonical_q["book"]).strip()
    chapter = int(canonical_q["chapter"])
    verse_start = int(canonical_q["verse_start"])
    verse_end = int(canonical_q["verse_end"]) if canonical_q.get("verse_end") is not None else None
    ref_display = str(canonical_q.get("reference", f"{book} {chapter}:{verse_start}")).strip()

    category = str(canonical_q.get("category", "AT_GENERAL")).strip()
    subcategory = canonical_q.get("subcategory")
    if subcategory is not None:
        subcategory = str(subcategory).strip()

    characters = [str(c).strip() for c in canonical_q.get("characters", [])]
    difficulty = normalize_difficulty(str(canonical_q.get("difficulty", "Intermedio")))
    question_type = normalize_question_type(str(canonical_q.get("question_type", "Selección múltiple")))
    prompt = str(canonical_q.get("question", "")).strip()

    opcion_a = str(canonical_q.get("opcion_a", "")).strip()
    opcion_b = str(canonical_q.get("opcion_b", "")).strip()
    opcion_c = str(canonical_q.get("opcion_c", "")).strip()
    opcion_d = str(canonical_q.get("opcion_d", "")).strip()

    options = [
        {"id": "A", "text": opcion_a},
        {"id": "B", "text": opcion_b},
        {"id": "C", "text": opcion_c},
        {"id": "D", "text": opcion_d},
    ]

    correct_option_id = str(canonical_q.get("correct_option", "A")).strip().upper()
    explanation = str(canonical_q.get("explanation", "")).strip()
    eligible_modes = [str(m).strip() for m in canonical_q.get("eligible_modes", ["AT", "AMBOS"])]

    runtime_obj: dict[str, Any] = {
        "id": qid,
        "testament": determine_testament(canonical_q),
        "book": book,
        "chapter": chapter,
        "verseStart": verse_start,
        "verseEnd": verse_end,
        "referenceDisplay": ref_display,
        "category": category,
        "subcategory": subcategory,
        "characters": characters,
        "difficulty": difficulty,
        "questionType": question_type,
        "prompt": prompt,
        "options": options,
        "correctOptionId": correct_option_id,
        "explanation": explanation,
        "eligibleModes": eligible_modes,
        "verificationTranslation": "RVR1960",
        "auditStatus": audit_status,
        "humanReviewStatus": human_review_status,
    }

    assert_no_forbidden_keys(runtime_obj, path=f"Question({qid})")
    return runtime_obj


def build_runtime_collection(
    questions: list[dict[str, Any]],
    generated_at: str = "2026-08-21T00:00:00Z",
    schema_version: str = "quizbible-runtime-v1"
) -> dict[str, Any]:
    """Empaqueta una lista de preguntas de runtime en el contenedor oficial."""
    return {
        "schemaVersion": schema_version,
        "generatedAt": generated_at,
        "totalQuestions": len(questions),
        "questions": questions,
    }


def validate_runtime_collection(
    data: dict[str, Any],
    schema_path: Path | str | None = None
) -> bool:
    """Valida la colección de runtime contra el schema JSON oficial."""
    sp = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
    if not sp.exists():
        raise FileNotFoundError(f"Schema de runtime no encontrado en '{sp}'")

    schema_json = json.loads(sp.read_text(encoding="utf-8"))

    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema_json)
    except ImportError:
        # Validación estricta fallback integrada
        if data.get("schemaVersion") != "quizbible-runtime-v1":
            raise ValueError("schemaVersion inválido")
        if not isinstance(data.get("questions"), list):
            raise ValueError("questions debe ser una lista")
        if data.get("totalQuestions") != len(data["questions"]):
            raise ValueError("totalQuestions no coincide con el conteo de preguntas")
        for q in data["questions"]:
            if len(q.get("options", [])) != 4:
                raise ValueError(f"Pregunta {q.get('id')} no tiene 4 opciones")
            if q.get("correctOptionId") != "A":
                raise ValueError(f"correctOptionId canónico debe ser 'A' en {q.get('id')}")

    # Comprobación de no persistencia de fuentes
    assert_no_forbidden_keys(data, path="RuntimeCollection")
    return True


def export_canonical_data(
    canonical_questions: list[dict[str, Any]],
    filter_ids: set[str] | None = None,
    audit_status_map: dict[str, str] | None = None,
    human_review_status_map: dict[str, str] | None = None,
    generated_at: str = "2026-08-21T00:00:00Z"
) -> dict[str, Any]:
    """Transforma una lista de preguntas canónicas a una colección runtime oficial."""
    runtime_questions: list[dict[str, Any]] = []

    for q in canonical_questions:
        qid = q.get("id")
        if filter_ids is not None and qid not in filter_ids:
            continue
        audit_st = audit_status_map.get(qid, "VERIFIED") if audit_status_map else "VERIFIED"
        human_st = human_review_status_map.get(qid, "PENDING") if human_review_status_map else "PENDING"
        rt_q = export_question_to_runtime(q, audit_status=audit_st, human_review_status=human_st)
        runtime_questions.append(rt_q)

    # Si se especificó una lista de IDs filtrados, preservar el orden de esa lista si existe
    if filter_ids is not None and isinstance(filter_ids, list):
        id_order = {qid: i for i, qid in enumerate(filter_ids)}
        runtime_questions.sort(key=lambda x: id_order.get(x["id"], 999999))

    collection = build_runtime_collection(runtime_questions, generated_at=generated_at)
    validate_runtime_collection(collection)
    return collection


def export_files_to_runtime(
    input_paths: list[Path],
    output_path: Path,
    filter_ids: set[str] | list[str] | None = None,
    generated_at: str = "2026-08-21T00:00:00Z"
) -> tuple[dict[str, Any], str]:
    """Lee archivos canónicos, los transforma, valida y escribe el runtime JSON determinista."""
    all_canonical_qs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for p in input_paths:
        if not p.exists():
            raise FileNotFoundError(f"Archivo de entrada no encontrado: '{p}'")
        raw = json.loads(p.read_text(encoding="utf-8"))
        qs = raw.get("questions", raw) if isinstance(raw, dict) else raw
        for q in qs:
            qid = q.get("id")
            if qid not in seen_ids:
                seen_ids.add(qid)
                all_canonical_qs.append(q)

    collection = export_canonical_data(
        all_canonical_qs,
        filter_ids=filter_ids,
        generated_at=generated_at
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(collection, indent=2, ensure_ascii=False) + "\n"
    output_path.write_text(serialized, encoding="utf-8")

    sha256_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return collection, sha256_hash


def main() -> None:
    parser = argparse.ArgumentParser(description="Exportador de preguntas canónicas a Runtime JSON v1 para Quiz Bible.")
    parser.add_argument("--inputs", nargs="+", help="Rutas de archivos *-master-input.json", required=True)
    parser.add_argument("--output", help="Ruta del archivo JSON runtime de salida", required=True)
    parser.add_argument("--filter-ids", nargs="*", help="Lista opcional de IDs de preguntas a incluir", default=None)
    parser.add_argument("--generated-at", help="Marca de tiempo determinista ISO", default="2026-08-21T00:00:00Z")

    args = parser.parse_args()
    input_paths = [Path(p) for p in args.inputs]
    output_path = Path(args.output)
    filter_ids = args.filter_ids if args.filter_ids else None

    collection, sha = export_files_to_runtime(
        input_paths,
        output_path,
        filter_ids=filter_ids,
        generated_at=args.generated_at
    )

    print(f"Exportación runtime exitosa:")
    print(f"  Preguntas exportadas: {collection['totalQuestions']}")
    print(f"  Archivo de salida: {output_path}")
    print(f"  SHA-256: {sha}")


if __name__ == "__main__":
    main()
