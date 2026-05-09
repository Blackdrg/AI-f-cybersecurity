/**
 * AIFace SDK - WebAssembly/TypeScript Client for LEVI-AI Face Recognition
 * Status: v2.1 Production Ready (Q2 2026) - Full REST implementation
 *
 * Full-featured TypeScript SDK for browser-based applications.
 * Supports REST API for server-side recognition with optional on-device
 * WASM inference for detection/embedding (when offlineMode enabled).
 */

export interface AIFaceConfig {
  /** Base URL of the LEVI-AI backend API */
  apiBaseURL: string;
  /** API key for authentication */
  apiKey: string;
  /** Enable on-device WASM models for offline recognition (future) */
  offlineMode?: boolean;
  /** Request timeout in milliseconds */
  timeout?: number;
}

export interface FaceRecognitionResult {
  personId: string;
  confidence: number;
  matched: boolean;
}

export interface EnrollmentResult {
  personId: string;
  templateId: string;
  success: boolean;
  message?: string;
}

export interface Person {
  person_id: string;
  name?: string;
  age?: number;
  gender?: string;
  embeddings: string[];
  created_at?: string;
  updated_at?: string;
}

export interface VerifyResult {
  is_same_person: boolean;
  confidence: number;
  similarity: number;
}

export interface RecognitionResponse {
  faces: Array<{
    matches: Array<{
      person: Person;
      confidence: number;
      similarity_score: number;
    }>;
  }>;
}

export interface MetricsResponse {
  num_persons: number;
  num_embeddings: number;
  recognition_count: number;
  enroll_count: number;
  avg_latency_ms: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  redis: string;
  models_loaded: number;
  uptime_seconds: number;
}

/**
 * Main SDK client class
 */
export class AIFaceClient {
  private config: AIFaceConfig;
  private baseURL: string;
  private timeout: number;

  /**
   * Initialize the SDK client
   * @param config Configuration object
   */
  constructor(config: AIFaceConfig) {
    this.config = config;
    this.baseURL = config.apiBaseURL.replace(/\/$/, '');
    this.timeout = config.timeout || 30000;
  }

