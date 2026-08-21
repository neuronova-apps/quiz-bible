#!/usr/bin/env python3
"""Pruebas unitarias y de regresión para el auditor bíblico semántico RVR1960.

Carga preguntas reales directamente desde genesis-master-input.json,
exodus-master-input.json, leviticus-master-input.json y numbers-master-input.json,
realizando mutaciones controladas sobre copias profundas (deepcopy) para verificar:
- Soporte multilibro (Génesis, Éxodo, Levítico, Números);
- Tratamiento estricto de artículos indefinidos 'un/una' frente a cantidades reales (NUM-0009, NUM-0095, NUM-0058, NUM-0064, NUM-0088);
- Preposición 'sin' no detectada como falso topónimo (NUM-0012, NUM-0041, NUM-0073);
- Equivalencia editorial de nombres propios RVR1960 (Miriam ↔ María en NUM-0026, NUM-0027, NUM-0044; Sihón ↔ Sehón en NUM-0051);
- Parsing de números compuestos grandes (601 730 en NUM-0062) y mutación negativa;
- División en dos partes / partir por mitad (NUM-0076) y mutación negativa;
- NQB-AT-LEV-0079: 'La décima parte' vs diezmo de la tierra en Levítico 27:30;
- NQB-AT-LEV-0079 negativo: 'La quinta parte' produce FAIL;
- NQB-AT-LEV-0080: 'Cada décimo animal' vs concepto de diezmo/vara en Levítico 27:32;
- NQB-AT-LEV-0080 negativo: 'Cada séptimo animal' produce FAIL;
- No generación automática de 10 ante apariciones no cuantitativas de 'diezmo';
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

from auditor import evaluate_question, run_audit, extract_numbers, normalize, detect_book_key, token_matches_text, BOOK_CONFIGS

GENESIS_PATH = Path(__file__).parent / "genesis-master-input.json"
EXODUS_PATH = Path(__file__).parent / "exodus-master-input.json"
LEVITICUS_PATH = Path(__file__).parent / "leviticus-master-input.json"
NUMBERS_PATH = Path(__file__).parent / "numbers-master-input.json"
DEUTERONOMY_PATH = Path(__file__).parent / "deuteronomy-master-input.json"
JOSHUA_PATH = Path(__file__).parent / "joshua-master-input.json"
JUDGES_PATH = Path(__file__).parent / "judges-master-input.json"
RUTH_PATH = Path(__file__).parent / "ruth-master-input.json"
SAMUEL1_PATH = Path(__file__).parent / "1samuel-master-input.json"
SAMUEL2_PATH = Path(__file__).parent / "2samuel-master-input.json"


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

        if NUMBERS_PATH.exists():
            raw_num = json.loads(NUMBERS_PATH.read_text(encoding="utf-8"))
            cls.numbers_questions = {q["id"]: q for q in (raw_num.get("questions", []) if isinstance(raw_num, dict) else raw_num)}
        else:
            cls.numbers_questions = {}

        if DEUTERONOMY_PATH.exists():
            raw_deut = json.loads(DEUTERONOMY_PATH.read_text(encoding="utf-8"))
            cls.deuteronomy_questions = {q["id"]: q for q in (raw_deut.get("questions", []) if isinstance(raw_deut, dict) else raw_deut)}
        else:
            cls.deuteronomy_questions = {}

        if JOSHUA_PATH.exists():
            raw_jos = json.loads(JOSHUA_PATH.read_text(encoding="utf-8"))
            cls.joshua_questions = {q["id"]: q for q in (raw_jos.get("questions", []) if isinstance(raw_jos, dict) else raw_jos)}
        else:
            cls.joshua_questions = {}

        if JUDGES_PATH.exists():
            raw_jue = json.loads(JUDGES_PATH.read_text(encoding="utf-8"))
            cls.judges_questions = {q["id"]: q for q in (raw_jue.get("questions", []) if isinstance(raw_jue, dict) else raw_jue)}
        else:
            cls.judges_questions = {}

        if RUTH_PATH.exists():
            raw_rut = json.loads(RUTH_PATH.read_text(encoding="utf-8"))
            cls.ruth_questions = {q["id"]: q for q in (raw_rut.get("questions", []) if isinstance(raw_rut, dict) else raw_rut)}
        else:
            cls.ruth_questions = {}

        if SAMUEL1_PATH.exists():
            raw_1sa = json.loads(SAMUEL1_PATH.read_text(encoding="utf-8"))
            cls.samuel1_questions = {q["id"]: q for q in (raw_1sa.get("questions", []) if isinstance(raw_1sa, dict) else raw_1sa)}
        else:
            cls.samuel1_questions = {}

        if SAMUEL2_PATH.exists():
            raw_2sa = json.loads(SAMUEL2_PATH.read_text(encoding="utf-8"))
            cls.samuel2_questions = {q["id"]: q for q in (raw_2sa.get("questions", []) if isinstance(raw_2sa, dict) else raw_2sa)}
        else:
            cls.samuel2_questions = {}

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

    def get_numbers_question(self, qid: str) -> dict:
        self.assertIn(qid, self.numbers_questions, f"ID '{qid}' no encontrado en numbers-master-input.json")
        return copy.deepcopy(self.numbers_questions[qid])

    def get_deuteronomy_question(self, qid: str) -> dict:
        self.assertIn(qid, self.deuteronomy_questions, f"ID '{qid}' no encontrado en deuteronomy-master-input.json")
        return copy.deepcopy(self.deuteronomy_questions[qid])

    def get_joshua_question(self, qid: str) -> dict:
        self.assertIn(qid, self.joshua_questions, f"ID '{qid}' no encontrado en joshua-master-input.json")
        return copy.deepcopy(self.joshua_questions[qid])

    def get_judges_question(self, qid: str) -> dict:
        self.assertIn(qid, self.judges_questions, f"ID '{qid}' no encontrado en judges-master-input.json")
        return copy.deepcopy(self.judges_questions[qid])

    def get_ruth_question(self, qid: str) -> dict:
        self.assertIn(qid, self.ruth_questions, f"ID '{qid}' no encontrado en ruth-master-input.json")
        return copy.deepcopy(self.ruth_questions[qid])

    def get_1samuel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.samuel1_questions, f"ID '{qid}' no encontrado en 1samuel-master-input.json")
        return copy.deepcopy(self.samuel1_questions[qid])

    def get_2samuel_question(self, qid: str) -> dict:
        self.assertIn(qid, self.samuel2_questions, f"ID '{qid}' no encontrado en 2samuel-master-input.json")
        return copy.deepcopy(self.samuel2_questions[qid])

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

    def test_global_canonical_id_reference_integrity_numbers(self) -> None:
        """Verifica consistencia de IDs y referencias en Números."""
        if not self.numbers_questions:
            self.skipTest("numbers-master-input.json no disponible")
        for qid, q in self.numbers_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_deuteronomy(self) -> None:
        """Verifica consistencia de IDs y referencias en Deuteronomio."""
        if not self.deuteronomy_questions:
            self.skipTest("deuteronomy-master-input.json no disponible")
        for qid, q in self.deuteronomy_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_joshua(self) -> None:
        """Verifica consistencia de IDs y referencias en Josué."""
        if not self.joshua_questions:
            self.skipTest("joshua-master-input.json no disponible")
        for qid, q in self.joshua_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_judges(self) -> None:
        """Verifica consistencia de IDs y referencias en Jueces si el archivo está presente."""
        if not self.judges_questions:
            self.skipTest("judges-master-input.json aún no presente")
        for qid, q in self.judges_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_ruth(self) -> None:
        """Verifica consistencia de IDs y referencias en Rut."""
        if not self.ruth_questions:
            self.skipTest("ruth-master-input.json aún no presente")
        self.assertEqual(len(self.ruth_questions), 40)
        for qid, q in self.ruth_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_1samuel(self) -> None:
        """Verifica consistencia de IDs y referencias en 1 Samuel."""
        if not self.samuel1_questions:
            self.skipTest("1samuel-master-input.json aún no presente")
        self.assertEqual(len(self.samuel1_questions), 100)
        for qid, q in self.samuel1_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_global_canonical_id_reference_integrity_2samuel(self) -> None:
        """Verifica consistencia de IDs y referencias en 2 Samuel."""
        if not self.samuel2_questions:
            self.skipTest("2samuel-master-input.json aún no presente")
        self.assertEqual(len(self.samuel2_questions), 84)
        for qid, q in self.samuel2_questions.items():
            ref = q.get("reference", "")
            ch = q.get("chapter")
            start = q.get("verse_start")
            end = q.get("verse_end", start)
            expected_suffix = f"{ch}:{start}" if start == end else f"{ch}:{start}-{end}"
            self.assertTrue(
                expected_suffix in ref or ref.endswith(expected_suffix),
                f"Referencia inconsistente en {qid}: ref='{ref}', esperada terminada en '{expected_suffix}'"
            )

    def test_numbers_book_detection(self) -> None:
        """Verifica detección de configuración de Números."""
        if not self.numbers_questions:
            self.skipTest("numbers-master-input.json no disponible")
        book_key = detect_book_key(list(self.numbers_questions.values()))
        self.assertEqual(book_key, "numeros")

    def test_deuteronomy_book_detection(self) -> None:
        """Verifica detección de configuración de Deuteronomio."""
        if not self.deuteronomy_questions:
            self.skipTest("deuteronomy-master-input.json no disponible")
        book_key = detect_book_key(list(self.deuteronomy_questions.values()))
        self.assertEqual(book_key, "deuteronomio")

    def test_joshua_book_detection(self) -> None:
        """Verifica detección de configuración de Josué."""
        if not self.joshua_questions:
            self.skipTest("joshua-master-input.json no disponible")
        book_key = detect_book_key(list(self.joshua_questions.values()))
        self.assertEqual(book_key, "josue")

    def test_judges_book_detection(self) -> None:
        """Verifica detección de configuración de Jueces."""
        sample_q = [{"id": "NQB-AT-JUE-0001", "book": "Jueces", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "jueces")

    def test_ruth_book_detection(self) -> None:
        """Verifica detección de configuración de Rut."""
        sample_q = [{"id": "NQB-AT-RUT-0001", "book": "Rut", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "rut")
        self.assertEqual(BOOK_CONFIGS["rut"]["total_chapters"], 4)
        self.assertIn("ruth", BOOK_CONFIGS["rut"]["aliases"])

    def test_1samuel_book_detection(self) -> None:
        """Verifica detección de configuración de 1 Samuel."""
        sample_q = [{"id": "NQB-AT-1SA-0001", "book": "1 Samuel", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "1samuel")
        self.assertEqual(BOOK_CONFIGS["1samuel"]["total_chapters"], 31)
        self.assertIn("1 samuel", BOOK_CONFIGS["1samuel"]["aliases"])

    def test_2samuel_book_detection(self) -> None:
        """Verifica detección de configuración de 2 Samuel."""
        sample_q = [{"id": "NQB-AT-2SA-0001", "book": "2 Samuel", "chapter": 1, "verse_start": 1, "verse_end": 2}]
        book_key = detect_book_key(sample_q)
        self.assertEqual(book_key, "2samuel")
        self.assertEqual(BOOK_CONFIGS["2samuel"]["total_chapters"], 24)
        self.assertIn("2 samuel", BOOK_CONFIGS["2samuel"]["aliases"])

    def test_joshua_0061_with_additional_reference(self) -> None:
        """NQB-AT-JOS-0061: Josué 20:9 con additional_references=['Números 35:15'] se evalúa correctamente."""
        q61 = self.get_joshua_question("NQB-AT-JOS-0061")
        self.assertEqual(q61["reference"], "Josué 20:9")
        v61 = {9: "Estas fueron las ciudades señaladas para todos los hijos de Israel, y para el extranjero que morase entre ellos, para que se acogiese a ellas cualquiera que hiriese a alguno de muerte por yerro, y no muriese a mano del vengador de la sangre, hasta que compareciese delante de la congregación."}
        res61 = evaluate_question(q61, v61, book_key="josue")
        self.assertEqual(res61["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res61["estado"], "VERIFICADO")

    # --- REGRESIONES DE ARTÍCULOS INDEFINIDOS UN / UNA Y FRACCIONES EN NÚMEROS ---

    def test_num_0009_una_quinta_parte_no_spurious_one(self) -> None:
        """NUM-0009: 'Una quinta parte adicional' reconoce quinta=5 sin número 1 espurio."""
        q9 = self.get_numbers_question("NQB-AT-NUM-0009")
        v9 = {7: "confesarán su pecado que cometieron, y compensarán su ofensa enteramente, y añadirán sobre ello la quinta parte, y lo darán a aquel contra quien pecaron."}
        res9 = evaluate_question(q9, v9, book_key="numeros")
        self.assertEqual(res9["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertNotEqual(res9["estado"], "REQUIERE_CORRECCION")

        # Mutación negativa
        q9_neg = copy.deepcopy(q9)
        q9_neg["opcion_a"] = "Una tercera parte adicional"
        q9_neg["correct_answer"] = "Una tercera parte adicional"
        res9_neg = evaluate_question(q9_neg, v9, book_key="numeros")
        self.assertEqual(res9_neg["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res9_neg["estado"], "REQUIERE_CORRECCION")

    def test_num_indefinite_articles_not_converted_to_numbers(self) -> None:
        """Verifica que 'un/una' como artículo indefinido no extraiga cantidad 1 (NUM-0095, NUM-0058, NUM-0064, NUM-0088)."""
        # NUM-0095: Tomó un incensario...
        q95 = self.get_numbers_question("NQB-AT-NUM-0095")
        v95 = {
            46: "Y dijo Moisés a Aarón: Toma el incensario, y pon en él fuego del altar...",
            47: "Entonces tomó Aarón el incensario, como Moisés dijo, y corrió en medio de la congregación...",
            48: "Y se puso entre los muertos y los vivos; y cesó la mortandad."
        }
        res95 = evaluate_question(q95, v95, book_key="numeros")
        self.assertEqual(res95["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res95["estado"], "REQUIERE_CORRECCION")

        # NUM-0058: Una estrella
        q58 = self.get_numbers_question("NQB-AT-NUM-0058")
        v58 = {17: "Lo veré, mas no ahora; lo miraré, mas no de cerca; saldrá estrella de Jacob, y se levantará cetro de Israel..."}
        res58 = evaluate_question(q58, v58, book_key="numeros")
        self.assertEqual(res58["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res58["estado"], "REQUIERE_CORRECCION")

        # NUM-0064: Recibir una propiedad...
        q64 = self.get_numbers_question("NQB-AT-NUM-0064")
        v64 = {
            1: "Vinieron las hijas de Zelofehad hijo de Hefer...",
            2: "y se presentaron delante de Moisés y delante del sacerdote Eleazar...",
            3: "Nuestro padre murió en el desierto...",
            4: "¿Por qué será quitado el nombre de nuestro padre de entre su familia, por no haber tenido hijo? Danos heredad entre los hermanos de nuestro padre."
        }
        res64 = evaluate_question(q64, v64, book_key="numeros")
        self.assertEqual(res64["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res64["estado"], "REQUIERE_CORRECCION")

        # NUM-0088: una muerte sin intención
        q88 = self.get_numbers_question("NQB-AT-NUM-0088")
        v88 = {
            11: "os señalaréis ciudades, ciudades de refugio tendréis, donde huya el homicida que hiriere a alguno de muerte sin intención.",
            12: "Y os serán aquellas ciudades por refugio del vengador, y no morirá el homicida hasta que entre en juicio delante de la congregación."
        }
        res88 = evaluate_question(q88, v88, book_key="numeros")
        self.assertEqual(res88["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertNotEqual(res88["estado"], "REQUIERE_CORRECCION")

    def test_explicit_counting_un_cordero(self) -> None:
        """En preguntas cuantitativas explícitas, 'Un cordero' sí debe extraer 1."""
        nums = extract_numbers("Un cordero", is_quantitative_context=True)
        self.assertIn(1, nums)

    # --- REGRESIONES ESPECÍFICAS DE DEUTERONOMIO ---

    def test_deu_0003_comparative_father_son_metaphor(self) -> None:
        """DEU-0003: 'Como un padre que lleva a su hijo' frente a 'como trae el hombre a su hijo' en Deuteronomio 1:31."""
        q3 = self.get_deuteronomy_question("NQB-AT-DEU-0003")
        v3 = {31: "Y en el desierto has visto que Jehová tu Dios te ha traído, como trae el hombre a su hijo, por todo el camino que habéis andado, hasta llegar a este lugar."}
        res3 = evaluate_question(q3, v3, book_key="deuteronomio")
        self.assertEqual(res3["controles_superados"]["control_relaciones_personajes"], "PASS")
        self.assertEqual(res3["estado"], "VERIFICADO")

    def test_literal_kinship_missing_produces_fail(self) -> None:
        """Pregunta de parentesco literal sin respaldo en el pasaje produce FAIL en control_relaciones_personajes."""
        q_literal = {
            "id": "TEST-KINSHIP-LITERAL",
            "book": "Deuteronomio",
            "chapter": 1,
            "verse_start": 38,
            "verse_end": 38,
            "reference": "Deuteronomio 1:38",
            "question": "¿Qué parentesco tenía Nun respecto de Josué según el texto?",
            "opcion_a": "Era el padre de Josué",
            "opcion_b": "Era el tío",
            "opcion_c": "Era el hermano",
            "opcion_d": "Era el abuelo",
            "correct_option": "A",
            "correct_answer": "Era el padre de Josué",
            "explanation": "Nun era el padre de Josué...",
            "characters": ["Josué", "Nun"],
            "difficulty": "Básico",
            "category": "PERSONAJES_BIBLICOS",
        }
        # 1. Pasaje con 'padre' explícito -> PASS
        v_pass = {38: "Josué hijo de Nun, y su padre Nun le enseñó..."}
        res_pass = evaluate_question(q_literal, v_pass, book_key="deuteronomio")
        self.assertEqual(res_pass["controles_superados"]["control_relaciones_personajes"], "PASS")

        # 2. Pasaje sin 'padre' -> FAIL
        v_fail = {38: "Josué, el cual te sirve, él entrará allá; anímale, porque él la hará heredar a Israel."}
        res_fail = evaluate_question(q_literal, v_fail, book_key="deuteronomio")
        self.assertEqual(res_fail["controles_superados"]["control_relaciones_personajes"], "FAIL")

    def test_deu_0060_action_measure_no_spurious_one(self) -> None:
        """DEU-0060: '¿Qué medida de seguridad...?' con 'Construir una protección...' no extrae 1 espurio."""
        q60 = self.get_deuteronomy_question("NQB-AT-DEU-0060")
        v60 = {8: "Cuando edifiques casa nueva, harás pretil a tu terrado, para que no pongas culpa de sangre sobre tu casa, si de él cayere alguno."}
        res60 = evaluate_question(q60, v60, book_key="deuteronomio")
        self.assertEqual(res60["controles_superados"]["control_numeros_cantidades"], "NOT_APPLICABLE")
        self.assertEqual(res60["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res60["estado"], "VERIFICADO")

    def test_explicit_quant_context_evaluations(self) -> None:
        """Verifica que preguntas con '¿Cuántas...?' y '¿Cuánto debía medir...?' evalúen cantidades correctamente."""
        # Cuántas -> extrae 1
        nums_cuantas = extract_numbers("Una", is_quantitative_context=True)
        self.assertEqual(nums_cuantas, [1])

        # Medida de seguridad (cualitativo) -> no extrae 1
        nums_cual = extract_numbers("Construir una protección", is_quantitative_context=False)
        self.assertEqual(nums_cual, [])

    # --- REGRESIONES ESPECÍFICAS DE NÚMEROS (SIN, MIRIAM, SIHÓN, 601730, MITADES) ---

    def test_num_sin_preposition_not_detected_as_place(self) -> None:
        """Verifica que la preposición 'sin' no se detecte como topónimo (NUM-0012, NUM-0041, NUM-0073)."""
        # NUM-0012: sin pasar navaja
        q12 = self.get_numbers_question("NQB-AT-NUM-0012")
        v12 = {5: "Todos los días del voto de su nazareato no pasará navaja sobre su cabeza; hasta que sean cumplidos los días... dejará crecer su cabello."}
        res12 = evaluate_question(q12, v12, book_key="numeros")
        self.assertNotEqual(res12["controles_superados"]["control_lugares"], "FAIL")
        self.assertEqual(res12["estado"], "VERIFICADO")

        # NUM-0041: sin defecto
        q41 = self.get_numbers_question("NQB-AT-NUM-0041")
        v41 = {2: "Esta es la ordenanza de la ley... una vaca alazana, perfecta, en la cual no haya falta, sobre la cual no se haya puesto yugo;"}
        res41 = evaluate_question(q41, v41, book_key="numeros")
        self.assertNotEqual(res41["controles_superados"]["control_lugares"], "FAIL")
        self.assertNotEqual(res41["estado"], "REQUIERE_CORRECCION")

        # NUM-0073: sin efecto
        q73 = self.get_numbers_question("NQB-AT-NUM-0073")
        v73 = {
            3: "Mas la mujer, cuando hiciere voto a Jehová...",
            4: "si su padre oyere su voto... todos los votos de ella serán firmes...",
            5: "Mas si su padre le vedare el día que oyere... no serán firmes;"
        }
        res73 = evaluate_question(q73, v73, book_key="numeros")
        self.assertNotEqual(res73["controles_superados"]["control_lugares"], "FAIL")
        self.assertEqual(res73["estado"], "VERIFICADO")

    def test_num_miriam_maria_equivalence(self) -> None:
        """Verifica equivalencia Miriam ↔ María en RVR1960 (NUM-0026, NUM-0027, NUM-0044)."""
        q26 = self.get_numbers_question("NQB-AT-NUM-0026")
        v26 = {
            1: "María y Aarón hablaron contra Moisés a causa de la mujer cusita que había tomado...",
            2: "Y dijeron: ¿Solamente por Moisés ha hablado Jehová? ¿No ha hablado también por nosotros? Y lo oyó Jehová."
        }
        res26 = evaluate_question(q26, v26, book_key="numeros")
        self.assertEqual(res26["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertNotEqual(res26["estado"], "REQUIERE_CORRECCION")

        q27 = self.get_numbers_question("NQB-AT-NUM-0027")
        v27 = {10: "Y la nube se apartó del tabernáculo, y he aquí que María estaba leprosa como la nieve; y miró Aarón a María, y he aquí que estaba leprosa."}
        res27 = evaluate_question(q27, v27, book_key="numeros")
        self.assertEqual(res27["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertNotEqual(res27["estado"], "REQUIERE_CORRECCION")

        q44 = self.get_numbers_question("NQB-AT-NUM-0044")
        v44 = {1: "Llegaron los hijos de Israel, toda la congregación, al desierto de Zin, en el mes primero, y acampó el pueblo en Cades; y allí murió María, y allí fue sepultada."}
        res44 = evaluate_question(q44, v44, book_key="numeros")
        self.assertEqual(res44["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res44["estado"], "VERIFICADO")

    def test_num_sihon_sehon_equivalence(self) -> None:
        """Verifica equivalencia Sihón ↔ Sehón (NUM-0051)."""
        q51 = self.get_numbers_question("NQB-AT-NUM-0051")
        v51 = {
            21: "Entonces envió Israel embajadores a Sehón rey de los amorreos, diciendo:",
            22: "Pasaré por tu tierra...",
            23: "Mas Sehón no dejó pasar a Israel...",
            24: "E Israel lo hirió a filo de espada, y tomó su tierra..."
        }
        res51 = evaluate_question(q51, v51, book_key="numeros")
        self.assertEqual(res51["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res51["estado"], "VERIFICADO")

    def test_num_compound_number_601730(self) -> None:
        """Verifica parsing de 601 730 (NUM-0062) y mutación negativa."""
        q62 = self.get_numbers_question("NQB-AT-NUM-0062")
        v62 = {51: "Estos son los contados de los hijos de Israel, seiscientos un mil setecientos treinta."}
        res62 = evaluate_question(q62, v62, book_key="numeros")
        self.assertEqual(res62["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertNotEqual(res62["estado"], "REQUIERE_CORRECCION")

        # Mutación negativa
        q62_neg = copy.deepcopy(q62)
        q62_neg["opcion_a"] = "603 550"
        q62_neg["correct_answer"] = "603 550"
        res62_neg = evaluate_question(q62_neg, v62, book_key="numeros")
        self.assertEqual(res62_neg["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res62_neg["estado"], "REQUIERE_CORRECCION")

    def test_num_division_dos_partes_mitad(self) -> None:
        """Verifica 'En dos partes' vs 'partir por mitad' (NUM-0076) y mutación negativa."""
        q76 = self.get_numbers_question("NQB-AT-NUM-0076")
        v76 = {
            25: "Y Jehová habló a Moisés, diciendo:",
            26: "Toma la cuenta del botín que se ha hecho...",
            27: "Y partirás por mitad el botín entre los que pelearon, los que salieron a la guerra, y toda la congregación."
        }
        res76 = evaluate_question(q76, v76, book_key="numeros")
        self.assertEqual(res76["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res76["estado"], "VERIFICADO")

        # Mutación negativa
        q76_neg = copy.deepcopy(q76)
        q76_neg["opcion_a"] = "En tres partes iguales"
        q76_neg["correct_answer"] = "En tres partes iguales"
        res76_neg = evaluate_question(q76_neg, v76, book_key="numeros")
        self.assertEqual(res76_neg["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res76_neg["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0079: LA DÉCIMA PARTE Y DIEZMO DE LA TIERRA EN LEVÍTICO 27:30 ---

    def test_positive_lev_0079_decima_parte_tithe(self) -> None:
        """NQB-AT-LEV-0079: 'La décima parte' respalda el diezmo de la tierra."""
        q = self.get_leviticus_question("NQB-AT-LEV-0079")
        self.assertEqual(q["reference"], "Levítico 27:30")
        self.assertEqual(q["opcion_a"], "La décima parte")
        verse_map = {
            30: "Y el diezmo de la tierra, así de la simiente de la tierra como del fruto de los árboles, de Jehová es; es cosa dedicada a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_lev_0079_contradictory_fraction(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0079: 'La quinta parte' produce FAIL."""
        q = self.get_leviticus_question("NQB-AT-LEV-0079")
        q["opcion_a"] = "La quinta parte"
        q["correct_answer"] = "La quinta parte"
        verse_map = {
            30: "Y el diezmo de la tierra, así de la simiente de la tierra como del fruto de los árboles, de Jehová es; es cosa dedicada a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    # --- CASO NQB-AT-LEV-0080: CADA DÉCIMO ANIMAL Y DIEZMO EN LEVÍTICO 27:32 ---

    def test_positive_lev_0080_decimo_animal_tithe(self) -> None:
        """NQB-AT-LEV-0080: 'Cada décimo animal' respalda el diezmo del ganado bajo la vara."""
        q = self.get_leviticus_question("NQB-AT-LEV-0080")
        self.assertEqual(q["reference"], "Levítico 27:32")
        self.assertEqual(q["opcion_a"], "Cada décimo animal")
        verse_map = {
            32: "Y todo diezmo de vacas o de ovejas, de todo lo que pasa bajo la vara, el diezmo será consagrado a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "PASS")
        self.assertEqual(res["controles_superados"]["control_opcion_a_correcta"], "PASS")
        self.assertEqual(res["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res["estado"], "VERIFICADO")

    def test_negative_lev_0080_contradictory_number(self) -> None:
        """Mutación negativa sobre NQB-AT-LEV-0080: 'Cada séptimo animal' produce FAIL."""
        q = self.get_leviticus_question("NQB-AT-LEV-0080")
        q["opcion_a"] = "Cada séptimo animal"
        q["correct_answer"] = "Cada séptimo animal"
        verse_map = {
            32: "Y todo diezmo de vacas o de ovejas, de todo lo que pasa bajo la vara, el diezmo será consagrado a Jehová."
        }
        res = evaluate_question(q, verse_map, book_key="levitico")
        self.assertEqual(res["controles_superados"]["control_numeros_cantidades"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_non_quantitative_diezmo_does_not_extract_10_blindly(self) -> None:
        """Mención no cuantitativa de 'diezmo' sin conteo/fracción no produce número 10."""
        text_non_quant = "Y el diezmo de la tierra de Jehová es santificado."
        nums = extract_numbers(text_non_quant, is_quantitative_context=False)
        self.assertNotIn(10, nums)

    # --- CASO NQB-AT-LEV-0019: LEVÍTICO 8:12 Y REFERENCIA ADICIONAL LEVÍTICO 8:10 ---

    def test_lev_0019_without_and_with_additional_reference(self) -> None:
        """NQB-AT-LEV-0019: 8:12 aislado produce REQUIERE_CORRECCION; con 8:10 valida a Moisés."""
        q = self.get_leviticus_question("NQB-AT-LEV-0019")
        self.assertEqual(q["reference"], "Levítico 8:12")
        self.assertEqual(q["opcion_a"], "Moisés")

        # 1. Rango aislado 8:12 -> Falta el sujeto Moisés (FAIL)
        v12_only = {12: "Y derramó del aceite de la unción sobre la cabeza de Aarón, y lo ungió para santificarlo."}
        q_isolated = copy.deepcopy(q)
        q_isolated["additional_references"] = []
        res_without = evaluate_question(q_isolated, v12_only, book_key="levitico")
        self.assertEqual(res_without["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res_without["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res_without["controles_superados"]["control_rango_suficiente"], "FAIL")

        # 2. Con additional_references=["Levítico 8:10"] -> Moisés presente en v10 (PASS)
        v_with_10 = {
            10: "Y tomó Moisés el aceite de la unción y ungió el tabernáculo, y todas las cosas que estaban en él, y las santificó.",
            12: "Y derramó del aceite de la unción sobre la cabeza de Aarón, y lo ungió para santificarlo.",
        }
        res_with = evaluate_question(q, v_with_10, book_key="levitico")
        self.assertEqual(res_with["controles_superados"]["control_nombres_propios"], "PASS")
        self.assertEqual(res_with["controles_superados"]["control_rango_suficiente"], "PASS")
        self.assertEqual(res_with["estado"], "VERIFICADO")

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

    # --- PRUEBAS DE NORMALIZACIÓN MORFOLÓGICA Y SINONIMIA BÍBLICA ---

    def test_token_matches_text_morphological_and_synonyms(self) -> None:
        """Verifica concordancia singular/plural y sinónimos bíblicos genéricos."""
        self.assertTrue(token_matches_text("extranjeros", "morase extranjero entre ellos"))
        self.assertTrue(token_matches_text("ciudades", "ciudad de refugio"))
        self.assertTrue(token_matches_text("otoniel", "otniel tomo quiriat-sefer"))
        self.assertTrue(token_matches_text("sorteada", "repartieron por suerte"))
        self.assertTrue(token_matches_text("combatir", "fueron a pelear contra ellos"))

    def test_joshua_cases_semantic_resolution(self) -> None:
        """Verifica resolución semántica de preguntas representativas de Josué."""
        # NQB-AT-JOS-0046: Otoniel
        q46 = self.get_joshua_question("NQB-AT-JOS-0046")
        v46 = {
            16: "Y dijo Caleb: Al que atacare a Quiriat-sefer, y la tomare, yo le daré a Acsa mi hija por mujer.",
            17: "Y la tomó Otoniel, hijo de Cenaz hermano de Caleb; y él le dio a Acsa su hija por mujer.",
        }
    # --- PRUEBAS DE REGRESIÓN DE JUECES Y GENTILICIOS BÍBLICOS ---

    def test_benjamita_benjamin_demonyms(self) -> None:
        """Verifica equivalencia genérica entre gentilicios bíblicos y nombres de tribus/lugares."""
        self.assertTrue(token_matches_text("benjamin", "aod hijo de gera benjamita"))
        self.assertTrue(token_matches_text("benjamita", "tribu de benjamin"))
        self.assertTrue(token_matches_text("efrain", "monte de los efraimitas"))
        self.assertTrue(token_matches_text("galaad", "jefte galaadita"))
        self.assertTrue(token_matches_text("dan", "familia de los danitas"))

    def test_ordinal_sequence_vs_quantitative(self) -> None:
        """Verifica que 'primero' discursivo/secuencial no genere conteo numérico falso."""
        nums_seq = extract_numbers("Primero que el vellón quedara mojado", is_quantitative_context=False)
        self.assertEqual(nums_seq, [])

        nums_seq2 = extract_numbers("a quien saliera primero de su casa", is_quantitative_context=False)
        self.assertEqual(nums_seq2, [])

        nums_quant = extract_numbers("el séptimo año la tierra tendrá reposo", is_quantitative_context=False)
        self.assertEqual(nums_quant, [7])

        nums_frac = extract_numbers("la décima parte", is_quantitative_context=True)
        self.assertEqual(nums_frac, [10])

    def test_judges_regression_four_cases(self) -> None:
        """Verifica resolución limpia sin FAIL en NQB-AT-JUE-0008, 0020, 0028 y 0094."""
        # JUE-0008: Aod benjamita vs tribu de Benjamín
        q8 = self.get_judges_question("NQB-AT-JUE-0008")
        v8 = {15: "Y clamaron los hijos de Israel a Jehová; y Jehová les levantó un libertador, a Aod hijo de Gera, benjamita, el cual era zurdo..."}
        res8 = evaluate_question(q8, v8, book_key="jueces")
        self.assertNotEqual(res8["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res8["controles_superados"]["control_nombres_propios"], "PASS")

        # JUE-0020: Secuencia de señales de Gedeón
        q20 = self.get_judges_question("NQB-AT-JUE-0020")
        v20 = {
            36: "Y Gedeón dijo a Dios: Si has de salvar a Israel por mi mano, como has dicho,",
            37: "he aquí que yo pondré un vellón de lana en la era; y si el rocío estuviere en el vellón solamente, quedando seca toda la tierra, entonces entenderé que salvarás a Israel por mi mano, como has dicho.",
            38: "Y aconteció así...",
            39: "Mas Gedeón dijo a Dios... Te ruego que solamente el vellón quede seco, y el rocío sobre la tierra.",
            40: "Y aquella noche lo hizo Dios así; sólo el vellón quedó seco, y en toda la tierra hubo rocío."
        }
        res20 = evaluate_question(q20, v20, book_key="jueces")
        self.assertNotEqual(res20["estado"], "REQUIERE_CORRECCION")

        # JUE-0028: Refusal of bread by Succoth to Gideon's men
        q28 = self.get_judges_question("NQB-AT-JUE-0028")
        v28 = {6: "Y los principales de Sucot respondieron: ¿Están ya en tu mano las cabezas de Zeba y de Zalmuna, para que demos pan a tu ejército?"}
        res28 = evaluate_question(q28, v28, book_key="jueces")
        self.assertNotEqual(res28["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res28["controles_superados"]["control_nombres_propios"], "PASS")

        # JUE-0094: Voto de Jefté
        q94 = self.get_judges_question("NQB-AT-JUE-0094")
        v94 = {
            30: "Y Jefté hizo voto a Jehová, diciendo: Si entregares a los amonitas en mis manos,",
            31: "cualquiera que saliere de las puertas de mi casa a recibirme, cuando regrese victorioso de los amonitas, será de Jehová, y lo ofreceré en holocausto."
        }
        res94 = evaluate_question(q94, v94, book_key="jueces")
        self.assertNotEqual(res94["estado"], "REQUIERE_CORRECCION")

    def test_ruth_cases_representative(self) -> None:
        """Verifica evaluación de casos representativos de Rut (efa de cebada, seis medidas, diez ancianos, genealogía)."""
        # RUT-0012: Un efa de cebada (Rut 2:17)
        q12 = self.get_ruth_question("NQB-AT-RUT-0012")
        v12 = {17: "Espigó, pues, en el campo hasta la noche, y desgranó lo que había recogido, y fue como un efa de cebada."}
        res12 = evaluate_question(q12, v12, book_key="rut")
        self.assertNotEqual(res12["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res12["controles_superados"]["control_nombres_propios"], "PASS")

        # RUT-0018: Diez ancianos (Rut 4:1-2)
        q18 = self.get_ruth_question("NQB-AT-RUT-0018")
        v18 = {
            1: "Booz subió a la puerta y se sentó allí...",
            2: "Y él tomó diez varones de los ancianos de la ciudad, y dijo: Sentaos aquí. Y ellos se sentaron."
        }
        res18 = evaluate_question(q18, v18, book_key="rut")
        self.assertNotEqual(res18["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res18["controles_superados"]["control_numeros_cantidades"], "PASS")

    def test_ruth_anaphoric_resolution_rut_0011_and_0033(self) -> None:
        """Verifica que referencias anafóricas/relacionales (su suegra -> Noemí, aquel hombre -> Booz) se resuelvan sin FAIL."""
        # RUT-0011: Booz destaca conducta hacia 'su suegra' (Noemí) en Rut 2:10-12
        q11 = self.get_ruth_question("NQB-AT-RUT-0011")
        v11 = {
            2: "Y Rut la moabita dijo a Noemí: Te ruego que me dejes ir al campo...",
            10: "Ella bajando su rostro se inclinó a tierra...",
            11: "Y respondiendo Booz, le dijo: He sabido todo lo que has hecho con tu suegra después de la muerte de tu marido, y que dejando a tu padre y a tu madre y la tierra donde naciste, has venido a un pueblo que no conociste antes.",
            12: "Jehová recompense tu obra..."
        }
        res11 = evaluate_question(q11, v11, book_key="rut")
        self.assertEqual(res11["estado"], "VERIFICADO")
        self.assertEqual(res11["controles_superados"]["control_nombres_propios"], "PASS")

        # RUT-0033: 'aquel hombre' (Booz) en Rut 3:18
        q33 = self.get_ruth_question("NQB-AT-RUT-0033")
        v33 = {
            2: "¿No es Booz nuestro pariente...?",
            18: "Entonces Noemí dijo: Espérate, hija mía, hasta que sepas cómo se resuelve el caso; porque aquel hombre no descansará hasta que concluya el asunto hoy."
        }
        res33 = evaluate_question(q33, v33, book_key="rut")
        self.assertEqual(res33["estado"], "VERIFICADO")
        self.assertEqual(res33["controles_superados"]["control_nombres_propios"], "PASS")

    def test_anaphoric_character_contradiction_fail(self) -> None:
        """Verifica que un personaje objetivamente contradictorio sin vínculo anafórico genere FAIL."""
        q = self.get_ruth_question("NQB-AT-RUT-0033")
        q["opcion_a"] = "Porque estaba convencida de que Saúl no descansaría hasta resolverlo ese mismo día"
        q["correct_answer"] = q["opcion_a"]
        v33 = {
            18: "Entonces Noemí dijo: Espérate, hija mía, hasta que sepas cómo se resuelve el caso; porque aquel hombre no descansará hasta que concluya el asunto hoy."
        }
        res = evaluate_question(q, v33, book_key="rut")
        self.assertEqual(res["controles_superados"]["control_nombres_propios"], "FAIL")
        self.assertEqual(res["estado"], "REQUIERE_CORRECCION")

    def test_1samuel_regression_and_cases(self) -> None:
        """Verifica casos canónicos clave de 1 Samuel (Ofni/Finees, 30.000, 5 tumores/ratones, 100/200 prepucios, etc.)."""
        # 1SA-0004: Ofni y Finees hijos de Elí (1 Samuel 1:3)
        q4 = self.get_1samuel_question("NQB-AT-1SA-0004")
        v4 = {3: "Y todos los años aquel varón subía de su ciudad para adorar y para ofrecer sacrificios a Jehová de los ejércitos en Silo, donde estaban dos hijos de Elí, Ofni y Finees, sacerdotes de Jehová."}
        res4 = evaluate_question(q4, v4, book_key="1samuel")
        self.assertNotEqual(res4["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res4["controles_superados"]["control_nombres_propios"], "PASS")

        # 1SA-0014: Treinta mil soldados (1 Samuel 4:10)
        q14 = self.get_1samuel_question("NQB-AT-1SA-0014")
        v14 = {10: "Pelearon, pues, los filisteos, e Israel fue vencido, y huyeron cada cual a sus tiendas; y fue hecha muy grande mortandad, pues cayeron de Israel treinta mil hombres de a pie."}
        res14 = evaluate_question(q14, v14, book_key="1samuel")
        self.assertNotEqual(res14["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res14["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1SA-0019: Cinco tumores y cinco ratones de oro (1 Samuel 6:4-5)
        q19 = self.get_1samuel_question("NQB-AT-1SA-0019")
        v19 = {
            4: "Y ellos dijeron: ¿Y qué será la expiación que le pagaremos? Ellos respondieron: Cinco tumores de oro, y cinco ratones de oro, conforme al número de los príncipes de los filisteos...",
            5: "Haréis, pues, figuras de vuestros tumores, y figuras de vuestros ratones que destruyen la tierra..."
        }
        res19 = evaluate_question(q19, v19, book_key="1samuel")
        self.assertNotEqual(res19["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res19["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1SA-0058: Cinco piedras lisas del arroyo (1 Samuel 17:40)
        q58 = self.get_1samuel_question("NQB-AT-1SA-0058")
        v58 = {40: "Y tomó su cayado en su mano, y escogió cinco piedras lisas del arroyo, y las puso en el saco pastoril..."}
        res58 = evaluate_question(q58, v58, book_key="1samuel")
        self.assertNotEqual(res58["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res58["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 1SA-0098: Jonatán, Abinadab y Malquisúa (1 Samuel 31:2)
        q98 = self.get_1samuel_question("NQB-AT-1SA-0098")
        v98 = {2: "Y siguiendo los filisteos a Saúl y a sus hijos, mataron a Jonatán, a Abinadab y a Malquisúa, hijos de Saúl."}
        res98 = evaluate_question(q98, v98, book_key="1samuel")
        self.assertNotEqual(res98["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res98["controles_superados"]["control_nombres_propios"], "PASS")

    def test_2samuel_regression_and_cases(self) -> None:
        """Verifica casos canónicos clave de 2 Samuel (amalecita, Is-boset, Mefi-boset, 30.000, 9 meses y 20 días)."""
        # 2SA-0002: Amalecita (2 Samuel 1:13)
        q2 = self.get_2samuel_question("NQB-AT-2SA-0002")
        v2 = {13: "Y dijo David a aquel joven que le había traído las nuevas: ¿De dónde eres tú? Y él respondió: Yo soy hijo de un extranjero, amalecita."}
        res2 = evaluate_question(q2, v2, book_key="2samuel")
        self.assertNotEqual(res2["estado"], "REQUIERE_CORRECCION")

        # 2SA-0007: Is-boset hijo de Saúl proclamado rey (2 Samuel 2:8-10)
        q7 = self.get_2samuel_question("NQB-AT-2SA-0007")
        v7 = {
            8: "Pero Abner hijo de Ner, general del ejército de Saúl, tomó a Is-boset hijo de Saúl, y lo llevó a Mahanaim,",
            9: "y lo hizo rey sobre Galaad...",
            10: "De cuarenta años era Is-boset hijo de Saúl cuando comenzó a reinar sobre Israel..."
        }
        res7 = evaluate_question(q7, v7, book_key="2samuel")
        self.assertNotEqual(res7["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res7["controles_superados"]["control_nombres_propios"], "PASS")

        # 2SA-0012: Mefi-boset hijo de Jonatán lisiado de los pies (2 Samuel 4:4)
        q12 = self.get_2samuel_question("NQB-AT-2SA-0012")
        v12 = {4: "Y Jonatán hijo de Saúl tenía un hijo lisiado de los pies. Tenía cinco años de edad cuando llegaron de Jezreel las noticias de la muerte de Saúl y de Jonatán... y quedó cojo. Su nombre era Mefi-boset."}
        res12 = evaluate_question(q12, v12, book_key="2samuel")
        self.assertNotEqual(res12["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res12["controles_superados"]["control_nombres_propios"], "PASS")

        # 2SA-0018: Treinta mil escogidos (2 Samuel 6:1)
        q18 = self.get_2samuel_question("NQB-AT-2SA-0018")
        v18 = {1: "David volvió a reunir a todos los escogidos de Israel, treinta mil."}
        res18 = evaluate_question(q18, v18, book_key="2samuel")
        self.assertNotEqual(res18["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res18["controles_superados"]["control_numeros_cantidades"], "PASS")

        # 2SA-0078: Nueve meses y veinte días (2 Samuel 24:8-9)
        q78 = self.get_2samuel_question("NQB-AT-2SA-0078")
        v78 = {
            8: "Después que hubieron recorrido toda la tierra, volvieron a Jerusalén al cabo de nueve meses y veinte días.",
            9: "Y Joab dio el número del censo del pueblo al rey..."
        }
        res78 = evaluate_question(q78, v78, book_key="2samuel")
        self.assertNotEqual(res78["estado"], "REQUIERE_CORRECCION")
        self.assertEqual(res78["controles_superados"]["control_numeros_cantidades"], "PASS")


if __name__ == "__main__":
    unittest.main()
