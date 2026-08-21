package com.example.quizbible.data

import com.example.quizbible.model.AuditStatus
import com.example.quizbible.model.Difficulty
import com.example.quizbible.model.HumanReviewStatus
import com.example.quizbible.model.QuestionType
import com.example.quizbible.model.QuizBibleRuntimeCollection
import com.example.quizbible.model.RuntimeOption
import com.example.quizbible.model.RuntimeQuestion
import com.example.quizbible.model.Testament
import org.json.JSONArray
import org.json.JSONObject

object RuntimeQuestionParser {

    fun parseCollection(jsonString: String): QuizBibleRuntimeCollection {
        val root = JSONObject(jsonString)
        val schemaVersion = root.getString("schemaVersion")
        val generatedAt = root.optString("generatedAt", "")
        val totalQuestions = root.getInt("totalQuestions")
        val questionsArray = root.getJSONArray("questions")

        val questionsList = mutableListOf<RuntimeQuestion>()
        for (i in 0 until questionsArray.length()) {
            val qObj = questionsArray.getJSONObject(i)
            questionsList.add(parseQuestion(qObj))
        }

        return QuizBibleRuntimeCollection(
            schemaVersion = schemaVersion,
            generatedAt = generatedAt,
            totalQuestions = totalQuestions,
            questions = questionsList
        )
    }

    fun parseQuestion(qObj: JSONObject): RuntimeQuestion {
        val id = qObj.getString("id")
        val testament = Testament.valueOf(qObj.getString("testament"))
        val book = qObj.getString("book")
        val chapter = qObj.getInt("chapter")
        val verseStart = qObj.getInt("verseStart")
        val verseEnd = if (qObj.isNull("verseEnd")) null else qObj.getInt("verseEnd")
        val referenceDisplay = qObj.getString("referenceDisplay")
        val category = qObj.getString("category")
        val subcategory = if (qObj.isNull("subcategory")) null else qObj.getString("subcategory")

        val charactersArray = qObj.optJSONArray("characters") ?: JSONArray()
        val characters = mutableListOf<String>()
        for (j in 0 until charactersArray.length()) {
            characters.add(charactersArray.getString(j))
        }

        val difficulty = Difficulty.valueOf(qObj.getString("difficulty"))
        val questionType = QuestionType.valueOf(qObj.getString("questionType"))
        val prompt = qObj.getString("prompt")

        val optionsArray = qObj.getJSONArray("options")
        val options = mutableListOf<RuntimeOption>()
        for (j in 0 until optionsArray.length()) {
            val optObj = optionsArray.getJSONObject(j)
            options.add(
                RuntimeOption(
                    id = optObj.getString("id"),
                    text = optObj.getString("text")
                )
            )
        }

        val correctOptionId = qObj.getString("correctOptionId")
        val explanation = qObj.getString("explanation")

        val eligibleModesArray = qObj.getJSONArray("eligibleModes")
        val eligibleModes = mutableListOf<String>()
        for (j in 0 until eligibleModesArray.length()) {
            eligibleModes.add(eligibleModesArray.getString(j))
        }

        val verificationTranslation = if (qObj.isNull("verificationTranslation")) null else qObj.getString("verificationTranslation")
        val auditStatus = AuditStatus.valueOf(qObj.getString("auditStatus"))
        val humanReviewStatus = HumanReviewStatus.valueOf(qObj.getString("humanReviewStatus"))

        return RuntimeQuestion(
            id = id,
            testament = testament,
            book = book,
            chapter = chapter,
            verseStart = verseStart,
            verseEnd = verseEnd,
            referenceDisplay = referenceDisplay,
            category = category,
            subcategory = subcategory,
            characters = characters,
            difficulty = difficulty,
            questionType = questionType,
            prompt = prompt,
            options = options,
            correctOptionId = correctOptionId,
            explanation = explanation,
            eligibleModes = eligibleModes,
            verificationTranslation = verificationTranslation,
            auditStatus = auditStatus,
            humanReviewStatus = humanReviewStatus
        )
    }
}
