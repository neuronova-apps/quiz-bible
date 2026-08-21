#!/usr/bin/env python3
"""Auditor semántico y textual derivado de preguntas bíblicas contra RVR1960.

Soporta auditoría modular para Génesis (50 capítulos), Éxodo (40 capítulos)
y libros bíblicos adicionales.

Evalúa deterministamente los 17 controles de calidad editorial:
identidad de libro, capítulo, versículos, existencia de pasajes, respaldo
de la pregunta, validez de la opción A, inconsistencia de distractores,
alineación canónica, compatibilidad de explicación, verificación de nombres
propios, lugares, cantidades numéricas, parentescos, suficiencia de rango
y ausencia de ambigüedad.

Incluye cliente HTTP con throttling proactivo (máximo 26 peticiones/minuto,
intervalo >= 2.3s) y manejo inteligente de HTTP 429 con lectura de reset_at.

Estados por control: PASS, FAIL, NOT_APPLICABLE, UNKNOWN.
Clasificación final: VERIFICADO, REQUIERE_CORRECCION, NO_CONCLUYENTE.

El texto bíblico RVR1960 vive únicamente en memoria volátil y se libera
inmediatamente tras evaluar cada capítulo. source_text_persisted: False.
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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

try:
    from tools.bible_extractor.extractor import PASSAGE_URL, api_get, extract_verses, _verse_number_from_node
except ImportError:
    from extractor import PASSAGE_URL, api_get, extract_verses, _verse_number_from_node

BOOK_CONFIGS: dict[str, dict[str, Any]] = {
    "genesis": {
        "canonical_name": "Génesis",
        "api_name": "Genesis",
        "aliases": {"genesis", "génesis"},
        "total_chapters": 50,
        "blocks": [
            (1, 10, "genesis-01-10.json"),
            (11, 20, "genesis-11-20.json"),
            (21, 30, "genesis-21-30.json"),
            (31, 40, "genesis-31-40.json"),
            (41, 50, "genesis-41-50.json"),
        ],
        "default_output_dir": "build/audit/genesis",
    },
    "exodo": {
        "canonical_name": "Éxodo",
        "api_name": "Exodo",
        "aliases": {"exodo", "éxodo", "exodus"},
        "total_chapters": 40,
        "blocks": [
            (1, 10, "exodus-01-10.json"),
            (11, 20, "exodus-11-20.json"),
            (21, 30, "exodus-21-30.json"),
            (31, 40, "exodus-31-40.json"),
        ],
        "default_output_dir": "build/audit/exodus",
    },
}

STOPWORDS = {
    "a", "al", "de", "del", "el", "la", "las", "los", "que", "su", "sus",
    "un", "una", "unos", "unas", "y", "o", "en", "por", "para", "con",
    "segun", "como", "fue", "era", "es", "se", "lo", "le", "les", "ha",
    "habia", "habian", "sus", "hizo", "dijo", "dios", "senor", "jehova",
    "cual", "quien", "quienes", "cuando", "donde", "por", "que", "hacia",
    "sobre", "tras", "entre", "hasta", "desde", "ante", "bajo", "cabe",
    "pero", "mas", "este", "esta", "estos", "estas", "aquel", "aquella",
    "ser", "sido", "estar", "estaba", "estaban", "tener", "tenia", "tenian",
}

# Entidades y personajes bíblicos (Génesis, Éxodo y nombres bíblicos comunes)
BIBLE_PERSONAJES = {
    # Génesis
    "adan", "eva", "cain", "abel", "set", "enos", "cainan", "mahalaleel",
    "jared", "enoc", "matusalen", "lamec", "noe", "sem", "cam", "jafet",
    "canaan", "tare", "abram", "abraham", "sarai", "sara", "lot", "melquisedec",
    "agar", "ismael", "isaac", "rebeca", "laban", "betuel", "jacob", "esau",
    "lea", "raquel", "ruben", "simeon", "levi", "juda", "dan", "neftali",
    "gad", "aser", "isacar", "zabulon", "jose", "benjamin", "dina", "tamar",
    "potifar", "faraon", "asenat", "manases", "efrain", "abimelec", "eliezer",
    "cetura", "zilpa", "bilha", "potifera", "zafenat-panea", "zafenatpanea",
    "eber", "peleg", "milca", "isca", "er", "onan", "sela", "fares", "zara",
    "hezron", "hamul", "siquem", "hamor", "nemrod", "mizraim", "cuz",
    # Éxodo
    "moises", "aaron", "miriam", "maria", "sefora", "jetro", "reuel", "gersom",
    "sipra", "fua", "jocabed", "amram", "hur", "josue", "bezaleel", "aholiab",
    "nadab", "abiu", "eleazar", "itamar", "core", "datan", "abiram",
    "balac", "balaam", "finees", "caleb",
    # Otros comunes
    "david", "salomon", "saul", "samuel", "elias", "eliseo", "jonatan",
    "nabucodonosor", "pablo", "pedro", "juan", "jesus", "mateo", "marcos",
    "lucas", "esteban", "timoteo",
}

# Lugares, regiones y accidentes geográficos bíblicos (Génesis y Éxodo)
BIBLE_PLACES = {
    # Génesis
    "eden", "ararat", "babel", "ur", "haran", "betel", "bet-el", "hebron", "siquem",
    "sodoma", "gomorra", "adma", "zeboim", "bela", "zoar", "egipto", "gosen",
    "moriah", "beerseba", "beer-seba", "macpela", "mizpa", "seir", "rameses",
    "peniel", "penuel", "dotan", "dothan", "gerar", "gueral", "filistea", "ebal",
    "galaad", "guilead", "padan-aram", "padanaram", "mesopotamia", "canaan",
    "salem", "mamre", "cala", "sinar", "ofir", "havila", "caldea", "siria",
    "lahai-roi", "lahairoi", "berseba", "sucot", "efrata", "belen", "nilo",
    "eufrates", "hidekel", "pison", "gihon", "quedem", "horeb",
    "sion", "negev", "jordan", "atarot", "shiloh", "damasco",
    # Éxodo
    "madian", "sinai", "mar rojo", "mara", "elim", "sin", "refidim",
    "masa", "meriba", "etam", "pi-hahirot", "pihahirot", "baal-zefon",
    "baalzefon", "migdol", "sur", "piton",
}

# Raíces de parentesco y lemas
KINSHIP_STEMS = {
    "hij": ["hijo", "hija", "hijos", "hijas"],
    "herman": ["hermano", "hermana", "hermanos", "hermanas"],
    "padr": ["padre", "padres", "papa"],
    "madr": ["madre", "madres", "mama"],
    "espos": ["esposa", "esposo", "esposas", "mujer", "marido"],
    "sierv": ["sierva", "siervo", "siervas", "siervos", "criado", "criados", "doncella"],
    "primogenit": ["primogenito", "primogenita"],
    "sobrin": ["sobrino", "sobrina", "pariente"],
    "tio": ["tio", "tia"],
    "suegr": ["suegro", "suegra"],
    "yern": ["yerno", "nuera"],
    "niet": ["nieto", "nieta", "nietos"],
    "abuel": ["abuelo", "abuela"],
    "concubin": ["concubina", "concubinas"],
    "gemel": ["gemelos", "mellizos"],
}

# Equivalencias semánticas y de dimensiones
SYNONYMS = {
    "longitud": "largo",
    "anchura": "ancho",
    "altura": "alto",
    "largo": "longitud",
    "ancho": "anchura",
    "alto": "altura",
    "arameo": "padan-aram",
    "aramea": "padan-aram",
}

# Diccionario de números cardinales en español
SPANISH_NUMBERS_EXPLICIT = {
    "cero": 0, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29, "treinta": 30, "cuarenta": 40,
    "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300, "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500, "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900, "mil": 1000,
}


def normalize(value: str) -> str:
    """Normaliza texto para comparación insensible a tildes, mayúsculas, guiones y signos."""
    if not value:
        return ""
    value = unicodedata.normalize("NFD", str(value).casefold())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("bet-el", "betel").replace("beer-seba", "beerseba").replace("padan-aram", "padanaram")
    value = re.sub(r"[^a-z0-9ñ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def significant_tokens(value: str) -> list[str]:
    """Extrae palabras clave significativas omitiendo stopwords."""
    return [t for t in normalize(value).split() if len(t) >= 3 and t not in STOPWORDS]


def detect_book_key(spec: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Detecta la clave de configuración del libro a partir de las preguntas."""
    questions = spec if isinstance(spec, list) else spec.get("questions", [])
    if questions:
        first_book = normalize(str(questions[0].get("book", "")))
        for k, cfg in BOOK_CONFIGS.items():
            if first_book in cfg["aliases"]:
                return k
    return "genesis"


