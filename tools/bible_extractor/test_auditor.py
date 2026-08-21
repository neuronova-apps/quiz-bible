#!/usr/bin/env python3
"""Pruebas unitarias para el auditor de preguntas bíblicas (sin conexión externa)."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditor import evaluate_question, run_audit


class TestAuditor(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_evaluate_question_verificado(self) -> None:
        q = {
            "id": "NQB-AT-GEN-0001",
            "book": "Génesis",
            "chapter": 1,
            "verse_start": 1,
            "verse_end": 1,
            "reference": "Génesis 1:1",
            "category": "AT_GENERAL",
            "subcategory": "Creación",
            "characters": ["Dios"],
            "difficulty": "Básico",
            "question_type": "Selección múltiple",
            "question": "¿Quién es presentado como creador de los cielos y la tierra al comienzo del relato bíblico?",
            "opcion_a": "Dios",
            "opcion_b": "Adán",
            "opcion_c": "Noé",
            "opcion_d": "Abraham",
            "correct_option": "A",
            "correct_answer": "Dios",
            "explanation": "Génesis 1:1 afirma directamente que en el principio creó Dios los cielos y la tierra.",
            "additional_references": [],
            "eligible_modes": ["AT", "AMBOS"],
        }
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        result = evaluate_question(q, verse_map)

        self.assertEqual(result["id"], "NQB-AT-GEN-0001")
        self.assertEqual(result["estado"], "VERIFICADO")
        self.assertTrue(result["controles_superados"]["control_libro"])
        self.assertTrue(result["controles_superados"]["control_capitulo"])
        self.assertTrue(result["controles_superados"]["control_referencia_existencia"])
        self.assertTrue(result["controles_superados"]["control_opcion_a_correcta"])
        self.assertTrue(result["controles_superados"]["control_respuesta_coincide_a"])
        self.assertFalse(result["source_text_persisted"])
        self.assertIsNotNone(result["hash_sha256_pasaje"])

    def test_evaluate_additional_references_nqb_0031(self) -> None:
        q = {
            "id": "NQB-AT-GEN-0031",
            "book": "Génesis",
            "chapter": 4,
            "verse_start": 1,
            "verse_end": 2,
            "reference": "Génesis 4:1-2",
            "category": "PERSONAJES_BIBLICOS",
            "subcategory": "Hijos de Adán",
            "characters": ["Adán", "Eva", "Caín", "Abel", "Set"],
            "difficulty": "Intermedio",
            "question_type": "Selección múltiple",
            "question": "¿Qué tres hijos de Adán aparecen mencionados por nombre en Génesis?",
            "opcion_a": "Caín, Abel y Set",
            "opcion_b": "Caín, Set y Enoc",
            "opcion_c": "Abel, Noé y Set",
            "opcion_d": "Caín, Abel y Lamec",
            "correct_option": "A",
            "correct_answer": "Caín, Abel y Set",
            "explanation": "Génesis menciona por nombre a Caín y Abel al narrar los primeros hijos de Adán y Eva, y más adelante registra el nacimiento de Set.",
            "additional_references": ["Génesis 4:25"],
            "eligible_modes": ["AT", "AMBOS", "PERSONAJES_AT", "PERSONAJES_AMBOS"],
        }
        verse_map = {
            1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín...",
            2: "Después dio a luz a su hermano Abel...",
            25: "Y conoció de nuevo Adán a su mujer, la cual dio a luz un hijo, y llamó su nombre Set...",
        }
        result = evaluate_question(q, verse_map)
        self.assertEqual(result["id"], "NQB-AT-GEN-0031")
        self.assertEqual(result["estado"], "VERIFICADO")
        self.assertTrue(result["controles_superados"]["control_referencia_existencia"])
        self.assertTrue(result["controles_superados"]["control_opcion_a_correcta"])

    def test_evaluate_question_requiere_correccion_desalineacion(self) -> None:
        q = {
            "id": "NQB-AT-GEN-0002",
            "book": "Génesis",
            "chapter": 1,
            "verse_start": 3,
            "verse_end": 5,
            "reference": "Génesis 1:3-5",
            "category": "AT_GENERAL",
            "subcategory": "Creación",
            "characters": ["Dios"],
            "difficulty": "Básico",
            "question_type": "Selección múltiple",
            "question": "¿Qué llamó Dios a existir primero?",
            "opcion_a": "La luz",
            "opcion_b": "Las estrellas",
            "opcion_c": "Los animales",
            "opcion_d": "El mar",
            "correct_option": "B",  # Error: desalineado con A
            "correct_answer": "Las estrellas",
            "explanation": "Dios dijo: Sea la luz; y fue la luz.",
            "additional_references": [],
            "eligible_modes": ["AT"],
        }
        verse_map = {
            3: "Y dijo Dios: Sea la luz; y fue la luz.",
            4: "Y vio Dios que la luz era buena; y separó Dios la luz de las tinieblas.",
            5: "Y llamó Dios a la luz Día, y a las tinieblas llamó Noche.",
        }
        result = evaluate_question(q, verse_map)
        self.assertEqual(result["estado"], "REQUIERE_CORRECCION")
        self.assertFalse(result["controles_superados"]["control_respuesta_coincide_a"])
        self.assertTrue(len(result["correcciones_sugeridas"]) > 0)

    def test_run_audit_pipeline_without_text_persistence(self) -> None:
        spec = {
            "source": "Quiz Bible master bank - Test",
            "version": "RVR1960",
            "book": "Génesis",
            "total_questions": 2,
            "questions": [
                {
                    "id": "NQB-AT-GEN-0001",
                    "book": "Génesis",
                    "chapter": 1,
                    "verse_start": 1,
                    "verse_end": 1,
                    "reference": "Génesis 1:1",
                    "category": "AT_GENERAL",
                    "subcategory": "Creación",
                    "characters": ["Dios"],
                    "difficulty": "Básico",
                    "question_type": "Selección múltiple",
                    "question": "¿Quién creó los cielos y la tierra?",
                    "opcion_a": "Dios",
                    "opcion_b": "Adán",
                    "opcion_c": "Noé",
                    "opcion_d": "Abraham",
                    "correct_option": "A",
                    "correct_answer": "Dios",
                    "explanation": "En el principio creó Dios los cielos y la tierra.",
                    "additional_references": [],
                    "eligible_modes": ["AT"],
                },
                {
                    "id": "NQB-AT-GEN-0050",
                    "book": "Génesis",
                    "chapter": 50,
                    "verse_start": 24,
                    "verse_end": 26,
                    "reference": "Génesis 50:24-26",
                    "category": "PERSONAJES_BIBLICOS",
                    "subcategory": "Patriarcas",
                    "characters": ["José"],
                    "difficulty": "Intermedio",
                    "question_type": "Selección múltiple",
                    "question": "¿Quién anunció a sus hermanos que Dios los visitaría antes de morir en Egipto?",
                    "opcion_a": "José",
                    "opcion_b": "Judá",
                    "opcion_c": "Rubén",
                    "opcion_d": "Benjamín",
                    "correct_option": "A",
                    "correct_answer": "José",
                    "explanation": "José dijo a sus hermanos: Yo voy a morir; mas Dios ciertamente os visitará.",
                    "additional_references": [],
                    "eligible_modes": ["AT", "PERSONAJES_AT"],
                },
            ],
        }

        mock_bible = {
            1: {1: "En el principio creó Dios los cielos y la tierra."},
            50: {
                24: "Y José dijo a sus hermanos: Yo voy a morir; mas Dios ciertamente os visitará.",
                25: "E hizo jurar José a los hijos de Israel.",
                26: "Y murió José a la edad de ciento diez años.",
            },
        }

        def mock_fetch(book: str, ch: int) -> dict[int, str]:
            return dict(mock_bible.get(ch, {}))

        summary = run_audit(spec, mock_fetch, self.temp_dir)
        self.assertEqual(summary["total_questions"], 2)
        self.assertEqual(summary["verified_count"], 2)
        self.assertFalse(summary["source_text_persisted"])

        # Validar que los archivos derivados existen y no tienen texto bíblico
        resumen_file = self.temp_dir / "resumen-general.json"
        self.assertTrue(resumen_file.exists())
        data = json.loads(resumen_file.read_text(encoding="utf-8"))
        self.assertFalse(data["source_text_persisted"])

        block_01_10 = json.loads((self.temp_dir / "genesis-01-10.json").read_text(encoding="utf-8"))
        self.assertEqual(block_01_10["questions_count"], 1)
        self.assertFalse(block_01_10["source_text_persisted"])
        for item in block_01_10["results"]:
            self.assertNotIn("text", item)
            self.assertNotIn("verse_text", item)


if __name__ == "__main__":
    unittest.main()
