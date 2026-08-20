#!/usr/bin/env python3
"""Genera preguntas de Quiz Bible usando RVR1960 solo en memoria.

Flujo: ApiBiblia -> capítulo RVR1960 en memoria -> Gemini -> banco derivado.
El texto bíblico fuente no se escribe en archivos ni se incluye en la salida.
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
from pathlib import Path
from typing import Any

PASSAGE_URL = "https://api.apibiblia.com/v1/passage"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--book", required=True)
    p.add_argument("--chapter", required=True, type=int)
    p.add_argument("--version", default="RVR1960")
    p.add_argument("--model", default="gemini-3.6-flash")
    p.add_argument("--output", default="build/generated-questions.json")
    return p.parse_args()


def api_get(url: str, api_key: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "X-API-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "QuizBible-Generator/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _int_from_value(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        m = re.search(r"(?:^|[.:\s])(\d+)$", value.strip())
        if m:
            return int(m.group(1))
    return None


def extract_verses(value: Any) -> list[dict[str, Any]]:
    verses: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text = node.get("text")
            if isinstance(text, str) and text.strip():
                number = None
                for key in ("verse", "verseNumber", "verse_number", "number", "verseId", "verse_id"):
                    number = _int_from_value(node.get(key))
                    if number:
                        break
                if not number:
                    for key in ("reference", "ref", "id"):
                        ref = node.get(key)
                        if isinstance(ref, str):
                            m = re.search(r"(?:[:.]|\s)(\d+)\s*$", ref)
                            if m:
                                number = int(m.group(1))
                                break
                verses.append({"verse_number": number, "text": text.strip()})
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    for index, verse in enumerate(verses, start=1):
        if not verse["verse_number"]:
            verse["verse_number"] = index
    return verses


def gemini_generate(model: str, api_key: str, prompt: str) -> Any:
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "verse_number": {"type": "integer"},
                        "question": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
                        "correct_answer": {"type": "string"},
                        "explanation": {"type": "string"},
                        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                        "category": {"type": "string"},
                    },
                    "required": [
                        "verse_number", "question", "options", "correct_answer",
                        "explanation", "difficulty", "category"
                    ],
                },
            }
        },
        "required": ["items"],
    }
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 20000,
            "responseFormat": {
                "text": {
                    "mimeType": "application/json",
                    "schema": schema,
                }
            },
        },
    }
    req = urllib.request.Request(
        GEMINI_URL.format(model=urllib.parse.quote(model, safe="-._")),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception as exc:
        raise RuntimeError("Gemini no devolvió JSON estructurado utilizable") from exc


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def validate_generated(book: str, chapter: int, verses: list[dict[str, Any]], generated: Any) -> dict[str, Any]:
    if not isinstance(generated, dict) or not isinstance(generated.get("items"), list):
        raise ValueError("La salida generada no contiene items válidos")

    expected = [int(v["verse_number"]) for v in verses]
    items = generated["items"]
    got = [item.get("verse_number") for item in items if isinstance(item, dict)]
    if got != expected:
        raise ValueError(f"Se esperaban versículos {expected}; se recibieron {got}")

    seen_questions: set[str] = set()
    output_items = []
    for verse, item in zip(verses, items):
        if not isinstance(item, dict):
            raise ValueError("Elemento generado inválido")
        question = str(item.get("question", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        options = item.get("options")
        correct = str(item.get("correct_answer", "")).strip()
        difficulty = str(item.get("difficulty", "")).strip()
        category = str(item.get("category", "")).strip()

        if not question or not explanation or not category:
            raise ValueError(f"Faltan campos en versículo {verse['verse_number']}")
        if re.search(r"\b\d+\s*:\s*\d+\b", question):
            raise ValueError(f"La pregunta del versículo {verse['verse_number']} contiene cita bíblica")
        qnorm = normalize_text(question)
        if qnorm in seen_questions:
            raise ValueError(f"Pregunta duplicada en versículo {verse['verse_number']}")
        seen_questions.add(qnorm)
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"El versículo {verse['verse_number']} no tiene 4 alternativas")
        options = [str(x).strip() for x in options]
        if len({normalize_text(x) for x in options}) != 4:
            raise ValueError(f"Alternativas duplicadas en versículo {verse['verse_number']}")
        if correct not in options:
            raise ValueError(f"Respuesta correcta fuera de alternativas en versículo {verse['verse_number']}")
        if difficulty not in {"easy", "medium", "hard"}:
            raise ValueError(f"Dificultad inválida en versículo {verse['verse_number']}")

        # Evita persistir el versículo completo de RVR1960 como pregunta o explicación.
        source_norm = normalize_text(str(verse["text"]))
        if len(source_norm) >= 40 and (source_norm in normalize_text(question) or source_norm in normalize_text(explanation)):
            raise ValueError(f"Se detectó copia íntegra del texto fuente en versículo {verse['verse_number']}")

        number = int(verse["verse_number"])
        output_items.append({
            "id": f"{book.upper().replace(' ', '_')}_{chapter:03d}_{number:03d}",
            "verse_number": number,
            "reference": f"{book} {chapter}:{number}",
            "question": question,
            "options": options,
            "correct_answer": correct,
            "explanation": explanation,
            "difficulty": difficulty,
            "category": category,
            "status": "generated_pending_review",
            "source_version": "RVR1960",
            "source_text_persisted": False,
        })

    return {
        "schema_version": "quizbible-generated-bank-v1",
        "source": "ApiBiblia",
        "source_version": "RVR1960",
        "book": book,
        "chapter": chapter,
        "generated_count": len(output_items),
        "requires_human_review": True,
        "items": output_items,
    }


def main() -> int:
    args = parse_args()
    if args.chapter < 1:
        raise SystemExit("El capítulo debe ser mayor o igual a 1")
    if args.version.upper() != "RVR1960":
        raise SystemExit("Este generador está restringido a RVR1960")

    bible_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not bible_key:
        raise SystemExit("Falta APIBIBLIA_API_KEY")
    if not gemini_key:
        raise SystemExit("Falta GEMINI_API_KEY")

    book = args.book.strip()
    reference = f"{book} {args.chapter}"
    query = urllib.parse.urlencode({"ref": reference, "version": "RVR1960"})

    print(f"1/3 Obteniendo {reference} temporalmente desde ApiBiblia...")
    try:
        payload = api_get(f"{PASSAGE_URL}?{query}", bible_key)
    except Exception as exc:
        print(f"Error consultando ApiBiblia: {exc}", file=sys.stderr)
        return 10

    verses = extract_verses(payload)
    if not verses:
        print("No se detectaron versículos", file=sys.stderr)
        return 11

    source_for_prompt = [{"verse_number": int(v["verse_number"]), "text": v["text"]} for v in verses]
    prompt = (
        "Actúa como editor de un banco de preguntas bíblicas para Quiz Bible. "
        "A partir del capítulo RVR1960 proporcionado, genera exactamente una pregunta por cada versículo recibido. "
        "Reglas obligatorias: la pregunta NO debe contener libro, capítulo ni número de versículo; debe ser clara y responderse "
        "por comprensión del contenido; crea exactamente 4 alternativas plausibles y una sola correcta; correct_answer debe coincidir "
        "literalmente con una de las 4 opciones; la explicación debe justificar con suficiente detalle por qué la respuesta es correcta "
        "sin copiar íntegramente el versículo; evita preguntas triviales basadas únicamente en recordar una palabra; evita preguntas repetidas; "
        "difficulty debe ser easy, medium o hard; category debe ser una categoría breve del contenido. "
        "No incluyas el texto bíblico fuente ni un campo verse_text en la respuesta. "
        f"Libro para contexto: {book}. Capítulo: {args.chapter}. Versículos temporales:\n"
        + json.dumps(source_for_prompt, ensure_ascii=False)
    )

    print(f"2/3 Generando preguntas con {args.model}...")
    try:
        generated = gemini_generate(args.model, gemini_key, prompt)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Gemini HTTP {exc.code}: {body[:600]}", file=sys.stderr)
        return 20
    except Exception as exc:
        print(f"Error generando preguntas: {exc}", file=sys.stderr)
        return 21

    print("3/3 Validando estructura y eliminando texto fuente...")
    try:
        bank = validate_generated(book, args.chapter, verses, generated)
    except Exception as exc:
        print(f"Validación fallida: {exc}", file=sys.stderr)
        return 30

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for verse in verses:
        verse["text"] = ""
    for item in source_for_prompt:
        item["text"] = ""
    del source_for_prompt
    del verses
    del payload
    del generated

    print(f"Banco generado: {bank['generated_count']} preguntas. Texto RVR1960 no persistido. Revisión humana requerida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
