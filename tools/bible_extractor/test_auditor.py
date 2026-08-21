#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Carga preguntas reales directamente desde genesis-master-input.json,
exodus-master-input.json y leviticus-master-input.json (si existe), realizando
mutaciones controladas sobre copias profundas (deepcopy) para verificar:
- Soporte multilibro (Génesis, Éxodo, Levítico);
- NQB-AT-LEV-0019: rango aislado 8:12 insuficiente vs contexto 8:10 con Moisés;
- NQB-AT-LEV-0038: suertes sobre machos cabríos no produce falso FAIL;
- NQB-AT-LEV-0065: período descriptivo 'un año de reposo' no produce falso FAIL contra 7;
- NQB-AT-EXO-0003 (Nilo / río);
- NQB-AT-EXO-0027 (Egipto como marco ambiental);
- NQB-AT-EXO-0074 (Dos corderos, uno...);
- Diagnóstico de NQB-AT-GEN-0110 sin y con Génesis 44:18;
- Manejo de fallos de API como NO_CONCLUYENTE;
- Pruebas negativas estrictas de contradicción objetiva en números, lugares y entidades.
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditor import evaluate_question, run_audit, extract_numbers, normalize, detect_book_key

GENESIS_PATH = Path(__file__).parent / "genesis-master-input.json"
EXODUS_PATH = Path(__file__).parent / "exodus-master-input.json"
LEVITICUS_PATH = Path(__file__).parent / "leviticus-master-input.json"


