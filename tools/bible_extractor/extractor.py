#!/usr/bin/env python3
"""Extractor temporal para el banco de Quiz Bible.

Valida la API Key, consulta un capítulo RVR1960, separa los versículos en
memoria y prepara una estructura de trabajo para futuras preguntas. El texto
bíblico nunca se escribe en disco: solo se persisten metadatos, referencias y
campos vacíos del banco.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSE_TEST_URL = "https://api.apibiblia.com/v1/verses/JHN/3/16?version=RVR1960"
PASSAGE_URL = "https://api.apibiblia.com/v1/passage"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", required=True, help="Libro o nombre aceptado por ApiBiblia")
    parser.add_argument("--chapter", required=True, type=int, help="Número de capítulo")
    parser.add_argument("--version", default="RVR1960")
    parser.add_argument("--output", default="build/extraction-report.json")
    parser.add_argument("--candidates-output", default="build/question-candidates.json")
    return parser.parse_args()


def count_text_nodes(value: Any) -> tuple[int, int]:
    """Cuenta nodos con texto sin copiar su contenido al reporte."""
    nodes = 0
    chars = 0
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            nodes += 1
            chars += len(text)
        for child in value.values():
            n, c = count_text_nodes(child)
            nodes += n
            chars += c
    elif isinstance(value, list):
        for child in value:
            n, c = count_text_nodes(child)
            nodes += n
            chars += c
    return nodes, chars


def api_get(url: str, api_key: str) -> tuple[int, object]:
    request = urllib.request.Request(
        url,
        headers={
            "X-API-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "QuizBible-Extractor/1.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"ApiBiblia HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        if body:
            print(f"Respuesta del servidor: {body[:500]}", file=sys.stderr)
        raise


def _int_from_value(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        match = re.search(r"(?:^|[.:\s])(\d+)$", value.strip())
        if match:
            number = int(match.group(1))
            return number if number > 0 else None
    return None


def _verse_number_from_node(node: dict[str, Any]) -> int | None:
    for key in ("verse", "verseNumber", "verse_number", "number", "verseId", "verse_id"):
        if key in node:
            number = _int_from_value(node.get(key))
            if number:
                return number
    for key in ("reference", "ref", "id"):
        value = node.get(key)
        if isinstance(value, str):
            match = re.search(r"(?:[:.]|\s)(\d+)\s*$", value)
            if match:
                number = int(match.group(1))
                if number > 0:
                    return number
    return None


def extract_verses(value: Any) -> list[dict[str, Any]]:
    """Recoge, en orden, nodos de versículo que contengan texto.

    La lista resultante vive solo en memoria. Se conserva el texto únicamente
    para que una fase posterior pueda consumirlo dentro de la misma ejecución.
    """
    verses: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text = node.get("text")
            if isinstance(text, str) and text.strip():
                verses.append(
                    {
                        "verse_number": _verse_number_from_node(node),
                        "text": text.strip(),
                        "reference_from_api": node.get("reference") or node.get("ref"),
                    }
                )
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)

    # Si la API no incluye el número en cada nodo, el orden del capítulo es
    # suficiente para numerarlos. No se altera el texto.
    for index, verse in enumerate(verses, start=1):
        if not verse["verse_number"]:
            verse["verse_number"] = index
    return verses


def build_question_candidates(book: str, chapter: int, verses: list[dict[str, Any]]) -> dict[str, Any]:
    """Crea el esqueleto persistible del banco sin copiar texto bíblico."""
    items = []
    for verse in verses:
        number = int(verse["verse_number"])
        api_reference = verse.get("reference_from_api")
        reference = api_reference.strip() if isinstance(api_reference, str) and api_reference.strip() else f"{book} {chapter}:{number}"
        items.append(
            {
                "verse_number": number,
                "reference": reference,
                "question": None,
                "options": [],
                "correct_answer": None,
                "explanation": None,
                "difficulty": None,
                "category": None,
                "status": "pending_generation",
                "source_text_persisted": False,
            }
        )
    return {
        "schema_version": "quizbible-question-candidates-v1",
        "source": "ApiBiblia",
        "version": "RVR1960",
        "book": book,
        "chapter": chapter,
        "verse_count": len(items),
        "items": items,
    }


def main() -> int:
    args = parse_args()
    if args.chapter < 1:
        raise SystemExit("El capítulo debe ser mayor o igual a 1.")
    if args.version.upper() != "RVR1960":
        raise SystemExit("Este flujo está restringido a RVR1960.")

    api_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Falta el secreto APIBIBLIA_API_KEY.")

    print("Paso 1/3: validando API Key con JHN 3:16 (RVR1960)...")
    try:
        auth_status, auth_payload = api_get(VERSE_TEST_URL, api_key)
    except urllib.error.HTTPError as exc:
        print(
            f"La prueba oficial JHN 3:16 falló con HTTP {exc.code}. "
            "Esto indica un problema de autenticación/autorización de la API Key o de la cuenta.",
            file=sys.stderr,
        )
        return 10
    except Exception as exc:
        print(f"Error de red durante la prueba de autenticación: {exc}", file=sys.stderr)
        return 11

    if auth_status != 200:
        print(f"La prueba de autenticación devolvió HTTP {auth_status}.", file=sys.stderr)
        return 12

    print("API Key aceptada por el endpoint oficial de versículo.")

    book = args.book.strip()
    reference = f"{book} {args.chapter}"
    query = urllib.parse.urlencode({"ref": reference, "version": "RVR1960"})
    passage_url = f"{PASSAGE_URL}?{query}"

    print(f"Paso 2/3: consultando capítulo {reference}...")
    try:
        chapter_status, chapter_payload = api_get(passage_url, api_key)
    except urllib.error.HTTPError as exc:
        print(
            f"La API Key sí fue aceptada en JHN 3:16, pero el capítulo falló con HTTP {exc.code}.",
            file=sys.stderr,
        )
        return 20
    except Exception as exc:
        print(f"Error de red consultando el capítulo: {exc}", file=sys.stderr)
        return 21

    success = chapter_payload.get("success", True) if isinstance(chapter_payload, dict) else True
    if not success:
        print("ApiBiblia devolvió una respuesta de capítulo no exitosa.", file=sys.stderr)
        return 22

    print("Paso 3/3: separando versículos y preparando estructura temporal...")
    verses = extract_verses(chapter_payload)
    if not verses:
        print("No se pudieron identificar versículos con texto en la respuesta.", file=sys.stderr)
        return 30

    # Validar numeración sin incluir texto en ningún archivo persistente.
    verse_numbers = [int(v["verse_number"]) for v in verses]
    duplicated_numbers = sorted({n for n in verse_numbers if verse_numbers.count(n) > 1})
    sequential = verse_numbers == list(range(1, len(verse_numbers) + 1))

    auth_nodes, auth_chars = count_text_nodes(auth_payload)
    chapter_nodes, chapter_chars = count_text_nodes(chapter_payload)
    candidates = build_question_candidates(book, args.chapter, verses)

    candidates_output = Path(args.candidates_output)
    candidates_output.parent.mkdir(parents=True, exist_ok=True)
    candidates_output.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "source": "ApiBiblia",
        "version_requested": "RVR1960",
        "authentication_probe": {
            "reference": "JHN 3:16",
            "http_status": auth_status,
            "response_valid": True,
            "text_nodes_detected": auth_nodes,
            "character_count_detected": auth_chars,
        },
        "chapter_probe": {
            "reference_requested": reference,
            "http_status": chapter_status,
            "response_valid": True,
            "text_nodes_detected": chapter_nodes,
            "character_count_detected": chapter_chars,
        },
        "verse_processing": {
            "verses_prepared_in_memory": len(verses),
            "verse_numbers_sequential": sequential,
            "duplicate_verse_numbers": duplicated_numbers,
            "question_candidates_created": len(candidates["items"]),
            "candidate_schema": candidates["schema_version"],
            "persisted_fields": [
                "verse_number",
                "reference",
                "question",
                "options",
                "correct_answer",
                "explanation",
                "difficulty",
                "category",
                "status",
            ],
        },
        "scripture_text_persisted": False,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "next_stage": "question_generation_from_in_memory_verses",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Borrado explícito de los objetos que contienen RVR1960 antes de terminar.
    for verse in verses:
        verse["text"] = ""
    del verses
    del auth_payload
    del chapter_payload

    print(
        f"Procesamiento completado para {reference}: {len(candidates['items'])} candidatos preparados. "
        "El texto RVR1960 no fue persistido."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
