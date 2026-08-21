#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Incluye pruebas positivas para números, lugares, parentescos y referencias adicionales,
así como fixtures negativos obligatorios (errores deliberados de cifras, nombres, lugares,
parentescos, distractores en conflicto, explicaciones falsas y rangos insuficientes).
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditor import evaluate_question, run_audit, extract_numbers


class TestAuditorSemantic(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # --- PRUEBAS DE UTILIDADES ---
    def test_extract_numbers(self) -> None:
        text = "Y fueron todos los días de Matusalén novecientos sesenta y nueve años; y el arca de 300 codos, 50 de ancho y treinta de alto con 318 hombres a los ciento treinta años."
        nums = extract_numbers(text)
        self.assertIn(969, nums)
        self.assertIn(300, nums)
        self.assertIn(50, nums)
        self.assertIn(30, nums)
        self.assertIn(318, nums)
        self.assertIn(130, nums)

    # --- PRUEBAS POSITIVAS DE EJEMPLOS DEL BANCO ---

    def test_positive_nqb_0084_matusalen_969(self) -> None:
        """NQB-AT-GEN-0084: Matusalén vivió 969 años (Génesis 5:27)."""
        q = {
            "id": "NQB-AT-GEN-0084",
            "book": "Génesis",
            "chapter": 5,
            "verse_start": 27,
            "verse_end": 27,
            "reference": "Génesis 5:27",
            "characters": ["Matusalén"],
            "question": "¿Cuántos años vivió Matusalén según Génesis?",
            "opcion_a": "969 años",
            "opcion_b": "950 años",
            "opcion_c": "930 años",
            "opcion_d": "912 años",
            "correct_option": "A",
            "correct_answer": "969 años",
            "explanation": "Génesis 5:27 afirma que fueron todos los días de Matusalén novecientos sesenta y nueve años; y murió.",
            "additional_references": [],
        }
        verse_map = {27: "Fueron, pues, todos los días de Matusalén novecientos sesenta y nueve años; y murió."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "PASS")

    def test_positive_nqb_0033_medidas_arca_300_50_30(self) -> None:
        """NQB-AT-GEN-0033: Medidas del arca de Noé: 300, 50 y 30 codos (Génesis 6:15)."""
        q = {
            "id": "NQB-AT-GEN-0033",
            "book": "Génesis",
            "chapter": 6,
            "verse_start": 15,
            "verse_end": 15,
            "reference": "Génesis 6:15",
            "characters": ["Noé"],
            "question": "¿Cuáles fueron las dimensiones que Dios ordenó para el arca construida por Noé?",
            "opcion_a": "300 codos de longitud, 50 codos de anchura y 30 codos de altura",
            "opcion_b": "200 codos de longitud, 40 codos de anchura y 20 codos de altura",
            "opcion_c": "400 codos de longitud, 60 codos de anchura y 40 codos de altura",
            "opcion_d": "250 codos de longitud, 50 codos de anchura y 35 codos de altura",
            "correct_option": "A",
            "correct_answer": "300 codos de longitud, 50 codos de anchura y 30 codos de altura",
            "explanation": "El pasaje de Génesis 6:15 detalla que la longitud del arca sería de trescientos codos, su anchura de cincuenta codos y su altura de treinta codos.",
            "additional_references": [],
        }
        verse_map = {15: "Y de esta manera la harás: de trescientos codos la longitud del arca, de cincuenta codos su anchura, y de treinta codos su altura."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")

    def test_positive_nqb_0069_abram_318_hombres(self) -> None:
        """NQB-AT-GEN-0069: Abram rescató a Lot con 318 criados (Génesis 14:14)."""
        q = {
            "id": "NQB-AT-GEN-0069",
            "book": "Génesis",
            "chapter": 14,
            "verse_start": 14,
            "verse_end": 14,
            "reference": "Génesis 14:14",
            "characters": ["Abram", "Lot"],
            "question": "¿Con cuántos hombres armados de su casa salió Abram al rescate de Lot?",
            "opcion_a": "318 criados",
            "opcion_b": "300 hombres",
            "opcion_c": "400 guerreros",
            "opcion_d": "120 siervos",
            "correct_option": "A",
            "correct_answer": "318 criados",
            "explanation": "Génesis 14:14 relata que oyó Abram que su pariente estaba prisionero, y armó a sus criados, los nacidos en su casa, trescientos dieciocho.",
            "additional_references": [],
        }
        verse_map = {14: "Oyó Abram que su pariente estaba prisionero, y armó a sus criados, los nacidos en su casa, trescientos dieciocho, y los siguió hasta Dan."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_positive_nqb_0095_isaac_40_anos(self) -> None:
        """NQB-AT-GEN-0095: Isaac tenía 40 años al casarse con Rebeca (Génesis 25:20)."""
        q = {
            "id": "NQB-AT-GEN-0095",
            "book": "Génesis",
            "chapter": 25,
            "verse_start": 20,
            "verse_end": 20,
            "reference": "Génesis 25:20",
            "characters": ["Isaac", "Rebeca"],
            "question": "¿Qué edad tenía Isaac cuando tomó por mujer a Rebeca?",
            "opcion_a": "40 años",
            "opcion_b": "30 años",
            "opcion_c": "50 años",
            "opcion_d": "25 años",
            "correct_option": "A",
            "correct_answer": "40 años",
            "explanation": "Génesis 25:20 afirma que era Isaac de cuarenta años cuando tomó por mujer a Rebeca, hija de Betuel.",
            "additional_references": [],
        }
        verse_map = {20: "y era Isaac de cuarenta años cuando tomó por mujer a Rebeca, hija de Betuel arameo de Padan-aram, hermana de Labán arameo."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_relaciones_personajes"], "PASS")

    def test_positive_nqb_0120_jacob_130_anos(self) -> None:
        """NQB-AT-GEN-0120: Jacob declaró tener 130 años ante Faraón (Génesis 47:9)."""
        q = {
            "id": "NQB-AT-GEN-0120",
            "book": "Génesis",
            "chapter": 47,
            "verse_start": 9,
            "verse_end": 9,
            "reference": "Génesis 47:9",
            "characters": ["Jacob", "Faraón"],
            "question": "¿Cuántos años dijo Jacob a Faraón que tenían los días de su peregrinación?",
            "opcion_a": "130 años",
            "opcion_b": "120 años",
            "opcion_c": "110 años",
            "opcion_d": "140 años",
            "correct_option": "A",
            "correct_answer": "130 años",
            "explanation": "Jacob respondió a Faraón en Génesis 47:9 que los días de los años de su peregrinación eran ciento treinta años.",
            "additional_references": [],
        }
        verse_map = {9: "Y Jacob respondió a Faraón: Los días de los años de mi peregrinación son ciento treinta años; pocos y malos han sido los días de los años de mi vida."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_positive_places_ararat(self) -> None:
        """Verificación positiva de lugar: montes de Ararat (Génesis 8:4)."""
        q = {
            "id": "NQB-AT-GEN-0044",
            "book": "Génesis",
            "chapter": 8,
            "verse_start": 4,
            "verse_end": 4,
            "reference": "Génesis 8:4",
            "question": "¿Sobre qué montes reposó el arca de Noé en el mes séptimo?",
            "opcion_a": "Montes de Ararat",
            "opcion_b": "Montes de Sinaí",
            "opcion_c": "Montes de Seir",
            "opcion_d": "Montes de Moriah",
            "correct_option": "A",
            "correct_answer": "Montes de Ararat",
            "explanation": "Génesis 8:4 relata que el arca reposó sobre los montes de Ararat.",
            "additional_references": [],
        }
        verse_map = {4: "Y reposó el arca en el mes séptimo, a los diecisiete días del mes, sobre los montes de Ararat."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")

    def test_positive_additional_references_nqb_0031(self) -> None:
        """NQB-AT-GEN-0031 con referencia adicional Génesis 4:25 para Set."""
        q = {
            "id": "NQB-AT-GEN-0031",
            "book": "Génesis",
            "chapter": 4,
            "verse_start": 1,
            "verse_end": 2,
            "reference": "Génesis 4:1-2",
            "characters": ["Adán", "Eva", "Caín", "Abel", "Set"],
            "question": "¿Qué tres hijos de Adán aparecen mencionados por nombre en Génesis?",
            "opcion_a": "Caín, Abel y Set",
            "opcion_b": "Caín, Set y Enoc",
            "opcion_c": "Abel, Noé y Set",
            "opcion_d": "Caín, Abel y Lamec",
            "correct_option": "A",
            "correct_answer": "Caín, Abel y Set",
            "explanation": "Génesis menciona a Caín y Abel en 4:1-2 y a Set en 4:25.",
            "additional_references": ["Génesis 4:25"],
        }
        verse_map = {
            1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín...",
            2: "Después dio a luz a su hermano Abel...",
            25: "Y conoció de nuevo Adán a su mujer, la cual dio a luz un hijo, y llamó su nombre Set...",
        }
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")

    # --- PRUEBAS NEGATIVAS OBLIGATORIAS (REGRESIONES Y DETECCIÓN DE ERRORES) ---

    def test_negative_incorrect_age_or_number(self) -> None:
        """Detecta número incorrecto en opción A (950 en vez de 969)."""
        q = {
            "id": "NQB-TEST-NUM-FAIL",
            "book": "Génesis",
            "chapter": 5,
            "verse_start": 27,
            "verse_end": 27,
            "reference": "Génesis 5:27",
            "characters": ["Matusalén"],
            "question": "¿Cuántos años vivió Matusalén?",
            "opcion_a": "950 años",  # Incorrecto: el pasaje dice 969
            "opcion_b": "900 años",
            "opcion_c": "800 años",
            "opcion_d": "700 años",
            "correct_option": "A",
            "correct_answer": "950 años",
            "explanation": "Matusalén vivió novecientos sesenta y nueve años.",
            "additional_references": [],
        }
        verse_map = {27: "Fueron, pues, todos los días de Matusalén novecientos sesenta y nueve años; y murió."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")

    def test_negative_incorrect_name(self) -> None:
        """Detecta nombre incorrecto en opción A."""
        q = {
            "id": "NQB-TEST-NAME-FAIL",
            "book": "Génesis",
            "chapter": 4,
            "verse_start": 1,
            "verse_end": 1,
            "reference": "Génesis 4:1",
            "characters": ["Moisés"],
            "question": "¿Quién nació como primogénito de Eva?",
            "opcion_a": "Moisés",  # Moisés no aparece en Génesis 4:1
            "opcion_b": "Caín",
            "opcion_c": "Abel",
            "opcion_d": "Set",
            "correct_option": "A",
            "correct_answer": "Moisés",
            "explanation": "El pasaje menciona el nacimiento de Caín.",
            "additional_references": [],
        }
        verse_map = {1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín, y dijo: Por voluntad de Jehová he adquirido varón."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")

    def test_negative_incorrect_place(self) -> None:
        """Detecta lugar incorrecto en opción A."""
        q = {
            "id": "NQB-TEST-PLACE-FAIL",
            "book": "Génesis",
            "chapter": 8,
            "verse_start": 4,
            "verse_end": 4,
            "reference": "Génesis 8:4",
            "question": "¿Sobre qué montes reposó el arca?",
            "opcion_a": "Montes de Sinaí",  # Incorrecto: reposó sobre Ararat
            "opcion_b": "Montes de Ararat",
            "opcion_c": "Montes de Hebrón",
            "opcion_d": "Montes de Seir",
            "correct_option": "A",
            "correct_answer": "Montes de Sinaí",
            "explanation": "El arca reposó sobre los montes de Ararat.",
            "additional_references": [],
        }
        verse_map = {4: "Y reposó el arca en el mes séptimo, a los diecisiete días del mes, sobre los montes de Ararat."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_lugares"], "FAIL")

    def test_negative_incorrect_kinship(self) -> None:
        """Detecta parentesco incorrecto en opción A."""
        q = {
            "id": "NQB-TEST-KIN-FAIL",
            "book": "Génesis",
            "chapter": 12,
            "verse_start": 5,
            "verse_end": 5,
            "reference": "Génesis 12:5",
            "question": "¿Qué parentesco tenía Lot con Abram según Génesis?",
            "opcion_a": "Padre de Abram",  # Incorrecto: era su sobrino / hijo de su hermano
            "opcion_b": "Hijo de su hermano",
            "opcion_c": "Suegro de Abram",
            "opcion_d": "Yerno de Abram",
            "correct_option": "A",
            "correct_answer": "Padre de Abram",
            "explanation": "Tomó, pues, Abram a Sarai su mujer, y a Lot hijo de su hermano.",
            "additional_references": [],
        }
        verse_map = {5: "Tomó, pues, Abram a Sarai su mujer, y a Lot hijo de su hermano, y todos sus bienes que habían ganado."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_relaciones_personajes"], "FAIL")

    def test_negative_duplicate_distractor(self) -> None:
        """Detecta distractor duplicado o idéntico a opción A."""
        q = {
            "id": "NQB-TEST-DUP-FAIL",
            "book": "Génesis",
            "chapter": 1,
            "verse_start": 1,
            "verse_end": 1,
            "reference": "Génesis 1:1",
            "question": "¿Quién creó los cielos y la tierra?",
            "opcion_a": "Dios",
            "opcion_b": "Dios",  # Duplicado
            "opcion_c": "Adán",
            "opcion_d": "Noé",
            "correct_option": "A",
            "correct_answer": "Dios",
            "explanation": "En el principio creó Dios los cielos y la tierra.",
            "additional_references": [],
        }
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_distractores_invalidos"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_sin_ambiguedad"], "FAIL")

    def test_negative_insufficient_range_missing_additional_ref(self) -> None:
        """Detecta rango insuficiente cuando falta la referencia adicional requerida."""
        q = {
            "id": "NQB-TEST-RANGE-FAIL",
            "book": "Génesis",
            "chapter": 4,
            "verse_start": 1,
            "verse_end": 2,
            "reference": "Génesis 4:1-2",
            "characters": ["Set"],  # Set no está en 4:1-2
            "question": "¿Quién nació como tercer hijo mencionado de Adán?",
            "opcion_a": "Set",  # Set aparece en 4:25, no en 4:1-2
            "opcion_b": "Caín",
            "opcion_c": "Abel",
            "opcion_d": "Enoc",
            "correct_option": "A",
            "correct_answer": "Set",
            "explanation": "Set nace en Génesis 4:25.",
            "additional_references": [],  # Olvido de additional_references
        }
        verse_map = {
            1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín...",
            2: "Después dio a luz a su hermano Abel...",
        }
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "FAIL")

    def test_negative_partially_correct_composite_answer(self) -> None:
        """Detecta respuesta compuesta incompleta o parcialmente correcta."""
        q = {
            "id": "NQB-TEST-PARTIAL-FAIL",
            "book": "Génesis",
            "chapter": 4,
            "verse_start": 1,
            "verse_end": 2,
            "reference": "Génesis 4:1-2",
            "question": "¿Quiénes nacieron según Génesis 4:1-2?",
            "opcion_a": "Caín, Abel y Abraham",  # Abraham no está en 4:1-2
            "opcion_b": "Caín y Moisés",
            "opcion_c": "Abel y David",
            "opcion_d": "Noé y Set",
            "correct_option": "A",
            "correct_answer": "Caín, Abel y Abraham",
            "explanation": "Génesis 4:1-2 relata el nacimiento de Caín y Abel.",
            "additional_references": [],
        }
        verse_map = {
            1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín...",
            2: "Después dio a luz a su hermano Abel...",
        }
        res = evaluate_question(q, verse_map)
        self.assertIn(res["estado"], {"REQUIERE_CORRECCION", "NO_CONCLUYENTE"})
        self.assertNotEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")

    def test_run_audit_offline_pipeline(self) -> None:
        """Verifica la ejecución modular completa de run_audit y que source_text_persisted sea False."""
        spec = [
            {
                "id": "NQB-AT-GEN-0001",
                "book": "Génesis",
                "chapter": 1,
                "verse_start": 1,
                "verse_end": 1,
                "reference": "Génesis 1:1",
                "question": "¿Qué creó Dios en el principio?",
                "opcion_a": "Los cielos y la tierra",
                "opcion_b": "El sol y la luna",
                "opcion_c": "El mar y la tierra seca",
                "opcion_d": "Las plantas y los animales",
                "correct_option": "A",
                "correct_answer": "Los cielos y la tierra",
                "explanation": "Génesis 1:1 afirma que en el principio creó Dios los cielos y la tierra.",
                "additional_references": [],
            }
        ]
        summary = run_audit(spec, lambda b, c: {1: "En el principio creó Dios los cielos y la tierra."}, self.temp_dir)
        self.assertEqual(summary["total_questions"], 1)
        self.assertFalse(summary["source_text_persisted"])
        self.assertTrue((self.temp_dir / "resumen-general.json").exists())
        self.assertTrue((self.temp_dir / "genesis-01-10.json").exists())


if __name__ == "__main__":
    unittest.main()
