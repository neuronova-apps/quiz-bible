#!/usr/bin/env python3
"""Extractor temporal para el banco de Quiz Bible.

Primero valida la autenticación contra el endpoint oficial de versículo
(JHN 3:16, RVR1960). Solo si esa prueba responde correctamente, consulta
el capítulo solicitado. El texto bíblico se mantiene únicamente en memoria
y el reporte final conserva solo metadatos técnicos.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

VERSE_TEST_URL = "https://api.apibiblia.com/v1/verses/JHN/3/16?version=RVR1960"
PASSAGE_URL = "https://api.apibiblia.com/v1/passage"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book", required=True, help="Libro o nombre aceptado por ApiBiblia")
    parser.add_argument("--chapter", required=True, type=int, help="Número de capítulo")
    parser.add_argument("--version", default="RVR1960")
    parser.add_argument("--output", default="build/extraction-report.json")
    return parser.parse_args()


def count_text_nodes(value) -> tuple[int, int]:
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
            "User-Agent": "QuizBible-Extractor/1.0",
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
            # Limitar el diagnóstico para no volcar respuestas extensas en Actions.
            print(f"Respuesta del servidor: {body[:500]}", file=sys.stderr)
        raise


def main() -> int:
    args = parse_args()
    if args.chapter < 1:
        raise SystemExit("El capítulo debe ser mayor o igual a 1.")
    if args.version.upper() != "RVR1960":
        raise SystemExit("Este flujo está restringido a RVR1960.")

    api_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Falta el secreto APIBIBLIA_API_KEY.")

    print("Paso 1/2: validando API Key con JHN 3:16 (RVR1960)...")
    try:
        auth_status, auth_payload = api_get(VERSE_TEST_URL, api_key)
    except urllib.error.HTTPError as exc:
        print(
            f"La prueba oficial JHN 3:16 falló con HTTP {exc.code}. "
            "Esto indica un problema de autenticación/autorización de la API Key o de la cuenta, no del capítulo solicitado.",
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

    reference = f"{args.book.strip()} {args.chapter}"
    query = urllib.parse.urlencode({"ref": reference, "version": "RVR1960"})
    passage_url = f"{PASSAGE_URL}?{query}"

    print(f"Paso 2/2: consultando capítulo {reference}...")
    try:
        chapter_status, chapter_payload = api_get(passage_url, api_key)
    except urllib.error.HTTPError as exc:
        print(
            f"La API Key sí fue aceptada en JHN 3:16, pero el capítulo falló con HTTP {exc.code}. "
            "El problema está entonces en el endpoint de pasaje, la referencia o el permiso para esa operación.",
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

    auth_nodes, auth_chars = count_text_nodes(auth_payload)
    chapter_nodes, chapter_chars = count_text_nodes(chapter_payload)

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
        "scripture_text_persisted": False,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "next_stage": "review_then_question_generation",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    del auth_payload
    del chapter_payload
    print(f"Validación completada para {reference}. Texto bíblico no persistido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
