/*
 * AIFace SDK - Android/Kotlin Client for LEVI-AI Face Recognition
 * Status: v2.1 Production Ready (Q2 2026) - Full REST implementation
 * Target: Android API 24+ (Android 7.0 Nougat)
 *
 * Full-featured client for face recognition, enrollment, verification,
 * and management operations with production-grade error handling.
 */

package com.aif.sdk

import android.content.Context
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.util.concurrent.CompletableFuture
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

/**
 * Configuration for the AIFace SDK
 */
data class AIFaceConfig(
    val apiBaseUrl: String,
    val apiKey: String,
    val offlineMode: Boolean = false,
    val context: Context,
    val timeoutSeconds: Int = 30
)

/**
 * Face recognition result
 */
data class FaceRecognitionResult(
    val personId: String,
    val confidence: Double,
    val matched: Boolean
)

/**
 * Enrollment result
 */
data class EnrollmentResult(
    val personId: String,
    val templateId: String,
    val success: Boolean,
    val message: String? = null
)

/**
 * Person details
 */
data class Person(
    val personId: String,
    val name: String?,
    val age: Int?,
    val gender: String?,
    val embeddings: List<String>,
    val createdAt: String?,
    val updatedAt: String?
)

/**
 * Verification result
 */
data class VerifyResult(
    val similarity: Double,
    val verified: Boolean
)

/**
 * Main SDK client with full REST API implementation
 */
class AIFaceClient private constructor(private val config: AIFaceConfig) {

    companion object {
        @Volatile
        private var instance: AIFaceClient? = null

        /**
         * Initialize the SDK singleton
         */
        fun initialize(config: AIFaceConfig): AIFaceClient {
            return instance ?: synchronized(this) {
                instance ?: AIFaceClient(config).also { instance = it }
            }
        }

        /**
         * Get the SDK instance
         */
        fun getInstance(): AIFaceClient {
            return instance ?: throw IllegalStateException(
                "AIFaceClient not initialized. Call initialize() first."
            )
        }
    }

    private val client: OkHttpClient
    private val jsonMediaType = "application/json; charset=utf-8".toMediaTypeOrNull()
    private val imageMediaType = "image/jpeg".toMediaTypeOrNull()

    init {
        val timeout = config.timeoutSeconds.toLong()
        client = OkHttpClient.Builder()
            .connectTimeout(timeout, java.util.concurrent.TimeUnit.SECONDS)
            .readTimeout(timeout, java.util.concurrent.TimeUnit.SECONDS)
            .writeTimeout(timeout, java.util.concurrent.TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("Authorization", "Bearer ${config.apiKey}")
                    .build()
                chain.proceed(request)
            }
            .build()
    }