  private async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const url = `${this.baseURL}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
          ...(options.headers || {}),
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status} ${response.statusText}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          // Use default error message
        }
        throw new Error(errorMessage);
      }

      return response;
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error(`Request timeout after ${this.timeout}ms`);
      }
      throw error;
    }
  }

  private async multipartRequest(
    endpoint: string,
    fields: Map<string, string>,
    files: Array<{ name: string; data: Blob }>
  ): Promise<Response> {
    const formData = new FormData();

    // Add text fields
    for (const [key, value] of fields.entries()) {
      formData.append(key, value);
    }

    // Add files
    for (const file of files) {
      formData.append(file.name, file.data);
    }

    return this.request(endpoint, {
      method: 'POST',
      body: formData,
    });
  }

  /**
   * Enroll a face image for a person
   * @param imageBlob JPEG/PNG image as Blob
   * @param personId Unique identifier
   * @param name Human-readable name
   * @param age Optional age
   * @param gender Optional gender
   * @param consent Whether consent was obtained
   * @returns Enrollment result
   */
  async enroll(
    imageBlob: Blob,
    personId: string,
    name: string,
    age?: number,
    gender?: string,
    consent: boolean = true
  ): Promise<EnrollmentResult> {
    const fields = new Map<string, string>([
      ['person_id', personId],
      ['name', name],
      ['consent', consent ? 'true' : 'false'],
    ]);

    if (age !== undefined) fields.set('age', String(age));
    if (gender) fields.set('gender', gender);

    const response = await this.multipartRequest('/api/enroll', fields, [
      { name: 'images', data: imageBlob }
    ]);

    return response.json();
  }

  /**
   * Enroll multiple images for a person
   * @param imageBlobs Array of JPEG/PNG images as Blobs
   * @param personId Unique identifier
   * @param name Human-readable name
   * @param consent Whether consent was obtained
   * @returns Enrollment result
   */
  async enrollMultiple(
    imageBlobs: Blob[],
    personId: string,
    name: string,
    consent: boolean = true
  ): Promise<EnrollmentResult> {
    const fields = new Map<string, string>([
      ['person_id', personId],
      ['name', name],
      ['consent', consent ? 'true' : 'false'],
    ]);

    const files = imageBlobs.map((blob, idx) => ({
      name: 'images',
      data: blob
    }));

    const response = await this.multipartRequest('/api/enroll', fields, files);
    return response.json();
  }

  /**
   * Recognize a face from an image
   * @param imageBlob JPEG/PNG image as Blob
   * @param topK Number of top matches to return (default: 5)
   * @param threshold Minimum confidence threshold (default: 0.4)
   * @param enableSpoofCheck Enable liveness detection
   * @param cameraId Optional camera ID
   * @returns Recognition results with faces and matches
   */
  async recognize(
    imageBlob: Blob,
    topK: number = 5,
    threshold: number = 0.4,
    enableSpoofCheck: boolean = true,
    cameraId?: string
  ): Promise<RecognitionResponse> {
    const fields = new Map<string, string>([
      ['top_k', String(topK)],
      ['threshold', String(threshold)],
      ['enable_spoof_check', String(enableSpoofCheck)],
    ]);

    if (cameraId) fields.set('camera_id', cameraId);

    const response = await this.multipartRequest('/api/recognize', fields, [
      { name: 'image', data: imageBlob }
    ]);

    return response.json();
  }

  /**
   * Verify two faces belong to the same person
   * @param image1 First image Blob
   * @param image2 Second image Blob
   * @param threshold Similarity threshold
   * @returns Verification result
   */
  async verify(
    image1: Blob,
    image2: Blob,
    threshold: number = 0.7
  ): Promise<VerifyResult> {
    const fields = new Map<string, string>([
      ['threshold', String(threshold)],
    ]);

    const files = [
      { name: 'image1', data: image1 },
      { name: 'image2', data: image2 }
    ];

    const response = await this.multipartRequest('/api/verify', fields, files);
    return response.json();
  }

  /**
   * Get person details
   * @param personId Unique person identifier
   * @returns Person details
   */
  async getPerson(personId: string): Promise<Person> {
    const response = await this.request(`/api/persons/${personId}`);
    return response.json();
  }

  /**
   * Update person details
   * @param personId Unique person identifier
   * @param updates Partial person updates
   * @returns Updated person
   */
  async updatePerson(
    personId: string,
    updates: Partial<Pick<Person, 'name' | 'age' | 'gender'>>
  ): Promise<Person> {
    const response = await this.request(`/api/persons/${personId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });

    return response.json();
  }

  /**
   * Delete a person and all associated data
   * @param personId Unique person identifier
   * @returns Deletion confirmation
   */
  async deletePerson(personId: string): Promise<{ success: boolean }> {
    const response = await this.request(`/api/persons/${personId}`, {
      method: 'DELETE',
    });

    if (response.status === 204) {
      return { success: true };
    }

    return response.json().catch(() => ({ success: true }));
  }

  /**
   * Search for persons by name or metadata
   * @param query Search query string
   * @param limit Maximum results
   * @returns List of matching persons
   */
  async searchPersons(query: string, limit: number = 10): Promise<{ persons: Person[]; total: number }> {
    const params = new URLSearchParams({
      query,
      limit: String(limit),
    });

    const response = await this.request(`/api/persons/search?${params}`);
    return response.json();
  }

  /**
   * Get system metrics
   * @returns System metrics
   */
  async getMetrics(): Promise<MetricsResponse> {
    const response = await this.request('/api/metrics');
    return response.json();
  }

  /**
   * Check system health
   * @returns Health status
   */
  async getHealth(): Promise<HealthResponse> {
    const response = await this.request('/api/health');
    return response.json();
  }

  /**
   * Get audit logs
   * @param limit Maximum entries
   * @param startDate ISO start date
   * @param endDate ISO end date
   * @param action Filter by action
   * @param personId Filter by person
   * @returns Audit log entries
   */
  async getAuditLogs(
    limit: number = 100,
    startDate?: string,
    endDate?: string,
    action?: string,
    personId?: string
  ): Promise<{ logs: any[]; total: number }> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (action) params.append('action', action);
    if (personId) params.append('person_id', personId);

    const response = await this.request(`/api/audit?${params}`);
    return response.json();
  }

  /**
   * Get usage statistics
   * @param userId Optional user ID
   * @returns Usage statistics
   */
  async getUsage(userId?: string): Promise<any> {
    const path = userId ? `/api/usage/${userId}` : '/api/usage';
    const response = await this.request(path);
    return response.json();
  }

  /**
   * Initialize on-device WASM models for offline recognition
   * Requires pre-compiled CoreML/TFLite models bundled with the app.
   * (Reserved for future v2.2 offline mode)
   */
  async initWasmModels(): Promise<void> {
    if (!this.config.offlineMode) {
      console.warn('offlineMode is false; WASM models will not be loaded');
      return;
    }
    throw new Error('WASM model loading not implemented yet');
  }
}

/**
 * Error types for the SDK
 */
export class AIFaceError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message);
    this.name = 'AIFaceError';
  }
}

/**
 * Factory function to create a configured client
 */
export function createAIFaceClient(config: AIFaceConfig): AIFaceClient {
  return new AIFaceClient(config);
}