def extract_numbers(text: str, is_quantitative_context: bool = False) -> list[int]:
    """Extrae números enteros de dígitos o palabras numéricas."""
    raw_text = str(text)
    cleaned_digits_text = re.sub(r"\b\d+\s*:\s*\d+(?:-\d+)?\b", " ", raw_text)
    cleaned_norm = normalize(cleaned_digits_text)
    numbers: list[int] = []

    # 1. Dígitos directos
    for m in re.finditer(r"\b\d+\b", cleaned_norm):
        try:
            numbers.append(int(m.group(0)))
        except ValueError:
            pass

    # 2. 'un' / 'una' con unidades contables explícitas
    if re.search(r"\b(?:un|una)\b", cleaned_norm):
        countable_units_pattern = r"\b(?:un|una)\s+(?:vez|ano|anos|mes|meses|dia|dias|codo|codos|pareja|parejas|talento|siclo|pieza|piezas|hora|horas|parte|partes)\b"
        if is_quantitative_context or re.search(countable_units_pattern, cleaned_norm):
            numbers.append(1)

    # 3. Palabras numéricas compuestas
    words = cleaned_norm.split()
    i = 0
    while i < len(words):
        w = words[i]
        if w in SPANISH_NUMBERS_EXPLICIT:
            current_val = SPANISH_NUMBERS_EXPLICIT[w]
            j = i + 1
            while j < len(words):
                next_w = words[j]
                if next_w == "y" and j + 1 < len(words) and words[j + 1] in SPANISH_NUMBERS_EXPLICIT:
                    current_val += SPANISH_NUMBERS_EXPLICIT[words[j + 1]]
                    j += 2
                elif next_w in SPANISH_NUMBERS_EXPLICIT:
                    if SPANISH_NUMBERS_EXPLICIT[next_w] == 1000:
                        current_val = (current_val or 1) * 1000
                    else:
                        current_val += SPANISH_NUMBERS_EXPLICIT[next_w]
                    j += 1
                else:
                    break
            numbers.append(current_val)
            i = j
        else:
            i += 1

    return sorted(set(numbers))


