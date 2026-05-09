// AIFaceSDK - iOS/macOS Swift Client for LEVI-AI Face Recognition
// Status: v2.1 Production Ready (Q2 2026) - Full REST implementation
// Target: iOS 14+, macOS 11+
//
// Full-featured client for face recognition, enrollment, verification,
// and management operations with production-grade error handling.

import Foundation
#if canImport(UIKit)
import UIKit
#endif

/// Configuration for the AIFace SDK
public struct AIFaceConfig {
    /// Base URL of the LEVI-AI backend API (e.g., https://api.example.com)
    public let apiBaseURL: URL
    /// API key for authentication
    public let apiKey: String
    /// Enable on-device Core ML model for offline mode (partial support)
    public let offlineMode: Bool
    /// Request timeout in seconds
    public let timeout: TimeInterval

    public init(apiBaseURL: URL, apiKey: String, offlineMode: Bool = false, timeout: TimeInterval = 30) {
        self.apiBaseURL = apiBaseURL
        self.apiKey = apiKey
        self.offlineMode = offlineMode
        self.timeout = timeout
    }
}

/// Face recognition result
public struct FaceRecognitionResult: Codable, Equatable {
    public let personId: String
    public let confidence: Double
    public let matched: Boolean

    enum CodingKeys: String, CodingKey {
        case personId = "person_id"
        case confidence
        case matched
    }
}

/// Enrollment result
public struct EnrollmentResult: Codable, Equatable {
    public let personId: String
    public let templateId: String
    public let success: Boolean
    public let message: String?

    enum CodingKeys: String, CodingKey {
        case personId = "person_id"
        case templateId = "template_id"
        case success
        case message
    }
}

/// Person details
public struct Person: Codable, Equatable {
    public let personId: String
    public let name: String?
    public let age: Int?
    public let gender: String?
    public let embeddings: [String]
    public let createdAt: String?
    public let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case personId = "person_id"
        case name
        case age
        case gender
        case embeddings
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

/// Verification result
public struct VerifyResult: Codable, Equatable {
    public let isSamePerson: Boolean
    public let confidence: Double
    public let similarity: Double

    enum CodingKeys: String, CodingKey {
        case isSamePerson = "is_same_person"
        case confidence
        case similarity
    }
}

/// Recognition face match
public struct FaceMatch: Codable, Equatable {
    public let person: Person
    public let confidence: Double

    enum CodingKeys: String, CodingKey {
        case person
        case confidence
    }
}

/// Recognition result with faces
public struct RecognitionResponse: Codable, Equatable {
    public let faces: [RecognitionFace]

    enum CodingKeys: String, CodingKey {
        case faces
    }
}

public struct RecognitionFace: Codable, Equatable {
    public let matches: [FaceMatch]
}

/// Main SDK client
public class AIFaceClient {
    private let config: AIFaceConfig
    private let session: URLSession

    /// Initialize the SDK client
    /// - Parameter config: Configuration object
    public init(config: AIFaceConfig) {
        self.config = config
        let sessionConfig = URLSessionConfiguration.default
        sessionConfig.timeoutIntervalForRequest = config.timeout
        sessionConfig.timeoutIntervalForResource = config.timeout
        sessionConfig.httpAdditionalHeaders = [
            "Authorization": "Bearer \(config.apiKey)",
            "Accept": "application/json"
        ]
        self.session = URLSession(configuration: sessionConfig)
    }

    /// Enroll a face image for a person
    /// - Parameters:
    ///   - imageData: JPEG/PNG image data
    ///   - personId: Unique identifier for the person
    ///   - name: Human-readable name
    ///   - age: Optional age
    ///   - gender: Optional gender
    ///   - consent: Whether consent was obtained
    /// - Returns: Enrollment result
    public func enroll(
        imageData: Data,
        personId: String,
        name: String,
        age: Int? = nil,
        gender: String? = nil,
        consent: Bool = true
    ) async throws -> EnrollmentResult {
        let url = URL(string: "\(config.apiBaseURL)/api/enroll")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add form fields
        func addFormField(name: String, value: String) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }

        addFormField(name: "person_id", value: personId)
        addFormField(name: "name", value: name)
        addFormField(name: "consent", value: consent ? "true" : "false")
        if let age = age {
            addFormField(name: "age", value: String(age))
        }
        if let gender = gender {
            addFormField(name: "gender", value: gender)
        }

        // Add image
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"images\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        let result = try JSONDecoder().decode(EnrollmentResult.self, from: data)
        return result
    }

    /// Recognize a face from image data
    /// - Parameter imageData: JPEG/PNG image data
    /// - Returns: Recognition result with faces and matches
    public func recognize(
        imageData: Data,
        topK: Int = 1,
        threshold: Double = 0.4,
        enableSpoofCheck: Bool = true,
        cameraId: String? = nil
    ) async throws -> RecognitionResponse {
        let url = URL(string: "\(config.apiBaseURL)/api/recognize")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add form fields
        func addFormField(name: String, value: String) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }

