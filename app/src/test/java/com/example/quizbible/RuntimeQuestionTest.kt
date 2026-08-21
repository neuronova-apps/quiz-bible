package com.example.quizbible

import com.example.quizbible.data.RuntimeQuestionParser
import com.example.quizbible.model.AuditStatus
import com.example.quizbible.model.Difficulty
import com.example.quizbible.model.HumanReviewStatus
import com.example.quizbible.model.QuestionType
import com.example.quizbible.model.Testament
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.InputStreamReader
import java.util.Random

class RuntimeQuestionTest {

    private lateinit var jsonString: String

    @Before
    fun setUp() {
        val inputStream = javaClass.classLoader?.getResourceAsStream("quiz_bible_runtime_sample_v1.json")
            ?: throw IllegalStateException("No se encontró quiz_bible_runtime_sample_v1.json en test resources")
        jsonString = InputStreamReader(inputStream, Charsets.UTF_8).use { it.readText() }
    }

    @Test
    fun testLoadAndParse20QuestionsSample() {
        val collection = RuntimeQuestionParser.parseCollection(jsonString)

        assertEquals("quizbible-runtime-v1", collection.schemaVersion)
        assertEquals(20, collection.totalQuestions)
        assertEquals(20, collection.questions.size)

        val expectedIds = listOf(
            "NQB-AT-GEN-0001", "NQB-AT-GEN-0036",
            "NQB-AT-EXO-0002", "NQB-AT-EXO-0021",
            "NQB-AT-LEV-0017", "NQB-AT-LEV-0045",
            "NQB-AT-NUM-0001", "NQB-AT-NUM-0062",
            "NQB-AT-DEU-0013", "NQB-AT-DEU-0078",
            "NQB-AT-JOS-0001", "NQB-AT-JOS-0005",
            "NQB-AT-JUE-0048",
            "NQB-AT-RUT-0004",
            "NQB-AT-1SA-0043",
            "NQB-AT-2SA-0028",
            "NQB-AT-1RE-0011",
            "NQB-AT-2RE-0006",
            "NQB-AT-1CR-0066",
            "NQB-AT-2CR-0102"
        )

        val actualIds = collection.questions.map { it.id }
        assertEquals(expectedIds, actualIds)
    }

    @Test
    fun testOptionIntegrityAndCorrectOptionId() {
        val collection = RuntimeQuestionParser.parseCollection(jsonString)

        for (q in collection.questions) {
            assertEquals(4, q.options.size)
            assertEquals("A", q.correctOptionId)
            assertEquals(Testament.OT, q.testament)
            assertEquals(QuestionType.MULTIPLE_CHOICE, q.questionType)
            assertEquals("RVR1960", q.verificationTranslation)
            assertTrue(q.prompt.isNotBlank())
            assertTrue(q.explanation.isNotBlank())
            assertTrue(q.referenceDisplay.isNotBlank())

            val optionIds = q.options.map { it.id }
            assertEquals(listOf("A", "B", "C", "D"), optionIds)

            val correctOption = q.options.first { it.id == q.correctOptionId }
            assertTrue(correctOption.text.isNotBlank())
        }
    }

    @Test
    fun testDifficultyDeserialization() {
        val collection = RuntimeQuestionParser.parseCollection(jsonString)

        val basics = collection.questions.filter { it.difficulty == Difficulty.BASIC }
        val intermediates = collection.questions.filter { it.difficulty == Difficulty.INTERMEDIATE }
        val advanceds = collection.questions.filter { it.difficulty == Difficulty.ADVANCED }
        val experts = collection.questions.filter { it.difficulty == Difficulty.EXPERT }

        assertEquals(6, basics.size)
        assertEquals(6, intermediates.size)
        assertEquals(5, advanceds.size)
        assertEquals(3, experts.size)
    }

    @Test
    fun testEligibleModesAndCategoryFilters() {
        val collection = RuntimeQuestionParser.parseCollection(jsonString)

        // Filtro modo AT
        val atQuestions = collection.questions.filter { it.eligibleModes.contains("AT") }
        assertEquals(20, atQuestions.size)

        // Filtro modo PERSONAJES_AT
        val personajesQuestions = collection.questions.filter { it.eligibleModes.contains("PERSONAJES_AT") }
        assertEquals(10, personajesQuestions.size)
        for (q in personajesQuestions) {
            assertEquals("PERSONAJES_BIBLICOS", q.category)
        }

        // Filtro modo AMBOS
        val ambosQuestions = collection.questions.filter { it.eligibleModes.contains("AMBOS") }
        assertEquals(20, ambosQuestions.size)
    }

    @Test
    fun testKotlinShufflePreservesCorrectOptionIdentity() {
        val collection = RuntimeQuestionParser.parseCollection(jsonString)
        val question = collection.questions[0] // Génesis 1:1
        val originalCorrectText = question.options.first { it.id == question.correctOptionId }.text

        val positionsVisited = mutableSetOf<Int>()

        for (seed in 0..200) {
            val random = kotlin.random.Random(seed)
            val shuffledOptions = question.options.shuffled(random)

            val correctPostShuffle = shuffledOptions.first { it.id == question.correctOptionId }
            val visualIndex = shuffledOptions.indexOf(correctPostShuffle)
            positionsVisited.add(visualIndex)

            assertEquals("A", correctPostShuffle.id)
            assertEquals(originalCorrectText, correctPostShuffle.text)
        }

        // Confirmar que ocupó todas las posiciones visuales posibles (0, 1, 2, 3)
        assertEquals(setOf(0, 1, 2, 3), positionsVisited)
    }

    @Test
    fun testProductionReadinessRule() {
        val collection = RuntimeQuestionParser.parseCollection(jsonString)
        val q = collection.questions[0]

        // Estado inicial de la muestra: VERIFIED + PENDING -> no listo para producción
        assertEquals(AuditStatus.VERIFIED, q.auditStatus)
        assertEquals(HumanReviewStatus.PENDING, q.humanReviewStatus)
        assertFalse(q.isProductionReady)

        // Aprobación humana -> listo para producción
        val approvedQ = q.copy(humanReviewStatus = HumanReviewStatus.APPROVED)
        assertTrue(approvedQ.isProductionReady)

        // Rechazo humano -> no listo para producción
        val rejectedQ = q.copy(humanReviewStatus = HumanReviewStatus.REJECTED)
        assertFalse(rejectedQ.isProductionReady)

        // Auditoría requiere corrección -> nunca listo para producción aunque esté aprobado
        val faultyQ = q.copy(
            auditStatus = AuditStatus.REQUIRES_CORRECTION,
            humanReviewStatus = HumanReviewStatus.APPROVED
        )
        assertFalse(faultyQ.isProductionReady)
    }
}