class TestAuditorCanonical(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw_gen = json.loads(GENESIS_PATH.read_text(encoding="utf-8"))
        cls.genesis_questions = {q["id"]: q for q in (raw_gen.get("questions", []) if isinstance(raw_gen, dict) else raw_gen)}

        if EXODUS_PATH.exists():
            raw_exo = json.loads(EXODUS_PATH.read_text(encoding="utf-8"))
            cls.exodus_questions = {q["id"]: q for q in (raw_exo.get("questions", []) if isinstance(raw_exo, dict) else raw_exo)}
        else:
            cls.exodus_questions = {}

        if LEVITICUS_PATH.exists():
            raw_lev = json.loads(LEVITICUS_PATH.read_text(encoding="utf-8"))
            cls.leviticus_questions = {q["id"]: q for q in (raw_lev.get("questions", []) if isinstance(raw_lev, dict) else raw_lev)}
        else:
            cls.leviticus_questions = {}

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def get_genesis_question(self, qid: str) -> dict:
        self.assertIn(qid, self.genesis_questions, f"ID '{qid}' no encontrado en genesis-master-input.json")
        return copy.deepcopy(self.genesis_questions[qid])

    def get_exodus_question(self, qid: str) -> dict:
        self.assertIn(qid, self.exodus_questions, f"ID '{qid}' no encontrado en exodus-master-input.json")
        return copy.deepcopy(self.exodus_questions[qid])

    def get_leviticus_question(self, qid: str) -> dict:
        self.assertIn(qid, self.leviticus_questions, f"ID '{qid}' no encontrado en leviticus-master-input.json")
        return copy.deepcopy(self.leviticus_questions[qid])

    # --- TEST GLOBAL DE CONSISTENCIA DE IDs Y REFERENCIAS ---

    def test_global_canonical_id_reference_integrity_genesis(self) -> None:
        """Verifica consistencia de IDs y referencias en Génesis."""
        for qid, q in self.genesis_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_exodus(self) -> None:
        """Verifica consistencia de IDs y referencias en Éxodo."""
        if not self.exodus_questions:
            self.skipTest("exodus-master-input.json no disponible")
        for qid, q in self.exodus_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_leviticus(self) -> None:
        """Verifica consistencia de IDs y referencias en Levítico."""
        if not self.leviticus_questions:
            self.skipTest("leviticus-master-input.json no disponible")
        for qid, q in self.leviticus_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    # --- CASO NQB-AT-LEV-0019: LEVÍTICO 8:12 Y REFERENCIA ADICIONAL LEVÍTICO 8:10 ---

    def test_lev_0019_without_and_with_additional_reference(self) -> None:
        """NQB-AT-LEV-0019: 8:12 aislado produce REQUIERE_CORRECCION; con 8:10 valida a Moisés."""
        q = self.get_leviticus_question("NQB-AT-LEV-0019")
        self.assertEqual(q["reference"], "Levítico 8:12")
        self.assertEqual(q["opcion_a"], "Moisés")

        # 1. Rango aislado 8:12 -> Falta el sujeto Moisés (FAIL)
        v12_only = {12: "Y derramó del aceite de la unción sobre la cabeza de Aarón, y lo ungió para santificarlo."}
        res_without = evaluate_question(q, v12_only, book_key="levitico")
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res_without["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res_without["controles_superados"]["control_rango_suficiente"], "FAIL")

        # 2. Con additional_references=["Levítico 8:10"] -> Moisés presente en v10 (PASS)
        q_with = copy.deepcopy(q)
        q_with["additional_references"] = ["Levítico 8:10"]
        v_with_10 = {
            10: "Y tomó Moisés el aceite de la unción y ungió el tabernáculo, y todas las cosas que estaban en él, y las santificó.",
            12: "Y derramó del aceite de la unción sobre la cabeza de Aarón, y lo ungió para santificarlo.",
        }
        res_with = evaluate_question(q_with, v_with_10, book_key="levitico")
        self.assertEqual(res_with["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res_with["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertNotEqual(res_with["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0038: CONSTRUCCIÓN DISTRIBUTIVA EN LEVÍTICO 16:8-10 ---

    def test_positive_lev_0038_distributive_uno_otro(self) -> None:
        """NQB-AT-LEV-0038: 'Uno para Dios y otro para Azazel' no extrae número 1 contradictorio."""
        q = self.get_leviticus_question("NQB-AT-LEV-0038")
        self.assertEqual(q["reference"], "Levítico 16:8-10")
        verse_map = {
            8: "Y echará suertes Aarón sobre los dos machos cabríos; una suerte por Jehová, y otra suerte por Azazel.",
            9: "Y hará traer Aarón el macho cabrío sobre el cual cayere la suerte por Jehová, y lo ofrecerá en expiación.",
            10: "Mas el macho cabrío sobre el cual cayere la suerte por Azazel, lo presentará vivo delante de Jehová...",
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_negative_lev_0038_contradictory_number(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0038: cantidad explícita contradictoria produce FAIL."""
        q = self.get_leviticus_question("NQB-AT-LEV-0038")
        q["opcion_a"] = "Cinco machos cabríos para Jehová y tres para Azazel"
        q["correct_answer"] = "Cinco machos cabríos para Jehová y tres para Azazel"
        verse_map = {
            8: "Y echará suertes Aarón sobre los dos machos cabríos; una suerte por Jehová, y otra suerte por Azazel.",
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0065: PERÍODO DESCRIPTIVO EN LEVÍTICO 25:4 ---

    def test_positive_lev_0065_qualitative_period(self) -> None:
        """NQB-AT-LEV-0065: 'un año de reposo' no genera contradicción cuantitativa contra 7."""
        q = self.get_leviticus_question("NQB-AT-LEV-0065")
        self.assertEqual(q["reference"], "Levítico 25:4")
        verse_map = {
            4: "pero el séptimo año la tierra tendrá reposo, sábado de reposo para Jehová; no sembrarás tu tierra, ni podarás tu viña."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertNotEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_negative_lev_0065_contradictory_period(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0065: cifra errónea explícita (diez años de reposo)."""
        q = self.get_leviticus_question("NQB-AT-LEV-0065")
        q["opcion_a"] = "Debía tener diez años de reposo"
        q["correct_answer"] = "Debía tener diez años de reposo"
        verse_map = {
            4: "pero el séptimo año la tierra tendrá reposo, sábado de reposo para Jehová..."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASOS ÉXODO (NILO, EGIPTO, CANTIDADES) ---

    def test_positive_exo_0003_nilo_rio_equivalence(self) -> None:
        q = self.get_exodus_question("NQB-AT-EXO-0003")
        verse_map = {22: "Entonces Faraón mandó a todo su pueblo, diciendo: Echad en el río a todo hijo que nazca, y a toda hija preservad la vida."}
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_positive_exo_0027_ambient_place_egypt(self) -> None:
        q = self.get_exodus_question("NQB-AT-EXO-0027")
        verse_map = {
            24: "Entonces Faraón hizo llamar a Moisés, y dijo: Id, servid a Jehová; solamente queden vuestras ovejas y vuestras vacas; vayan también vuestros niños con vosotros.",
            25: "Y Moisés respondió: Tú también nos darás sacrificios y holocaustos que sacrifiquemos para Jehová nuestro Dios.",
            26: "Nuestros ganados irán también con nosotros; no quedará ni una pezuña...",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_positive_exo_0074_compound_numbers_dos_uno(self) -> None:
        q = self.get_exodus_question("NQB-AT-EXO-0074")
        verse_map = {
            38: "Esto es lo que ofrecerás sobre el altar: dos corderos de un año cada día, continuamente.",
            39: "Ofrecerás uno de los corderos por la mañana, y el otro cordero ofrecerás a la caída de la tarde.",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    # --- REGRESIÓN ESPECÍFICA NQB-AT-GEN-0110 (Génesis 44:33-34 y 44:18) ---

    def test_regression_nqb_0110_without_and_with_additional_ref(self) -> None:
        q_canonical = self.get_genesis_question("NQB-AT-GEN-0110")
        q_without = copy.deepcopy(q_canonical)
        q_without["additional_references"] = []
        verse_map_33_34 = {
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_without = evaluate_question(q_without, verse_map_33_34, book_key="genesis")
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")

        verse_map_with_18 = {
            18: "Entonces Judá se acercó a él, y dijo: ¡Ay, señor mío! te ruego que permitas que hable tu siervo una palabra en oídos de mi señor...",
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_with = evaluate_question(q_canonical, verse_map_with_18, book_key="genesis")
        self.assertEqual(res_with["estado"], "VERIFICADO")

    # --- MANEJO DE ERROR DE API VS ERROR DEL BANCO ---

    def test_api_failure_produces_inconclusive_not_requires_correction(self) -> None:
        q = self.get_genesis_question("NQB-AT-GEN-0001")
        res = evaluate_question(q, {}, book_key="genesis")
        self.assertEqual(res["estado"], "NO_CONCLUYENTE")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")


if __name__ == "__main__":
    unittest.main()