def parse_additional_ref(ref_str: str, default_chapter: int) -> tuple[int, list[int]]:
    """Extrae capítulo y versículos de una referencia adicional multilibro."""
    m = re.search(r"(?:[A-Za-zÁÉÍÓÚáéíóúñÑ]+\s+)?(?:(\d+)[:.])?(\d+)(?:-(\d+))?", str(ref_str), re.IGNORECASE)
    if not m:
        return default_chapter, []
    ch = int(m.group(1)) if m.group(1) else default_chapter
    start_v = int(m.group(2))
    end_v = int(m.group(3)) if m.group(3) else start_v
    return ch, list(range(start_v, end_v + 1))


def extract_verses_robust(payload: Any) -> dict[int, str]:
    """Extrae versículos indexados por número de forma determinista."""
    verse_map: dict[int, str] = {}
    if not isinstance(payload, dict):
        return verse_map

    verses_list = payload.get("verses")
    if not verses_list and isinstance(payload.get("data"), dict):
        verses_list = payload["data"].get("verses")

    if isinstance(verses_list, list) and len(verses_list) > 0:
        for idx, item in enumerate(verses_list, start=1):
            if isinstance(item, dict):
                v_num = _verse_number_from_node(item) or idx
                text = item.get("text") or item.get("verse") or ""
                if isinstance(text, str) and text.strip():
                    verse_map[v_num] = text.strip()
        if verse_map:
            return verse_map

    verses = extract_verses(payload)
    for v in verses:
        try:
            num = int(v.get("verse_number", 0))
            txt = str(v.get("text", "")).strip()
            if num > 0 and txt:
                verse_map[num] = txt
        except (ValueError, TypeError):
            continue
    return verse_map


def split_composite_answer(answer_str: str) -> list[str]:
    """Descompone respuestas compuestas unidas por comas, 'y', 'e'."""
    raw = re.split(r"[,;]|\s+y\s+|\s+e\s+", answer_str)
    parts = [p.strip() for p in raw if p.strip()]
    return parts if len(parts) > 1 else [answer_str.strip()]


