#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Carga preguntas reales directamente desde genesis-master-input.json, realizando
mutaciones controladas sobre copias profundas (deepcopy).
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditor import evaluate_question, run_audit, extract_numbers, normalize

MASTER_PATH = Path(__file__).parent / "genesis-master-input.json"


class TestAuditorCanonical(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw_data = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
        questions_list = raw_data.get("questions", []) if isinstance(raw_data, dict) else raw_data
        cls.master_questions = {q["id"]: q for q in questions_list}

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_real_question(self, qid: str) -> dict:
        """Devuelve una copia profunda exacta del registro canónico."""
        self.assertIn(qid, self.master_questions, f"ID '{qid}' no encontrado en genesis-master-input.json")
        return copy.deepcopy(self.master_questions[qid])

    # --- TEST GLOBAL DE CONSISTENCIA DE IDs Y REFERENCIAS ---

    def test_global_canonical_id_reference_integrity(self) -> None:
        """Verifica que todos los IDs en el banco maestro tengan exactamente su referencia canónica."""
        for qid, q in self.master_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    # --- PRUEBAS DE UTILIDADES NUMÉRICAS Y ARTÍCULOS ---

    def test_extract_numbers_article_vs_quantity(self) -> None:
        """'un/una' no debe extraer número 1 cuando funciona como artículo indeterminado."""
        # Casos de artículos indeterminados -> NO deben producir el número 1
        self.assertEqual(extract_numbers("Una serpiente"), [])
        self.assertEqual(extract_numbers("una señal"), [])
        self.assertEqual(extract_numbers("una fuerte hambre"), [])
        self.assertEqual(extract_numbers("una estatua de sal"), [])
        self.assertEqual(extract_numbers("un cachorro de león"), [])
        self.assertEqual(extract_numbers("una túnica de diversos colores"), [])

        # Casos cuantitativos explícitos con unidades contables -> SÍ deben producir 1
        self.assertIn(1, extract_numbers("un año"))
        self.assertIn(1, extract_numbers("una vez"))
        self.assertIn(1, extract_numbers("un codo"))
        self.assertIn(1, extract_numbers("una pareja"))

        # Dígitos y números compuestos
        self.assertEqual(extract_numbers("novecientos sesenta y nueve años"), [969])
        self.assertEqual(extract_numbers("300 codos de largo, 50 de ancho y 30 de alto"), [30, 50, 300])

    # --- PRUEBAS DE ELIMINACIÓN DE FALSOS NOMBRES PROPIOS ---

    def test_capitalized_initial_words_not_treated_as_names(self) -> None:
        """Palabras iniciales como 'Ser', 'Ofreció', 'Matarlo', 'Guardar' no se evalúan como nombres propios."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        # Mutamos opción A para iniciar con un verbo capitalizado no presente en el versículo
        q["opcion_a"] = "Crear los cielos y la tierra"
        q["correct_answer"] = "Crear los cielos y la tierra"
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        # 'Crear' no debe ser marcado como fallo en control_nombres_propios
        self.assertNotEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")

    # --- PRUEBAS DE CASOS REALES DEL BANCO (POSITIVOS) ---

    def test_positive_nqb_0084_matusalen_969(self) -> None:
        """NQB-AT-GEN-0084 real: Matusalén vivió 969 años (Génesis 5:27)."""
        q = self.get_real_question("NQB-AT-GEN-0084")
        self.assertEqual(q["reference"], "Génesis 5:27")
        verse_map = {27: "Fueron, pues, todos los días de Matusalén novecientos sesenta y nueve años; y murió."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "PASS")

    def test_positive_nqb_0033_medidas_arca_300_50_30(self) -> None:
        """NQB-AT-GEN-0033 real: Medidas del arca (Génesis 6:15)."""
        q = self.get_real_question("NQB-AT-GEN-0033")
        self.assertEqual(q["reference"], "Génesis 6:15")
        verse_map = {15: "Y de esta manera la harás: de trescientos codos la longitud del arca, de cincuenta codos su anchura, y de treinta codos su altura."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")

    def test_positive_nqb_0069_abram_318_hombres(self) -> None:
        """NQB-AT-GEN-0069 real: Abram y 318 criados (Génesis 14:14)."""
        q = self.get_real_question("NQB-AT-GEN-0069")
        self.assertEqual(q["reference"], "Génesis 14:14")
        verse_map = {14: "Oyó Abram que su pariente estaba prisionero, y armó a sus criados, los nacidos en su casa, trescientos dieciocho, y los siguió hasta Dan."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_positive_nqb_0095_isaac_40_anos(self) -> None:
        """NQB-AT-GEN-0095 real: Isaac 40 años al casarse con Rebeca (Génesis 25:20)."""
        q = self.get_real_question("NQB-AT-GEN-0095")
        self.assertEqual(q["reference"], "Génesis 25:20")
        verse_map = {20: "y era Isaac de cuarenta años cuando tomó por mujer a Rebeca, hija de Betuel arameo de Padan-aram, hermana de Labán arameo."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_relaciones_personajes"], "PASS")

    def test_positive_nqb_0120_jacob_130_anos(self) -> None:
        """NQB-AT-GEN-0120 real: Jacob 130 años ante Faraón (Génesis 47:9)."""
        q = self.get_real_question("NQB-AT-GEN-0120")
        self.assertEqual(q["reference"], "Génesis 47:9")
        verse_map = {9: "Y Jacob respondió a Faraón: Los días de los años de mi peregrinación son ciento treinta años; pocos y malos han sido los días de los años de mi vida."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_positive_nqb_0031_additional_references_set(self) -> None:
        """NQB-AT-GEN-0031 real: Caín, Abel y Set con additional_references Génesis 4:25."""
        q = self.get_real_question("NQB-AT-GEN-0031")
        self.assertEqual(q["reference"], "Génesis 4:1-2")
        self.assertIn("Génesis 4:25", q["additional_references"])
        verse_map = {
            1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín, y dijo: Por voluntad de Jehová he adquirido varón.",
            2: "Después dio a luz a su hermano Abel. Y Abel fue pastor de ovejas, y Caín fue labrador de la tierra.",
            25: "Y conoció de nuevo Adán a su mujer, la cual dio a luz un hijo, y llamó su nombre Set: Porque Dios (dijo ella) me ha sustituido otro hijo en lugar de Abel, a quien mató Caín.",
        }
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")

    def test_positive_orthographic_variants_betel(self) -> None:
        """Variantes 'Betel' y 'Bet-el' se normalizan de forma transparente."""
        self.assertEqual(normalize("Bet-el"), "betel")
        self.assertEqual(normalize("Beer-seba"), "beerseba")
        self.assertEqual(normalize("Padan-aram"), "padanaram")

    # --- PRUEBAS DE PARÁFRASIS (PRODUCEN UNKNOWN, NO FAIL) ---

    def test_paraphrase_produces_unknown_not_fail(self) -> None:
        """Las paráfrasis legítimas sin coincidencia exacta producen UNKNOWN, nunca FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        q["opcion_a"] = "Para preservar vidas durante la hambruna"
        q["correct_answer"] = "Para preservar vidas durante la hambruna"
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        # Debe marcar UNKNOWN (NO_CONCLUYENTE) y NO FAIL (REQUIERE_CORRECCION)
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "UNKNOWN")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS NEGATIVAS OBLIGATORIAS (MUTACIONES CONTROLADAS) ---

    def test_negative_incorrect_age_mutated(self) -> None:
        """Mutación negativa sobre NQB-AT-GEN-0084: 950 años en vez de 969 -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0084")
        q["opcion_a"] = "950 años"  # Mutación negativa deliberada
        q["correct_answer"] = "950 años"
        verse_map = {27: "Fueron, pues, todos los días de Matusalén novecientos sesenta y nueve años; y murió."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")

    def test_negative_incorrect_character_mutated(self) -> None:
        """Mutación negativa: personaje bíblico ajeno al pasaje en opción A -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        q["opcion_a"] = "Moisés"  # Mutación negativa deliberada
        q["correct_answer"] = "Moisés"
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")

    def test_negative_incorrect_place_mutated(self) -> None:
        """Mutación negativa sobre NQB-AT-GEN-0076 (Génesis 8:4): lugar bíblico contradictorio -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0076")
        self.assertEqual(q["reference"], "Génesis 8:4")
        q["opcion_a"] = "Montes de Sinaí"  # Mutación negativa deliberada
        q["correct_answer"] = "Montes de Sinaí"
        verse_map = {4: "Y reposó el arca en el mes séptimo, a los diecisiete días del mes, sobre los montes de Ararat."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_lugares"], "FAIL")

    def test_negative_duplicate_distractor_mutated(self) -> None:
        """Mutación negativa: distractor duplicado e idéntico a opción A -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        q["opcion_b"] = q["opcion_a"]  # Mutación negativa: duplicar opción A en B
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_distractores_invalidos"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_sin_ambiguedad"], "FAIL")

    def test_negative_missing_additional_reference_mutated(self) -> None:
        """Mutación negativa sobre NQB-AT-GEN-0031: eliminamos additional_references -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0031")
        q["additional_references"] = []  # Mutación negativa: omitir Génesis 4:25
        verse_map = {
            1: "Conoció Adán a su mujer Eva, la cual concibió y dio a luz a Caín...",
            2: "Después dio a luz a su hermano Abel...",
        }
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "FAIL")


if __name__ == "__main__":
    unittest.main()
