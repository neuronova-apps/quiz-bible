#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Carga preguntas reales directamente desde genesis-master-input.json, realizando
mutaciones controladas sobre copias profundas (deepcopy) para verificar:
- Comportamiento de NQB-AT-GEN-0110 sin y con Génesis 44:18;
- Manejo de fallos de API como NO_CONCLUYENTE (sin generar falsos REQUIERE_CORRECCION);
- Comprobación de las 3 preguntas de Génesis 31;
- Verificación de no interpretar artículos como números ni palabras iniciales como nombres.
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

    # --- REGRESIÓN ESPECÍFICA NQB-AT-GEN-0110 (Génesis 44:33-34 y 44:18) ---

    def test_regression_nqb_0110_without_and_with_additional_ref(self) -> None:
        """Demuestra el diagnóstico de NQB-AT-GEN-0110 sin y con Génesis 44:18."""
        q_canonical = self.get_real_question("NQB-AT-GEN-0110")
        self.assertEqual(q_canonical["reference"], "Génesis 44:33-34")
        self.assertEqual(q_canonical["opcion_a"], "Judá")
        self.assertIn("Génesis 44:18", q_canonical["additional_references"])

        # 1. Mutación: Sin Génesis 44:18 -> REQUIERE_CORRECCION (Judá no aparece en 33-34)
        q_without = copy.deepcopy(q_canonical)
        q_without["additional_references"] = []
        verse_map_33_34 = {
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_without = evaluate_question(q_without, verse_map_33_34)
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res_without["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res_without["controles_superados"]["control_rango_suficiente"], "FAIL")

        # 2. Con additional_references=["Génesis 44:18"] canónico -> Desaparecen los FAIL y valida 'Judá'
        verse_map_with_18 = {
            18: "Entonces Judá se acercó a él, y dijo: ¡Ay, señor mío! te ruego que permitas que hable tu siervo una palabra en oídos de mi señor...",
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_with = evaluate_question(q_canonical, verse_map_with_18)
        self.assertEqual(res_with["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res_with["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res_with["estado"], "VERIFICADO")

    # --- MANEJO DE ERROR DE API VS ERROR DEL BANCO ---

    def test_api_failure_produces_inconclusive_not_requires_correction(self) -> None:
        """Cuando un capítulo no se puede obtener (verse_map={}), produce NO_CONCLUYENTE, nunca REQUIERE_CORRECCION."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        # Simula verse_map vacío por 429 / error de red
        res = evaluate_question(q, {})
        self.assertEqual(res["estado"], "NO_CONCLUYENTE")
        self.assertEqual(res["controles_superados"]["control_referencia_existencia"], "UNKNOWN")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "UNKNOWN")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASOS DE GÉNESIS 31 EVALUADOS CON TEXTO REAL ---

    def test_genesis_31_questions_evaluate_when_chapter_fetched(self) -> None:
        """Verifica que las 3 preguntas de Génesis 31 se evalúen al disponer del texto."""
        # NQB-AT-GEN-0050: Génesis 31:19
        q50 = self.get_real_question("NQB-AT-GEN-0050")
        v50 = {19: "Pero Labán había ido a trasquilar sus ovejas; y Raquel hurtó los ídolos de su padre."}
        res50 = evaluate_question(q50, v50)
        self.assertEqual(res50["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res50["controles_superados"]["control_rango_suficiente"], "PASS")

        # NQB-AT-GEN-0106: Génesis 31:41
        q106 = self.get_real_question("NQB-AT-GEN-0106")
        v106 = {41: "Así he estado veinte años en tu casa; catorce años te serví por tus dos hijas, y seis años por tu ganado, y has cambiado mi salario diez veces."}
        res106 = evaluate_question(q106, v106)
        self.assertEqual(res106["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res106["estado"], "VERIFICADO")

        # NQB-AT-GEN-0051: Génesis 31:48-49
        q51 = self.get_real_question("NQB-AT-GEN-0051")
        v51 = {
            48: "Y dijo Labán: Este majano es testigo hoy entre nosotros dos; por eso fue llamado su nombre Galaad;",
            49: "y Mizpa, por cuanto dijo: Atalaya Jehová entre ti y mí, cuando nos apartemos el uno del otro.",
        }
        res51 = evaluate_question(q51, v51)
        self.assertEqual(res51["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res51["estado"], "VERIFICADO")

    # --- PRUEBAS DE UTILIDADES NUMÉRICAS Y ARTÍCULOS ---

    def test_extract_numbers_article_vs_quantity(self) -> None:
        """'un/una' no debe extraer número 1 cuando funciona como artículo indeterminado."""
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
        q["opcion_a"] = "Crear los cielos y la tierra"
        q["correct_answer"] = "Crear los cielos y la tierra"
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
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
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "UNKNOWN")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS NEGATIVAS OBLIGATORIAS (MUTACIONES CONTROLADAS) ---

    def test_negative_incorrect_age_mutated(self) -> None:
        """Mutación negativa sobre NQB-AT-GEN-0084: 950 años en vez de 969 -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0084")
        q["opcion_a"] = "950 años"
        q["correct_answer"] = "950 años"
        verse_map = {27: "Fueron, pues, todos los días de Matusalén novecientos sesenta y nueve años; y murió."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")

    def test_negative_incorrect_character_mutated(self) -> None:
        """Mutación negativa: personaje bíblico ajeno al pasaje en opción A -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        q["opcion_a"] = "Moisés"
        q["correct_answer"] = "Moisés"
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")

    def test_negative_incorrect_place_mutated(self) -> None:
        """Mutación negativa sobre NQB-AT-GEN-0076 (Génesis 8:4): lugar bíblico contradictorio -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0076")
        self.assertEqual(q["reference"], "Génesis 8:4")
        q["opcion_a"] = "Montes de Sinaí"
        q["correct_answer"] = "Montes de Sinaí"
        verse_map = {4: "Y reposó el arca en el mes séptimo, a los diecisiete días del mes, sobre los montes de Ararat."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_lugares"], "FAIL")

    def test_negative_duplicate_distractor_mutated(self) -> None:
        """Mutación negativa: distractor duplicado e idéntico a opción A -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0001")
        q["opcion_b"] = q["opcion_a"]
        verse_map = {1: "En el principio creó Dios los cielos y la tierra."}
        res = evaluate_question(q, verse_map)
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res["controles_superados"]["control_distractores_invalidos"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_sin_ambiguedad"], "FAIL")

    def test_negative_missing_additional_reference_mutated(self) -> None:
        """Mutación negativa sobre NQB-AT-GEN-0031: eliminamos additional_references -> FAIL."""
        q = self.get_real_question("NQB-AT-GEN-0031")
        q["additional_references"] = []
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