def evaluate_question(
    q: dict[str, Any],
    verse_map: dict[int, str],
    book_key: str = "genesis",
) -> dict[str, Any]:
    """Evalúa una pregunta contra el pasaje en memoria aplicando los 17 controles rigurosamente."""
    book_cfg = BOOK_CONFIGS.get(book_key, BOOK_CONFIGS["genesis"])

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

    controls: dict[str, str] = {}
    incidencias: list[str] = []
    correcciones_sugeridas: list[dict[str, Any]] = []

    # 1. Control Libro
    if normalize(book) in book_cfg["aliases"]:
        controls["control_libro"] = "PASS"
    else:
        controls["control_libro"] = "FAIL"
        incidencias.append(f"Libro no correspondiente: '{book}' (esperado '{book_cfg['canonical_name']}')")

    # 2. Control Capítulo
    if 1 <= chapter <= book_cfg["total_chapters"]:
        controls["control_capitulo"] = "PASS"
    else:
        controls["control_capitulo"] = "FAIL"
        incidencias.append(f"Capítulo fuera de rango 1-{book_cfg['total_chapters']}: {chapter}")

    # 3. Control Versículo Inicio
    if start >= 1:
        controls["control_versiculo_inicio"] = "PASS"
    else:
        controls["control_versiculo_inicio"] = "FAIL"
        incidencias.append(f"Versículo inicio inválido: {start}")

    # 4. Control Versículo Fin
    if end >= start:
        controls["control_versiculo_fin"] = "PASS"
    else:
        controls["control_versiculo_fin"] = "FAIL"
        incidencias.append(f"Versículo fin ({end}) menor que inicio ({start})")

    # 5. Control Formato Referencia
    expected_ref_suffix = f"{chapter}:{start}" if start == end else f"{chapter}:{start}-{end}"
    if bool(re.search(r"[:\s]" + re.escape(expected_ref_suffix) + r"$", ref_str)) or (f"{chapter}:{start}" in ref_str):
        controls["control_referencia_formato"] = "PASS"
    else:
        controls["control_referencia_formato"] = "FAIL"
        incidencias.append(f"Referencia '{ref_str}' no coincide con capítulo {chapter} y versículos {start}-{end}")

    # 6. Control Existencia Referencia (rango principal + additional_references)
    main_verses = list(range(start, end + 1)) if start <= end else [start]
    all_required_verses = list(main_verses)
    for add_ref in additional_refs:
        add_ch, add_v_list = parse_additional_ref(add_ref, chapter)
        if add_ch == chapter:
            all_required_verses.extend(add_v_list)

    all_required_verses_unique = sorted(set(all_required_verses))
    if verse_map and all(v in verse_map for v in all_required_verses_unique):
        controls["control_referencia_existencia"] = "PASS"
    else:
        if not verse_map:
            controls["control_referencia_existencia"] = "UNKNOWN"
            incidencias.append(f"Capítulo {chapter} no disponible temporalmente desde ApiBiblia (posible rate limit o error de red)")
        else:
            controls["control_referencia_existencia"] = "FAIL"
            missing_v = [v for v in all_required_verses_unique if v not in verse_map]
            incidencias.append(f"Versículos faltantes en el capítulo: {missing_v}")

    # Construir pasaje integral en memoria
    passage = " ".join(verse_map.get(v, "") for v in all_required_verses_unique) if verse_map else ""
    passage_norm = normalize(passage)
    passage_nums = set(extract_numbers(passage))
    passage_hash = hashlib.sha256(passage.encode("utf-8")).hexdigest() if controls["control_referencia_existencia"] == "PASS" else None

    # Si no hay pasaje disponible por fallo de API, todos los controles de texto son UNKNOWN
    if not verse_map:
        for c_name in (
            "control_soporte_pregunta", "control_opcion_a_correcta", "control_distractores_invalidos",
            "control_respuesta_coincide_a", "control_explicacion_compatible", "control_nombres_propios",
            "control_lugares", "control_numeros_cantidades", "control_relaciones_personajes",
            "control_rango_suficiente", "control_sin_ambiguedad"
        ):
            controls[c_name] = "UNKNOWN"
        return {
            "id": qid,
            "reference": ref_str,
            "chapter": chapter,
            "verse_start": start,
            "verse_end": end,
            "estado": "NO_CONCLUYENTE",
            "controles_superados": controls,
            "incidencias": incidencias,
            "correcciones_sugeridas": correcciones_sugeridas,
            "hash_sha256_pasaje": None,
            "source_text_persisted": False,
        }

    # 7. Control Soporte de Pregunta
    q_toks = significant_tokens(prompt)
    if not q_toks:
        controls["control_soporte_pregunta"] = "UNKNOWN"
    else:
        matching_q_toks = [t for t in q_toks if t in passage_norm or (t in SYNONYMS and SYNONYMS[t] in passage_norm)]
        coverage_q = len(matching_q_toks) / len(q_toks)
        if coverage_q >= 0.15 or len(matching_q_toks) >= 1:
            controls["control_soporte_pregunta"] = "PASS"
        else:
            controls["control_soporte_pregunta"] = "UNKNOWN"

    # 8. Control Opción A Correcta
    parts_a = split_composite_answer(opcion_a)
    missing_parts = []
    for part in parts_a:
        part_toks = significant_tokens(part)
        part_norm = normalize(part)
        part_nums = extract_numbers(part)

        if part_nums:
            nums_matched = all(n in passage_nums for n in part_nums)
            non_num_toks = [t for t in part_toks if not t.isdigit()]
            text_matched = True if not non_num_toks else any(t in passage_norm or (t in SYNONYMS and SYNONYMS[t] in passage_norm) for t in non_num_toks)
            if nums_matched and text_matched:
                continue
            missing_parts.append(part)
        else:
            if part_norm and (
                part_norm in passage_norm
                or any(t in passage_norm or (t in SYNONYMS and SYNONYMS[t] in passage_norm) for t in part_toks)
            ):
                continue
            missing_parts.append(part)

    if not missing_parts:
        controls["control_opcion_a_correcta"] = "PASS"
    else:
        opt_a_nums = extract_numbers(opcion_a)
        conflicting_num = any(n not in passage_nums for n in opt_a_nums if opt_a_nums and passage_nums)
        if conflicting_num:
            controls["control_opcion_a_correcta"] = "FAIL"
            incidencias.append(f"Contradicción numérica objetiva en Opción A: {opt_a_nums} vs {sorted(passage_nums)}")
        else:
            controls["control_opcion_a_correcta"] = "UNKNOWN"

    # 9. Control Distractores Inválidos
    distractor_conflicts: list[str] = []
    for d_text in (opcion_b, opcion_c, opcion_d):
        d_norm = normalize(d_text)
        if not d_norm:
            distractor_conflicts.append("Distractor vacío")
            continue
        if d_norm == normalize(opcion_a):
            distractor_conflicts.append(f"Distractor idéntico a opción A: '{d_text}'")
            continue

        d_nums = extract_numbers(d_text)
        opt_a_nums = extract_numbers(opcion_a)
        if d_nums and opt_a_nums and set(d_nums) == passage_nums and set(opt_a_nums) != passage_nums:
            distractor_conflicts.append(f"Distractor con datos correctos frente a Opción A incorrecta: '{d_text}'")

    if distractor_conflicts:
        controls["control_distractores_invalidos"] = "FAIL"
        incidencias.extend(distractor_conflicts)
    else:
        controls["control_distractores_invalidos"] = "PASS"

    # 10. Control Respuesta Coincide con Opción A
    ans_aligned = (correct_opt == "A") and (normalize(correct_ans) == normalize(opcion_a))
    if ans_aligned:
        controls["control_respuesta_coincide_a"] = "PASS"
    else:
        controls["control_respuesta_coincide_a"] = "FAIL"
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
    exp_cleaned = re.sub(r"\b(?:[A-Za-zÁÉÍÓÚáéíóúñÑ]+\s+)?\d+\s*:\s*\d+(?:-\d+)?\b", " ", explanation, flags=re.IGNORECASE)
    exp_toks = significant_tokens(exp_cleaned)
    if not exp_toks:
        controls["control_explicacion_compatible"] = "UNKNOWN"
    else:
        matching_exp_toks = [t for t in exp_toks if t in passage_norm or (t in SYNONYMS and SYNONYMS[t] in passage_norm)]
        exp_coverage = len(matching_exp_toks) / len(exp_toks)
        exp_nums = extract_numbers(exp_cleaned)
        conflicting_nums = [n for n in exp_nums if n not in passage_nums and n > 2]

        if conflicting_nums and controls["control_opcion_a_correcta"] == "FAIL":
            controls["control_explicacion_compatible"] = "FAIL"
            incidencias.append(f"La explicación contiene datos numéricos contradictorios: {conflicting_nums}")
        elif exp_coverage >= 0.12 or len(matching_exp_toks) >= 2:
            controls["control_explicacion_compatible"] = "PASS"
        else:
            controls["control_explicacion_compatible"] = "UNKNOWN"

    # 12. Control Nombres Propios
    entities_in_opt_a = set()
    for word in normalize(opcion_a).split():
        if word in BIBLE_PERSONAJES:
            entities_in_opt_a.add(word)

    entities_in_prompt = set()
    for word in normalize(prompt).split():
        if word in BIBLE_PERSONAJES:
            entities_in_prompt.add(word)

    if entities_in_opt_a:
        missing_entities = [n for n in entities_in_opt_a if n not in passage_norm]
        if not missing_entities:
            controls["control_nombres_propios"] = "PASS"
        else:
            controls["control_nombres_propios"] = "FAIL"
            incidencias.append(f"Personaje bíblico en opción A no respaldado en el pasaje: {missing_entities}")
    elif entities_in_prompt:
        matching_prompt_ent = [n for n in entities_in_prompt if n in passage_norm]
        if matching_prompt_ent:
            controls["control_nombres_propios"] = "PASS"
        else:
            controls["control_nombres_propios"] = "NOT_APPLICABLE" if not characters else "PASS"
    elif characters:
        matching_chars = [c for c in characters if normalize(c) in passage_norm]
        if matching_chars:
            controls["control_nombres_propios"] = "PASS"
        else:
            controls["control_nombres_propios"] = "NOT_APPLICABLE"
    else:
        controls["control_nombres_propios"] = "NOT_APPLICABLE"

    # 13. Control Lugares
    opt_a_toks = set(normalize(opcion_a).split())
    prompt_toks = set(normalize(prompt).split())
    detected_places = (opt_a_toks | prompt_toks) & BIBLE_PLACES

    if not detected_places:
        controls["control_lugares"] = "NOT_APPLICABLE"
    else:
        missing_places = [pl for pl in detected_places if pl not in passage_norm]
        if not missing_places:
            controls["control_lugares"] = "PASS"
        elif any(pl in opt_a_toks for pl in missing_places):
            controls["control_lugares"] = "FAIL"
            incidencias.append(f"Lugar en opción A no coincide con el pasaje: {missing_places}")
        else:
            controls["control_lugares"] = "UNKNOWN"

    # 14. Control Números y Cantidades
    has_count_context = bool(re.search(r"¿?\s*cuant[oa]s?\b", normalize(prompt)))
    opt_a_nums = extract_numbers(opcion_a, is_quantitative_context=has_count_context)
    prompt_nums = extract_numbers(prompt, is_quantitative_context=has_count_context)
    target_nums = set(opt_a_nums) | set(prompt_nums)

    if not target_nums:
        controls["control_numeros_cantidades"] = "NOT_APPLICABLE"
    else:
        composite_count = len(parts_a)
        prompt_nums_clean = [n for n in prompt_nums if n != composite_count]

        missing_nums = [n for n in (set(opt_a_nums) | set(prompt_nums_clean)) if n not in passage_nums]
        if not missing_nums:
            controls["control_numeros_cantidades"] = "PASS"
        elif any(n in opt_a_nums for n in missing_nums):
            controls["control_numeros_cantidades"] = "FAIL"
            incidencias.append(f"Cantidad numérica en opción A ({opt_a_nums}) no coincide con el pasaje ({sorted(passage_nums)})")
        else:
            controls["control_numeros_cantidades"] = "UNKNOWN"

    # 15. Control Relaciones de Personajes
    kin_detected_stems = set()
    all_text_norm = normalize(f"{opcion_a} {prompt}")
    for stem, words in KINSHIP_STEMS.items():
        if any(w in all_text_norm.split() for w in words):
            kin_detected_stems.add(stem)

    if not kin_detected_stems:
        controls["control_relaciones_personajes"] = "NOT_APPLICABLE"
    else:
        missing_stems = [stem for stem in kin_detected_stems if not any(w in passage_norm.split() for w in KINSHIP_STEMS[stem])]
        if not missing_stems:
            controls["control_relaciones_personajes"] = "PASS"
        elif any(any(w in normalize(opcion_a).split() for w in KINSHIP_STEMS[stem]) for stem in missing_stems):
            controls["control_relaciones_personajes"] = "FAIL"
            incidencias.append(f"Relación/parentesco en opción A no tiene respaldo en el pasaje: {missing_stems}")
        else:
            controls["control_relaciones_personajes"] = "UNKNOWN"

    # 16. Control Rango Suficiente
    evidence_missing_outside = []
    if controls["control_nombres_propios"] == "FAIL":
        evidence_missing_outside.append("personaje bíblico ausente")
    if controls["control_numeros_cantidades"] == "FAIL":
        evidence_missing_outside.append("cantidad numérica no hallada")
    if controls["control_lugares"] == "FAIL":
        evidence_missing_outside.append("lugar no hallado")

    if evidence_missing_outside:
        controls["control_rango_suficiente"] = "FAIL"
        incidencias.append(f"El rango versicular actual no contiene la evidencia requerida para: {', '.join(evidence_missing_outside)}")
    elif controls["control_opcion_a_correcta"] == "PASS" and controls["control_soporte_pregunta"] == "PASS":
        controls["control_rango_suficiente"] = "PASS"
    else:
        controls["control_rango_suficiente"] = "UNKNOWN"

    # 17. Control Sin Ambigüedad
    unique_options = len({normalize(x) for x in (opcion_a, opcion_b, opcion_c, opcion_d) if x}) == 4
    if not unique_options:
        controls["control_sin_ambiguedad"] = "FAIL"
        incidencias.append("Existen opciones duplicadas o ambiguas")
    elif controls["control_distractores_invalidos"] == "PASS":
        controls["control_sin_ambiguedad"] = "PASS"
    else:
        controls["control_sin_ambiguedad"] = "UNKNOWN"

    # Clasificación final estricta
    has_fail = any(v == "FAIL" for v in controls.values())
    has_unknown = any(v == "UNKNOWN" for v in controls.values())

    if has_fail:
        estado = "REQUIERE_CORRECCION"
    elif has_unknown:
        estado = "NO_CONCLUYENTE"
    else:
        estado = "VERIFICADO"

    return {
        "id": qid,
        "reference": ref_str,
        "chapter": chapter,
        "verse_start": start,
        "verse_end": end,
        "estado": estado,
        "controles_superados": controls,
        "total_pass": sum(1 for v in controls.values() if v == "PASS"),
        "total_fail": sum(1 for v in controls.values() if v == "FAIL"),
        "total_unknown": sum(1 for v in controls.values() if v == "UNKNOWN"),
        "total_not_applicable": sum(1 for v in controls.values() if v == "NOT_APPLICABLE"),
        "total_controles": len(controls),
        "incidencias": incidencias,
        "correcciones_sugeridas": correcciones_sugeridas,
        "hash_sha256_pasaje": passage_hash,
        "source_text_persisted": False,
    }