    /**
     * Enroll a face image for a person
     *
     * @param imageFile JPEG/PNG image file
     * @param personId Unique identifier for the person
     * @param name Human-readable name
     * @param age Optional age
     * @param gender Optional gender
     * @param consent Whether consent was obtained
     * @return Enrollment result
     */
    suspend fun enroll(
        imageFile: File,
        personId: String,
        name: String,
        age: Int? = null,
        gender: String? = null,
        consent: Boolean = true
    ): CompletableFuture<EnrollmentResult> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<EnrollmentResult>()
        try {
            val requestBody = MultipartBody.Builder().setType(MultipartBody.FORM)
                .addFormDataPart("person_id", personId)
                .addFormDataPart("name", name)
                .addFormDataPart("consent", consent.toString())
                .addFormDataPart(
                    "images",
                    imageFile.name,
                    imageFile.asRequestBody("image/jpeg".toMediaTypeOrNull())
                ).apply {
                    age?.let { addFormDataPart("age", it.toString()) }
                    gender?.let { addFormDataPart("gender", it) }
                }.build()

            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/enroll")
                .post(requestBody)
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Enrollment failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    future.complete(
                        EnrollmentResult(
                            personId = responseData.getString("person_id"),
                            templateId = responseData.optString("template_id", ""),
                            success = true,
                            message = responseData.optString("message", "Enrolled successfully")
                        )
                    )
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Recognize a face from image data
     *
     * @param imageFile JPEG/PNG image file
     * @param topK Number of top matches to return (default: 1)
     * @param threshold Recognition threshold 0-1 (default: 0.4)
     * @param enableSpoofCheck Whether to enable liveness detection
     * @param cameraId Optional camera ID for filtering
     * @return Recognition result with faces and matches
     */
    suspend fun recognize(
        imageFile: File,
        topK: Int = 1,
        threshold: Double = 0.4,
        enableSpoofCheck: Boolean = true,
        cameraId: String? = null
    ): CompletableFuture<Map<String, Any>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Map<String, Any>>()
        try {
            val requestBody = MultipartBody.Builder().setType(MultipartBody.FORM)
                .addFormDataPart("image", imageFile.name, imageFile.asRequestBody(imageMediaType))
                .addFormDataPart("top_k", topK.toString())
                .addFormDataPart("threshold", threshold.toString())
                .addFormDataPart("enable_spoof_check", enableSpoofCheck.toString())
                .apply {
                    cameraId?.let { addFormDataPart("camera_id", it) }
                }.build()

            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/recognize")
                .post(requestBody)
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Recognition failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    val result = mutableMapOf<String, Any>()
                    result["faces"] = responseData.optJSONArray("faces") ?: org.json.JSONArray()
                    future.complete(result)
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Verify two face images belong to same person
     *
     * @param image1 First image file
     * @param image2 Second image file
     * @param threshold Similarity threshold (default: 0.7)
     * @return Similarity score (0-1)
     */
    suspend fun verify(
        image1: File,
        image2: File,
        threshold: Double = 0.7
    ): CompletableFuture<VerifyResult> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<VerifyResult>()
        try {
            val requestBody = MultipartBody.Builder().setType(MultipartBody.FORM)
                .addFormDataPart("image1", image1.name, image1.asRequestBody(imageMediaType))
                .addFormDataPart("image2", image2.name, image2.asRequestBody(imageMediaType))
                .addFormDataPart("threshold", threshold.toString())
                .build()

            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/verify")
                .post(requestBody)
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Verification failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    future.complete(
                        VerifyResult(
                            similarity = responseData.getDouble("similarity"),
                            verified = responseData.getBoolean("verified")
                        )
                    )
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Get person details.
     *
     * @param personId Unique person identifier
     * @return Person details including embeddings
     */
    suspend fun getPerson(personId: String): CompletableFuture<Person> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Person>()
        try {
            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/persons/$personId")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Get person failed: ${response.code} $errorBody"))
                } else {
                    val data = JSONObject(response.body!!.string())
                    future.complete(
                        Person(
                            personId = data.getString("person_id"),
                            name = data.optString("name", null).takeIf { it.isNotEmpty() },
                            age = data.optInt("age", -1).takeIf { it != -1 },
                            gender = data.optString("gender", null).takeIf { it.isNotEmpty() },
                            embeddings = try {
                                val embeddingsArray = data.getJSONArray("embeddings")
                                (0 until embeddingsArray.length()).map { embeddingsArray.getString(it) }
                            } catch (e: Exception) { emptyList() },
                            createdAt = data.optString("created_at", null).takeIf { it.isNotEmpty() },
                            updatedAt = data.optString("updated_at", null).takeIf { it.isNotEmpty() }
                        )
                    )
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Update person details.
     *
     * @param personId Unique person identifier
     * @param name New name (optional)
     * @param age New age (optional)
     * @param gender New gender (optional)
     * @return Updated person details
     */
    suspend fun updatePerson(
        personId: String,
        name: String? = null,
        age: Int? = null,
        gender: String? = null
    ): CompletableFuture<Person> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Person>()
        try {
            val json = JSONObject().apply {
                name?.let { put("name", it) }
                age?.let { put("age", it) }
                gender?.let { put("gender", it) }
            }

            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/persons/$personId")
                .put(json.toString().toRequestBody(jsonMediaType))
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Update failed: ${response.code} $errorBody"))
                } else {
                    val data = JSONObject(response.body!!.string())
                    future.complete(
                        Person(
                            personId = data.getString("person_id"),
                            name = data.optString("name", null).takeIf { it.isNotEmpty() },
                            age = data.optInt("age", -1).takeIf { it != -1 },
                            gender = data.optString("gender", null).takeIf { it.isNotEmpty() },
                            embeddings = emptyList(),
                            createdAt = null,
                            updatedAt = null
                        )
                    )
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Delete a person and all associated data.
     *
     * @param personId Unique person identifier
     * @return Deletion confirmation
     */
    suspend fun deletePerson(personId: String): CompletableFuture<Map<String, Any>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Map<String, Any>>()
        try {
            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/persons/$personId")
                .delete()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Delete failed: ${response.code} $errorBody"))
                } else {
                    val responseData = if (response.body?.contentLength() ?: 0 > 0) {
                        JSONObject(response.body!!.string())
                    } else {
                        JSONObject().put("success", true)
                    }
                    future.complete(mapOf("success" to true, "data" to responseData))
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Search for persons by name or metadata.
     *
     * @param query Search query string
     * @param limit Maximum number of results (default: 10)
     * @return List of matching persons
     */
    suspend fun searchPersons(query: String, limit: Int = 10): CompletableFuture<List<Person>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<List<Person>>()
        try {
            val httpUrl = HttpUrl.parse("${config.apiBaseUrl}/api/persons/search")!!.newBuilder()
                .addQueryParameter("query", query)
                .addQueryParameter("limit", limit.toString())
                .build()

            val request = Request.Builder()
                .url(httpUrl)
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Search failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    val personsArray = responseData.getJSONArray("persons")
                    val persons = mutableListOf<Person>()
                    for (i in 0 until personsArray.length()) {
                        val p = personsArray.getJSONObject(i)
                        persons.add(
                            Person(
                                personId = p.getString("person_id"),
                                name = p.optString("name", null).takeIf { it.isNotEmpty() },
                                age = p.optInt("age", -1).takeIf { it != -1 },
                                gender = p.optString("gender", null).takeIf { it.isNotEmpty() },
                                embeddings = emptyList(),
                                createdAt = p.optString("created_at", null),
                                updatedAt = p.optString("updated_at", null)
                            )
                        )
                    }
                    future.complete(persons)
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Get system metrics and statistics.
     *
     * @return System metrics including recognition counts, latency, etc.
     */
    suspend fun getMetrics(): CompletableFuture<Map<String, Any>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Map<String, Any>>()
        try {
            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/metrics")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Get metrics failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    val result = mutableMapOf<String, Any>()
                    val keys = responseData.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        result[key] = responseData.get(key)
                    }
                    future.complete(result)
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Check system health status.
     *
     * @return Health status of all system components
     */
    suspend fun getHealth(): CompletableFuture<Map<String, Any>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Map<String, Any>>()
        try {
            val request = Request.Builder()
                .url("${config.apiBaseUrl}/api/health")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Health check failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    val result = mutableMapOf<String, Any>()
                    val keys = responseData.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        result[key] = responseData.get(key)
                    }
                    future.complete(result)
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Get audit logs for compliance and forensics.
     *
     * @param limit Maximum number of log entries (default: 100)
     * @param startDate Filter logs from this date (ISO format)
     * @param endDate Filter logs until this date (ISO format)
     * @param action Filter by specific action type
     * @param personId Filter by specific person
     * @return List of audit log entries
     */
    suspend fun getAuditLogs(
        limit: Int = 100,
        startDate: String? = null,
        endDate: String? = null,
        action: String? = null,
        personId: String? = null
    ): CompletableFuture<Map<String, Any>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Map<String, Any>>()
        try {
            val httpUrl = HttpUrl.parse("${config.apiBaseUrl}/api/audit")!!.newBuilder()
                .addQueryParameter("limit", limit.toString())
                .apply {
                    startDate?.let { addQueryParameter("start_date", it) }
                    endDate?.let { addQueryParameter("end_date", it) }
                    action?.let { addQueryParameter("action", it) }
                    personId?.let { addQueryParameter("person_id", it) }
                }.build()

            val request = Request.Builder()
                .url(httpUrl)
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Get audit logs failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    val result = mutableMapOf<String, Any>()
                    val keys = responseData.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        result[key] = responseData.get(key)
                    }
                    future.complete(result)
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Get usage statistics and quotas.
     *
     * @param userId Optional user ID (defaults to authenticated user)
     * @return Usage statistics including limits and current usage
     */
    suspend fun getUsage(userId: String? = null): CompletableFuture<Map<String, Any>> = withContext(Dispatchers.IO) {
        val future = CompletableFuture<Map<String, Any>>()
        try {
            val url = if (userId != null) {
                "${config.apiBaseUrl}/api/usage/$userId"
            } else {
                "${config.apiBaseUrl}/api/usage"
            }

            val request = Request.Builder()
                .url(url)
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string() ?: "Unknown error"
                    future.completeExceptionally(IOException("Get usage failed: ${response.code} $errorBody"))
                } else {
                    val responseData = JSONObject(response.body!!.string())
                    val result = mutableMapOf<String, Any>()
                    val keys = responseData.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        result[key] = responseData.get(key)
                    }
                    future.complete(result)
                }
            }
        } catch (e: Exception) {
            future.completeExceptionally(e)
        }
        return@withContext future
    }

    /**
     * Close the client and release resources.
     */
    fun close() {
        client.dispatcher.executorService.shutdown()
        client.connectionPool.evictAll()
    }

    /**
     * Convenience method to create a client from config
     */
    companion object {
        fun create(config: AIFaceConfig): AIFaceClient {
            return AIFaceClient(config)
        }
    }
}

// Backward compatibility alias
typealias FaceRecognitionSDK = AIFaceClient
