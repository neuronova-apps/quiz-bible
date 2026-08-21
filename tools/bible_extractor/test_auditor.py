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

from auditor import evaluate_question, run_audit, extract_numbers, normalize, detect_book_key

GENESIS_PATH = Path(__file__).parent / "genesis-master-input.json"
EXODUS_PATH = Path(__file__).parent / "exodus-master-input.json"
LEVITICUS_PATH = Path(__file__).parent / "leviticus-master-input.json"
NUMBERS_PATH = Path(__file__).parent / "numbers-master-input.json"


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

    def test_numbers_book_detection(self) -> None:
        """Verifica detección de configuración de Números."""
        if not self.numbers_questions:
            self.skipTest("numbers-master-input.json no disponible")
        book_key = detect_book_key(list(self.numbers_questions.values()))
        self.assertEqual(book_key, "numeros")

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

    # --- MANEJO DE ERROR DE API VS ERROR DEL BANCO ---

    def test_api_failure_produces_inconclusive_not_requires_correction(self) -> None:
        q = self.get_genesis_question("NQB-AT-GEN-0001")
        res = evaluate_question(q, {}, book_key="genesis")
        self.assertEqual(res["estado"], "NO_CONCLUYENTE")
        self.assertNotEqual(res["estado"], "REQUIERE_CORRECCION")


if __name__ == "__main__":
    unittest.main()
