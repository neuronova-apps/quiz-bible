#!/usr/bin/env python3
"""Audita preguntas existentes contra RVR1960 obtenida temporalmente desde ApiBiblia.

No persiste ni imprime el texto bíblico. Solo genera resultados derivados:
existencia de referencia, soporte de términos, conflictos con distractores y
huella SHA-256 del pasaje utilizado.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Any

from extractor import PASSAGE_URL, api_get, extract_verses

STOPWORDS = {
    "a", "al", "de", "del", "el", "la", "las", "los", "que", "su", "sus",
    "un", "una", "unos", "unas", "y", "o", "en", "por", "para", "con",
    "segun", "como", "fue", "era", "es", "se", "lo", "le", "les",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", default="build/audit-result.json")
    return p.parse_args()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value.casefold())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^a-z0-9ñ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def significant_tokens(value: str) -> list[str]:
    return [t for t in normalize(value).split() if len(t) >= 3 and t not in STOPWORDS]


def terms_missing(text_norm: str, terms: list[str]) -> list[str]:
    missing: list[str] = []
    for term in terms:
        term_norm = normalize(str(term))
        if term_norm and term_norm not in text_norm:
            missing.append(str(term))
    return missing


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Falta APIBIBLIA_API_KEY")

    spec = json.loads(Path(args.input).read_text(encoding="utf-8"))
    book = str(spec["book"]).strip()
    chapter = int(spec["chapter"])
    version = str(spec.get("version", "RVR1960")).strip().upper()
    if version != "RVR1960":
        raise SystemExit("Este auditor está restringido a RVR1960")

    query = urllib.parse.urlencode({"ref": f"{book} {chapter}", "version": version})
    status, payload = api_get(f"{PASSAGE_URL}?{query}", api_key)
    if status != 200:
        raise SystemExit(f"ApiBiblia devolvió HTTP {status}")

    verses = extract_verses(payload)
    verse_map = {int(v["verse_number"]): str(v["text"]) for v in verses}
    results: list[dict[str, Any]] = []

    for item in spec.get("questions", []):
        start = int(item["verse_start"])
        end = int(item.get("verse_end", start))
        required_numbers = list(range(start, end + 1))
        reference_exists = all(n in verse_map for n in required_numbers)
        passage = " ".join(verse_map.get(n, "") for n in required_numbers)
        passage_norm = normalize(passage)

        support_missing = terms_missing(passage_norm, list(item.get("support_terms", [])))
        explanation_missing = terms_missing(passage_norm, list(item.get("explanation_terms", [])))

        distractor_conflicts: list[str] = []
        for distractor in item.get("distractors", []):
            tokens = significant_tokens(str(distractor))
            if tokens and all(token in passage_norm for token in tokens):
                distractor_conflicts.append(str(distractor))

        direct_support = reference_exists and not support_missing
        explanation_supported = reference_exists and not explanation_missing
        unique_answer_signal = not distractor_conflicts
        verified = direct_support and explanation_supported and unique_answer_signal

        results.append({
            "id": item["id"],
            "reference": f"{book} {chapter}:{start}" + (f"-{end}" if end != start else ""),
            "reference_exists": reference_exists,
            "direct_answer_support": direct_support,
            "missing_support_terms": support_missing,
            "explanation_claims_supported": explanation_supported,
            "missing_explanation_terms": explanation_missing,
            "distractor_conflicts": distractor_conflicts,
            "unique_answer_signal": unique_answer_signal,
            "passage_sha256": hashlib.sha256(passage.encode("utf-8")).hexdigest() if reference_exists else None,
            "verdict": "VERIFICADO_DIRECTO" if verified else "REQUIERE_REVISION",
            "source_text_persisted": False,
        })

    out = {
        "schema_version": "quizbible-rvr1960-audit-v1",
        "source": "ApiBiblia API",
        "version": version,
        "book": book,
        "chapter": chapter,
        "api_http_status": status,
        "chapter_verse_count": len(verse_map),
        "questions_audited": len(results),
        "verified_count": sum(r["verdict"] == "VERIFICADO_DIRECTO" for r in results),
        "review_required_count": sum(r["verdict"] != "VERIFICADO_DIRECTO" for r in results),
        "source_text_persisted": False,
        "results": results,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Borrado explícito de estructuras que contienen RVR1960 antes de finalizar.
    for verse in verses:
        verse["text"] = ""
    verse_map.clear()
    del payload
    del verses

    print("Auditoría completada")
    print("book:", book)
    print("chapter:", chapter)
    print("questions_audited:", out["questions_audited"])
    print("verified_count:", out["verified_count"])
    print("review_required_count:", out["review_required_count"])
    print("source_text_persisted:", out["source_text_persisted"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