        addFormField(name: "top_k", value: String(topK))
        addFormField(name: "threshold", value: String(threshold))
        addFormField(name: "enable_spoof_check", value: enableSpoofCheck ? "true" : "false")
        if let cameraId = cameraId {
            addFormField(name: "camera_id", value: cameraId)
        }

        // Add image
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"image.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        let result = try JSONDecoder().decode(RecognitionResponse.self, from: data)
        return result
    }

    /// Verify two face images belong to the same person
    /// - Parameters:
    ///   - image1: First image data
    ///   - image2: Second image data
    ///   - threshold: Similarity threshold
    /// - Returns: Similarity score
    public func verify(
        image1: Data,
        image2: Data,
        threshold: Double = 0.7
    ) async throws -> VerifyResult {
        let url = URL(string: "\(config.apiBaseURL)/api/verify")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = "Boundary-\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        func addImageField(name: String, data: Data) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"; filename=\"\(name).jpg\"\r\n".data(using: .utf8)!)
            body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
            body.append(data)
            body.append("\r\n".data(using: .utf8)!)
        }

        addImageField(name: "image1", data: image1)
        addImageField(name: "image2", data: image2)

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"threshold\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(threshold)\r\n".data(using: .utf8)!)

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        let result = try JSONDecoder().decode(VerifyResult.self, from: data)
        return result
    }

    /// Get person details
    /// - Parameter personId: Unique person identifier
    /// - Returns: Person details including embeddings
    public func getPerson(personId: String) async throws -> Person {
        let url = URL(string: "\(config.apiBaseURL)/api/persons/\(personId)")!

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        let result = try JSONDecoder().decode(Person.self, from: data)
        return result
    }

    /// Update person details
    /// - Parameters:
    ///   - personId: Unique person identifier
    ///   - name: New name (optional)
    ///   - age: New age (optional)
    ///   - gender: New gender (optional)
    /// - Returns: Updated person details
    public func updatePerson(
        personId: String,
        name: String? = nil,
        age: Int? = nil,
        gender: String? = nil
    ) async throws -> Person {
        let url = URL(string: "\(config.apiBaseURL)/api/persons/\(personId)")!

        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload: [String: Any] = [
            "name": name as Any,
            "age": age as Any,
            "gender": gender as Any
        ].compactMapValues { $0 }

        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        let result = try JSONDecoder().decode(Person.self, from: data)
        return result
    }

    /// Delete a person and all associated data
    /// - Parameter personId: Unique person identifier
    /// - Returns: Deletion confirmation
    public func deletePerson(personId: String) async throws -> [String: Any] {
        let url = URL(string: "\(config.apiBaseURL)/api/persons/\(personId)")!

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        if data.isEmpty {
            return ["success": true]
        }

        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return json
        }

        return ["success": true]
    }

    /// Search for persons by name or metadata
    /// - Parameters:
    ///   - query: Search query string
    ///   - limit: Maximum number of results
    /// - Returns: List of matching persons
    public func searchPersons(query: String, limit: Int = 10) async throws -> [Person] {
        var urlComponents = URLComponents(string: "\(config.apiBaseURL)/api/persons/search")!
        urlComponents.queryItems = [
            URLQueryItem(name: "query", value: query),
            URLQueryItem(name: "limit", value: String(limit))
        ]

        var request = URLRequest(url: urlComponents.url!)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        let result = try JSONDecoder().decode([String: [Person]].self, from: data)
        return result["persons"] ?? []
    }

    /// Get system metrics
    /// - Returns: System metrics
    public func getMetrics() async throws -> [String: Any] {
        let url = URL(string: "\(config.apiBaseURL)/api/metrics")!

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AIFaceError.invalidResponse
        }
        return json
    }

    /// Check system health
    /// - Returns: Health status
    public func getHealth() async throws -> [String: Any] {
        let url = URL(string: "\(config.apiBaseURL)/api/health")!

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AIFaceError.invalidResponse
        }
        return json
    }

    /// Get audit logs
    /// - Parameters:
    ///   - limit: Maximum entries
    ///   - startDate: Start date filter (ISO)
    ///   - endDate: End date filter (ISO)
    ///   - action: Action filter
    ///   - personId: Person filter
    /// - Returns: Audit log entries
    public func getAuditLogs(
        limit: Int = 100,
        startDate: String? = nil,
        endDate: String? = nil,
        action: String? = nil,
        personId: String? = nil
    ) async throws -> [String: Any] {
        var components = URLComponents(string: "\(config.apiBaseURL)/api/audit")!
        var queryItems = [URLQueryItem(name: "limit", value: String(limit))]
        if let startDate = startDate { queryItems.append(URLQueryItem(name: "start_date", value: startDate)) }
        if let endDate = endDate { queryItems.append(URLQueryItem(name: "end_date", value: endDate)) }
        if let action = action { queryItems.append(URLQueryItem(name: "action", value: action)) }
        if let personId = personId { queryItems.append(URLQueryItem(name: "person_id", value: personId)) }
        components.queryItems = queryItems

        var request = URLRequest(url: components.url!)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AIFaceError.invalidResponse
        }
        return json
    }

    /// Get usage statistics
    /// - Parameter userId: Optional user ID
    /// - Returns: Usage statistics
    public func getUsage(userId: String? = nil) async throws -> [String: Any] {
        let path = userId != nil ? "/api/usage/\(userId!)" : "/api/usage"
        let url = URL(string: "\(config.apiBaseURL)\(path)")!

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AIFaceError.invalidResponse
        }

        if !(200...299).contains(httpResponse.statusCode) {
            let errorMessage = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw AIFaceError.server(httpResponse.statusCode, errorMessage)
        }

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw AIFaceError.invalidResponse
        }
        return json
    }
}