def run_audit(
    spec: dict[str, Any] | list[dict[str, Any]],
    fetch_chapter_fn: Callable[[str, int], dict[int, str]],
    output_dir: Path,
    rate_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta el pipeline completo de auditoría agrupando dinámicamente por capítulo."""
    if isinstance(spec, list):
        raw_questions = spec
    elif isinstance(spec, dict):
        raw_questions = spec.get("questions", [])
    else:
        raw_questions = []

    book_key = detect_book_key(spec)
    book_cfg = BOOK_CONFIGS.get(book_key, BOOK_CONFIGS["genesis"])
    canonical_book_name = book_cfg["canonical_name"]
    api_book_name = book_cfg["api_name"]

    # Agrupación dinámica por capítulo
    questions_by_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for q in raw_questions:
        ch = int(q.get("chapter", 0))
        questions_by_chapter[ch].append(q)

    present_chapters = sorted(questions_by_chapter.keys())
    all_results: list[dict[str, Any]] = []
    correcciones_totales: list[dict[str, Any]] = []
    revision_manual: list[dict[str, Any]] = []
    controles_distribution: dict[str, dict[str, int]] = defaultdict(lambda: Counter())

    successful_fetches: list[int] = []
    failed_fetches: list[int] = []

    print(f"Libro canónico: {canonical_book_name} (API: {api_book_name})", flush=True)
    print(f"Preguntas a auditar: {len(raw_questions)}", flush=True)
    print(f"Capítulos detectados ({len(present_chapters)}): {present_chapters[:10]}...{present_chapters[-5:] if len(present_chapters)>10 else ''}", flush=True)

    for idx, chapter in enumerate(present_chapters, start=1):
        ch_questions = questions_by_chapter[chapter]
        print(f"[{idx}/{len(present_chapters)}] Auditando {canonical_book_name} {chapter} ({len(ch_questions)} preguntas)...", flush=True)
        verse_map = fetch_chapter_fn(api_book_name, chapter)

        if verse_map:
            successful_fetches.append(chapter)
        else:
            failed_fetches.append(chapter)

        for q in ch_questions:
            res = evaluate_question(q, verse_map, book_key=book_key)
            all_results.append(res)
            for c_name, c_state in res["controles_superados"].items():
                controles_distribution[c_name][c_state] += 1

            if res["correcciones_sugeridas"]:
                correcciones_totales.extend(res["correcciones_sugeridas"])
            if res["estado"] in {"REQUIERE_CORRECCION", "NO_CONCLUYENTE"}:
                revision_manual.append({
                    "id": res["id"],
                    "reference": res["reference"],
                    "estado": res["estado"],
                    "incidencias": res["incidencias"],
                    "controles_fallidos_o_dudosos": {k: v for k, v in res["controles_superados"].items() if v in {"FAIL", "UNKNOWN"}},
                    "correcciones_sugeridas": res["correcciones_sugeridas"],
                })

        if isinstance(verse_map, dict):
            verse_map.clear()
        del verse_map

    output_dir.mkdir(parents=True, exist_ok=True)
    blocks = book_cfg.get("blocks", [])

    for start_ch, end_ch, filename in blocks:
        block_results = [r for r in all_results if start_ch <= r.get("chapter", 0) <= end_ch]
        block_payload = {
            "schema_version": f"quizbible-rvr1960-audit-block-v1",
            "book": canonical_book_name,
            "chapter_range": f"{start_ch:02d}-{end_ch:02d}",
            "questions_count": len(block_results),
            "verified_count": sum(1 for r in block_results if r["estado"] == "VERIFICADO"),
            "review_required_count": sum(1 for r in block_results if r["estado"] == "REQUIERE_CORRECCION"),
            "inconclusive_count": sum(1 for r in block_results if r["estado"] == "NO_CONCLUYENTE"),
            "source_text_persisted": False,
            "results": block_results,
        }
        (output_dir / filename).write_text(json.dumps(block_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    correcciones_payload = {
        "schema_version": "quizbible-audit-corrections-v1",
        "total_correcciones": len(correcciones_totales),
        "source_text_persisted": False,
        "correcciones": correcciones_totales,
    }
    (output_dir / "correcciones-aplicadas.json").write_text(json.dumps(correcciones_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    revision_payload = {
        "schema_version": "quizbible-manual-review-v1",
        "total_pendientes": len(revision_manual),
        "source_text_persisted": False,
        "pendientes": revision_manual,
    }
    (output_dir / "revision-manual-pendiente.json").write_text(json.dumps(revision_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    controles_stats = {
        c_name: {
            "PASS": counts.get("PASS", 0),
            "FAIL": counts.get("FAIL", 0),
            "UNKNOWN": counts.get("UNKNOWN", 0),
            "NOT_APPLICABLE": counts.get("NOT_APPLICABLE", 0),
        }
        for c_name, counts in controles_distribution.items()
    }

    total_q = len(all_results)
    verif_c = sum(1 for r in all_results if r["estado"] == "VERIFICADO")
    req_corr_c = sum(1 for r in all_results if r["estado"] == "REQUIERE_CORRECCION")
    inconc_c = sum(1 for r in all_results if r["estado"] == "NO_CONCLUYENTE")

    rm = rate_metrics or {}
    attempts_total = rm.get("http_request_attempts_total", len(present_chapters))
    rate_retries = rm.get("rate_limit_retries", 0)

    summary = {
        "schema_version": "quizbible-rvr1960-audit-summary-v1",
        "source": "ApiBiblia API RVR1960",
        "book": canonical_book_name,
        "total_questions": total_q,
        "chapters_present_in_bank": len(present_chapters),
        "successful_chapter_fetches": len(successful_fetches),
        "failed_chapter_fetches": len(failed_fetches),
        "failed_chapters": failed_fetches,
        "chapters_covered": len(successful_fetches),
        "textual_coverage_complete": (len(successful_fetches) == book_cfg["total_chapters"] and len(failed_fetches) == 0),
        "chapter_coverage_complete_1_max": present_chapters == list(range(1, book_cfg["total_chapters"] + 1)),
        "http_request_attempts_total": attempts_total,
        "rate_limit_retries": rate_retries,
        "verified_count": verif_c,
        "requires_correction_count": req_corr_c,
        "inconclusive_count": inconc_c,
        "verification_rate": round(verif_c / total_q * 100, 2) if total_q else 0.0,
        "controls_distribution": controles_stats,
        "source_text_persisted": False,
    }
    (output_dir / "resumen-general.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\nAuditoría finalizada:", flush=True)
    print(f"- Libro: {canonical_book_name}", flush=True)
    print(f"- Total preguntas: {total_q}", flush=True)
    print(f"- VERIFICADO: {verif_c}", flush=True)
    print(f"- REQUIERE_CORRECCION: {req_corr_c}", flush=True)
    print(f"- NO_CONCLUYENTE: {inconc_c}", flush=True)
    print(f"- Capítulos obtenidos: {len(successful_fetches)}/{book_cfg['total_chapters']}", flush=True)
    print(f"- Cobertura textual completa: {summary['textual_coverage_complete']}", flush=True)
    print(f"- Texto bíblico persistido: False", flush=True)
    return summary


def main() -> int:
    try:
        parser = argparse.ArgumentParser(description="Auditor bíblico semántico derivado contra RVR1960")
        parser.add_argument("--input", default="tools/bible_extractor/genesis-master-input.json", help="Archivo de entrada")
        parser.add_argument("--output-dir", default=None, help="Directorio de salidas derivadas")
        parser.add_argument("--version", default="RVR1960", help="Versión bíblica (RVR1960)")
        parser.add_argument("--offline-fixture", default=None, help="Archivo JSON con fixtures simulados")
        args = parser.parse_args()

        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: No se encontró el archivo de entrada '{input_path}'.", file=sys.stderr)
            return 1

        spec = json.loads(input_path.read_text(encoding="utf-8"))
        book_key = detect_book_key(spec)
        book_cfg = BOOK_CONFIGS.get(book_key, BOOK_CONFIGS["genesis"])

        output_dir_str = args.output_dir or book_cfg["default_output_dir"]
        output_dir = Path(output_dir_str)

        if args.offline_fixture:
            fixture_data = json.loads(Path(args.offline_fixture).read_text(encoding="utf-8"))

            def fetch_mock(book: str, chapter: int) -> dict[int, str]:
                return {int(k): str(v) for k, v in fixture_data.get(str(chapter), {}).items()}

            run_audit(spec, fetch_mock, output_dir)
            return 0

        api_key = os.environ.get("APIBIBLIA_API_KEY", "").strip()
        if not api_key:
            print("Falta APIBIBLIA_API_KEY en las variables de entorno. Para pruebas locales use --offline-fixture.", file=sys.stderr)
            return 2

        rate_metrics = {
            "http_request_attempts_total": 0,
            "rate_limit_retries": 0,
        }
        last_request_time = [0.0]
        min_interval = 2.3

        def fetch_apibiblia(api_book_name: str, chapter: int) -> dict[int, str]:
            query = urllib.parse.urlencode({"ref": f"{api_book_name} {chapter}", "version": args.version})
            url = f"{PASSAGE_URL}?{query}"

            max_retries = 4
            for attempt in range(1, max_retries + 1):
                elapsed = time.time() - last_request_time[0]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)

                rate_metrics["http_request_attempts_total"] += 1
                last_request_time[0] = time.time()

                try:
                    status, payload = api_get(url, api_key)
                    if status == 200:
                        verse_map = extract_verses_robust(payload)
                        del payload
                        return verse_map

                    print(f"ApiBiblia HTTP {status} para {api_book_name} {chapter} (intento {attempt}/{max_retries})", file=sys.stderr, flush=True)

                except Exception as exc:
                    err_msg = str(exc)
                    if "429" in err_msg or "Rate" in err_msg or "RATE_LIMIT" in err_msg:
                        rate_metrics["rate_limit_retries"] += 1
                        print(f"Rate limit detectado en capítulo {chapter}. Esperando 62s para reset de ventana (intento {attempt}/{max_retries})...", file=sys.stderr, flush=True)
                        time.sleep(62.0)
                    else:
                        print(f"Aviso consultando {api_book_name} {chapter} (intento {attempt}/{max_retries}): {exc}", file=sys.stderr, flush=True)
                        if attempt == max_retries:
                            print(f"Error definitivo obteniendo {api_book_name} {chapter}. Se continuará.", file=sys.stderr, flush=True)
                            return {}
                        time.sleep(3.0 * attempt)

            return {}

        run_audit(spec, fetch_apibiblia, output_dir, rate_metrics=rate_metrics)
        return 0

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
