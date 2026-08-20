#!/usr/bin/env python3
"""Extractor temporal para el banco de Quiz Bible.

Obtiene un capítulo de ApiBiblia en memoria, valida la respuesta y genera
únicamente un reporte técnico sin conservar el texto bíblico.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://api.apibiblia.com/v1/passage"


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


def main() -> int:
    args = parse_args()
    if args.chapter < 1:
        raise SystemExit("El capítulo debe ser mayor o igual a 1.")
    if args.version.upper() != "RVR1960":
        raise SystemExit("Este flujo está restringido a RVR1960.")

    api_key = os.environ.get("APIBIBLIA_API_KEY")
    if not api_key:
        raise SystemExit("Falta el secreto APIBIBLIA_API_KEY.")

    reference = f"{args.book.strip()} {args.chapter}"
    query = urllib.parse.urlencode({"ref": reference, "version": "RVR1960"})
    request = urllib.request.Request(
        f"{BASE_URL}?{query}",
        headers={"X-API-Key": api_key, "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
            http_status = response.status
    except Exception as exc:
        print(f"Error consultando ApiBiblia: {exc}", file=sys.stderr)
        return 2

    success = payload.get("success", True) if isinstance(payload, dict) else True
    if not success:
        print("ApiBiblia devolvió una respuesta no exitosa.", file=sys.stderr)
        return 3

    text_nodes, character_count = count_text_nodes(payload)

    report = {
        "source": "ApiBiblia",
        "reference_requested": reference,
        "version_requested": "RVR1960",
        "http_status": http_status,
        "response_valid": True,
        "text_nodes_detected": text_nodes,
        "character_count_detected": character_count,
        "scripture_text_persisted": False,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "next_stage": "review_then_question_generation",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # La variable payload queda solo en memoria y desaparece al finalizar el proceso.
    del payload
    print(f"Validación completada para {reference}. Texto bíblico no persistido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
