package com.example.quizbible.model

enum class Testament {
    OT,
    NT
}

enum class Difficulty {
    BASIC,
    INTERMEDIATE,
    ADVANCED,
    EXPERT
}

enum class QuestionType {
    MULTIPLE_CHOICE
}

enum class AuditStatus {
    VERIFIED,
    INCONCLUSIVE,
    REQUIRES_CORRECTION
}

enum class HumanReviewStatus {
    PENDING,
    APPROVED,
    REJECTED
}

data class RuntimeOption(
    val id: String,
    val text: String
)

data class RuntimeQuestion(
    val id: String,
    val testament: Testament,
    val book: String,
    val chapter: Int,
    val verseStart: Int,
    val verseEnd: Int?,
    val referenceDisplay: String,
    val category: String,
    val subcategory: String?,
    val characters: List<String>,
    val difficulty: Difficulty,
    val questionType: QuestionType,
    val prompt: String,
    val options: List<RuntimeOption>,
    val correctOptionId: String,
    val explanation: String,
    val eligibleModes: List<String>,
    val verificationTranslation: String?,
    val auditStatus: AuditStatus,
    val humanReviewStatus: HumanReviewStatus
) {
    val isProductionReady: Boolean
        get() = auditStatus != AuditStatus.REQUIRES_CORRECTION &&
                humanReviewStatus == HumanReviewStatus.APPROVED
}

data class QuizBibleRuntimeCollection(
    val schemaVersion: String,
    val generatedAt: String,
    val totalQuestions: Int,
    val questions: List<RuntimeQuestion>
)

interface BibleTextProvider {
    suspend fun getPassage(
        book: String,
        chapter: Int,
        verseStart: Int,
        verseEnd: Int?
    ): String?
}