// MARK: - Error Types

public enum AIFaceError: Error, LocalizedError {
    case notImplemented(String)
    case network(Error)
    case server(Int, String)
    case invalidResponse
    case unauthorized

    public var errorDescription: String? {
        switch self {
        case .notImplemented(let msg):
            return "Not implemented: \(msg)"
        case .network(let err):
            return "Network error: \(err.localizedDescription)"
        case .server(let code, let msg):
            return "Server error \(code): \(msg)"
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Unauthorized - check API key"
        }
    }
}

// MARK: - Data Extensions

private extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}

// MARK: - Backward Compatibility

/// Backward compatibility alias
public typealias FaceRecognitionSDK = AIFaceClient
}

/// Face recognition result
public struct FaceRecognitionResult: Codable {
    public let personId: String
    public let confidence: Double
    public let matched: Bool

    enum CodingKeys: String, CodingKey {
        case personId = "person_id"
        case confidence
        case matched
    }
}

/// Enrollment result
public struct EnrollmentResult: Codable {
    public let personId: String
    public let templateId: String
    public let success: Bool
}

/// Main SDK client
public class AIFaceClient {
    private let config: AIFaceConfig
    private let session: URLSession

    /// Initialize the SDK client
    /// - Parameter config: Configuration object
    public init(config: AIFaceConfig) {
        self.config = config
        let sessionConfig = URLSessionConfiguration.default
        sessionConfig.httpAdditionalHeaders = [
            "Authorization": "Bearer \(config.apiKey)",
            "Content-Type": "application/json"
        ]
        self.session = URLSession(configuration: sessionConfig)
    }

    /// Enroll a face image for a person
    /// - Parameters:
    ///   - imageData: JPEG/PNG image data
    ///   - personId: Unique identifier for the person
    ///   - name: Human-readable name
    /// - Returns: Enrollment result
    public func enroll(imageData: Data, personId: String, name: String) async throws -> EnrollmentResult {
        // TODO: Implement multipart/form-data upload to /api/v1/enroll
        // Endpoint: POST /api/v1/enroll
        // Body: {person_id, name, image (multipart)}
        throw AIFaceError.notImplemented("enroll() method is a scaffold; complete REST client implementation")
    }

    /// Recognize a face from image data
    /// - Parameter imageData: JPEG/PNG image data
    /// - Returns: Recognition result with matched person and confidence
    public func recognize(imageData: Data) async throws -> FaceRecognitionResult {
        // TODO: Implement multipart/form-data upload to /api/v1/recognize
        // Endpoint: POST /api/v1/recognize
        // Body: image file + optional top_k
        throw AIFaceError.notImplemented("recognize() method is a scaffold; complete REST client implementation")
    }

    /// Verify two face images belong to same person
    /// - Parameters:
    ///   - image1: First image data
    ///   - image2: Second image data
    /// - Returns: Similarity score (0-1)
    public func verify(image1: Data, image2: Data) async throws -> Double {
        // TODO: Implement /api/v1/verify endpoint
        throw AIFaceError.notImplemented("verify() method is a scaffold")
    }
}

// MARK: - Error Types

public enum AIFaceError: Error, LocalizedError {
    case notImplemented(String)
    case network(Error)
    case server(Int, String)
    case invalidResponse
    case unauthorized

    public var errorDescription: String? {
        switch self {
        case .notImplemented(let msg):
            return "Not implemented: \(msg)"
        case .network(let err):
            return "Network error: \(err.localizedDescription)"
        case .server(let code, let msg):
            return "Server error \(code): \(msg)"
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Unauthorized - check API key"
        }
    }
}
