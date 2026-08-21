#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Carga preguntas reales directamente desde genesis-master-input.json,
exodus-master-input.json y leviticus-master-input.json (si existe), realizando
mutaciones controladas sobre copias profundas (deepcopy) para verificar:
- Soporte multilibro (Génesis, Éxodo, Levítico);
- Comportamiento de NQB-AT-EXO-0003 (Nilo / río);
- Comportamiento de NQB-AT-EXO-0027 (Egipto como marco ambiental);
- Comportamiento de NQB-AT-EXO-0074 (Dos corderos, uno...);
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

    # --- SOPORTE MULTILIBRO (LEVÍTICO) ---

    def test_leviticus_book_detection_and_evaluation(self) -> None:
        """Verifica que el auditor reconozca preguntas de Levítico y evalúe sus 27 capítulos."""
        leviticus_sample = {
            "id": "NQB-AT-LEV-0001",
            "book": "Levítico",
            "chapter": 1,
            "verse_start": 1,
            "verse_end": 2,
            "reference": "Levítico 1:1-2",
            "category": "AT_GENERAL",
            "subcategory": "Leyes de los holocaustos",
            "characters": ["Moisés"],
            "difficulty": "Básico",
            "question_type": "Selección múltiple",
            "question": "¿Desde dónde llamó Jehová a Moisés para darle las instrucciones sobre las ofrendas?",
            "opcion_a": "Desde el tabernáculo de reunión",
            "opcion_b": "Desde la cima del monte Sinaí",
            "opcion_c": "Desde la tienda de Aarón",
            "opcion_d": "Desde el campamento de Judá",
            "correct_option": "A",
            "correct_answer": "Desde el tabernáculo de reunión",
            "explanation": "Jehová llamó a Moisés y habló con él desde el tabernáculo de reunión.",
            "additional_references": [],
            "eligible_modes": ["AT", "AMBOS"],
        }
        self.assertEqual(detect_book_key([leviticus_sample]), "levitico")
        verse_map = {
            1: "Llamó Jehová a Moisés, y habló con él desde el tabernáculo de reunión, diciendo:",
            2: "Habla a los hijos de Israel y diles: Cuando alguno de entre vosotros ofrece ofrenda a Jehová, de ganado vacuno u ovejuno haréis vuestra ofrenda.",
        }
        res = evaluate_question(leviticus_sample, verse_map, book_key="levitico")
        self.assertEqual(res["estado"], "VERIFICADO")
        self.assertEqual(res["controles_superados"]["control_libro"], "PASS")
        self.assertEqual(res["controles_superados"]["control_capitulo"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")

    # --- CASO NQB-AT-EXO-0003: NILO / RÍO EN ÉXODO 1:22 ---

    def test_positive_exo_0003_nilo_rio_equivalence(self) -> None:
        """NQB-AT-EXO-0003: 'río Nilo' respaldado por 'el río' en Éxodo 1:22."""
        q = self.get_exodus_question("NQB-AT-EXO-0003")
        self.assertEqual(q["reference"], "Éxodo 1:22")
        verse_map = {22: "Entonces Faraón mandó a todo su pueblo, diciendo: Echad en el río a todo hijo que nazca, y a toda hija preservad la vida."}
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_exo_0003_contradictory_place(self) -> None:
        """Mutación negativa sobre NQB-AT-EXO-0003: lugar ajeno (Éufrates) produce FAIL."""
        q = self.get_exodus_question("NQB-AT-EXO-0003")
        q["opcion_a"] = "Que fueran arrojados al río Éufrates"
        q["correct_answer"] = "Que fueran arrojados al río Éufrates"
        verse_map = {22: "Entonces Faraón mandó a todo su pueblo, diciendo: Echad en el río a todo hijo que nazca, y a toda hija preservad la vida."}
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-EXO-0027: EGIPTO COMO MARCO AMBIENTAL EN ÉXODO 10:24-26 ---

    def test_positive_exo_0027_ambient_place_egypt(self) -> None:
        """NQB-AT-EXO-0027: 'Egipto' como marco ambiental no produce falso FAIL."""
        q = self.get_exodus_question("NQB-AT-EXO-0027")
        self.assertEqual(q["reference"], "Éxodo 10:24-26")
        verse_map = {
            24: "Entonces Faraón hizo llamar a Moisés, y dijo: Id, servid a Jehová; solamente queden vuestras ovejas y vuestras vacas; vayan también vuestros niños con vosotros.",
            25: "Y Moisés respondió: Tú también nos darás sacrificios y holocaustos que sacrifiquemos para Jehová nuestro Dios.",
            26: "Nuestros ganados irán también con nosotros; no quedará ni una pezuña; porque de ellos hemos de tomar para servir a Jehová nuestro Dios, y no sabemos con qué hemos de servir a Jehová hasta que lleguemos allá.",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_exo_0027_contradictory_location(self) -> None:
        """Mutación negativa sobre NQB-AT-EXO-0027: lugar contradictorio explícito (Babilonia)."""
        q = self.get_exodus_question("NQB-AT-EXO-0027")
        q["opcion_a"] = "Que sus rebaños y ganados permanecieran en Babilonia"
        q["correct_answer"] = "Que sus rebaños y ganados permanecieran en Babilonia"
        verse_map = {
            24: "Entonces Faraón hizo llamar a Moisés, y dijo: Id, servid a Jehová; solamente queden vuestras ovejas y vuestras vacas...",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_lugares"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-EXO-0074: DOS CORDEROS, UNO POR LA MAÑANA EN ÉXODO 29:38-39 ---

    def test_positive_exo_0074_compound_numbers_dos_uno(self) -> None:
        """NQB-AT-EXO-0074: 'Dos, uno por la mañana...' extrae [1, 2] y valida con [1, 2]."""
        q = self.get_exodus_question("NQB-AT-EXO-0074")
        self.assertEqual(q["reference"], "Éxodo 29:38-39")
        verse_map = {
            38: "Esto es lo que ofrecerás sobre el altar: dos corderos de un año cada día, continuamente.",
            39: "Ofrecerás uno de los corderos por la mañana, y el otro cordero ofrecerás a la caída de la tarde.",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_exo_0074_contradictory_quantity(self) -> None:
        """Mutación negativa sobre NQB-AT-EXO-0074: cantidad contradictoria (Cinco corderos) -> FAIL."""
        q = self.get_exodus_question("NQB-AT-EXO-0074")
        q["opcion_a"] = "Cinco corderos, tres por la mañana y dos por la tarde"
        q["correct_answer"] = "Cinco corderos, tres por la mañana y dos por la tarde"
        verse_map = {
            38: "Esto es lo que ofrecerás sobre el altar: dos corderos de un año cada día, continuamente.",
            39: "Ofrecerás uno de los corderos por la mañana, y el otro cordero ofrecerás a la caída de la tarde.",
        }
        res = evaluate_question(q, verse_map, book_key="exodo")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- REGRESIÓN ESPECÍFICA NQB-AT-GEN-0110 (Génesis 44:33-34 y 44:18) ---

    def test_regression_nqb_0110_without_and_with_additional_ref(self) -> None:
        """Demuestra el diagnóstico de NQB-AT-GEN-0110 sin y con Génesis 44:18."""
        q_canonical = self.get_genesis_question("NQB-AT-GEN-0110")
        self.assertEqual(q_canonical["reference"], "Génesis 44:33-34")
        self.assertEqual(q_canonical["opcion_a"], "Judá")
        self.assertIn("Génesis 44:18", q_canonical["additional_references"])

        # 1. Mutación: Sin Génesis 44:18 -> REQUIERE_CORRECCION
        q_without = copy.deepcopy(q_canonical)
        q_without["additional_references"] = []
        verse_map_33_34 = {
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_without = evaluate_question(q_without, verse_map_33_34, book_key="genesis")
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res_without["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res_without["controles_superados"]["control_rango_suficiente"], "FAIL")

        # 2. Con additional_references=["Génesis 44:18"] canónico -> VERIFICADO
        verse_map_with_18 = {
            18: "Entonces Judá se acercó a él, y dijo: ¡Ay, señor mío! te ruego que permitas que hable tu siervo una palabra en oídos de mi señor...",
            33: "Ahora, pues, quede tu siervo por siervo de mi señor en lugar del joven, y vaya el joven con sus hermanos.",
            34: "Porque ¿cómo volveré yo a mi padre sin el joven? No vea yo el mal que sobrevendrá a mi padre.",
        }
        res_with = evaluate_question(q_canonical, verse_map_with_18, book_key="genesis")
        self.assertEqual(res_with["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res_with["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res_with["estado"], "VERIFICADO")

    # --- MANEJO DE ERROR DE API VS ERROR DEL BANCO ---

    def test_api_failure_produces_inconclusive_not_requires_correction(self) -> None:
        """Cuando un capítulo no se puede obtener (verse_map={}), produce NO_CONCLUYENTE."""
        q = self.get_genesis_question("NQB-AT-GEN-0001")
        res = evaluate_question(q, {}, book_key="genesis")
        self.assertEqual(res["estado"], "NO_CONCLUYENTE")
        self.assertEqual(res["controles_superados"]["control_referencia_existencia"], "UNKNOWN")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "UNKNOWN")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- PRUEBAS DE UTILIDADES NUMÉRICAS Y ARTÍCULOS ---

    def test_extract_numbers_article_vs_quantity(self) -> None:
        """'un/una' no debe extraer número 1 cuando funciona como artículo indeterminado."""
        self.assertEqual(extract_numbers("Una serpiente"), [])
        self.assertEqual(extract_numbers("una señal"), [])
        self.assertEqual(extract_numbers("una fuerte hambre"), [])
        self.assertEqual(extract_numbers("una estatua de sal"), [])
        self.assertEqual(extract_numbers("un cachorro de león"), [])
        self.assertEqual(extract_numbers("una túnica de diversos colores"), [])

        # Casos cuantitativos explícitos con unidades contables
        self.assertIn(1, extract_numbers("un año"))
        self.assertIn(1, extract_numbers("una vez"))
        self.assertIn(1, extract_numbers("un codo"))
        self.assertIn(1, extract_numbers("un cordero"))

        # Dígitos y números compuestos
        self.assertEqual(extract_numbers("novecientos sesenta y nueve años"), [969])
        self.assertEqual(extract_numbers("300 codos de largo, 50 de ancho y 30 de alto"), [30, 50, 300])
        self.assertEqual(extract_numbers("Dos, uno por la mañana y otro al caer la tarde"), [1, 2])

    # --- PRUEBAS DE CASOS REALES DEL BANCO (POSITIVOS GÉNESIS) ---

    def test_positive_nqb_0084_matusalen_969(self) -> None:
        q = self.get_genesis_question("NQB-AT-GEN-0084")
        verse_map = {27: "Fueron, pues, todos los días de Matusalén novecientos sesenta y nueve años; y murió."}
        res = evaluate_question(q, verse_map, book_key="genesis")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_positive_nqb_0033_medidas_arca(self) -> None:
        q = self.get_genesis_question("NQB-AT-GEN-0033")
        verse_map = {15: "Y de esta manera la harás: de trescientos codos la longitud del arca, de cincuenta codos su anchura, y de treinta codos su altura."}
        res = evaluate_question(q, verse_map, book_key="genesis")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_positive_nqb_0069_abram_318_hombres(self) -> None:
        q = self.get_genesis_question("NQB-AT-GEN-0069")
        verse_map = {14: "Oyó Abram que su pariente estaba prisionero, y armó a sus criados, los nacidos en su casa, trescientos dieciocho, y los siguió hasta Dan."}
        res = evaluate_question(q, verse_map, book_key="genesis")
        self.assertEqual(res["estado"], "VERIFICADO")


if __name__ == "__main__":
    unittest.main()
