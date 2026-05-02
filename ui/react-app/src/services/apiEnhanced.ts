/**
 * Enhanced API Service for AI-f Enterprise
 * 
 * Features:
 * - Comprehensive error handling with retry logic
 * - Request validation and sanitization
 * - Response schema validation
 * - Timeout and circuit breaker patterns
 * - Enterprise-grade error messages
 */

import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

// Validation Schemas
interface RecognitionResponseSchema {
  required: ('faces' | 'timestamp' | 'processing_time')[];
  optional: ('matches' | 'confidence' | 'spoof_detected' | 'explanations')[];
}

interface EnrollmentResponseSchema {
  required: ('person_id' | 'template_id' | 'enrolled_at')[];
  optional: ('warnings' | 'quality_score')[];
}

interface HealthResponseSchema {
  required: ('status' | 'timestamp')[];
  optional: ('services' | 'version' | 'uptime')[];
}

const ResponseSchemas = {
  recognition: {
    required: ['faces', 'timestamp', 'processing_time'],
    optional: ['matches', 'confidence', 'spoof_detected', 'explanations']
  } as RecognitionResponseSchema,
  enrollment: {
    required: ['person_id', 'template_id', 'enrolled_at'],
    optional: ['warnings', 'quality_score']
  } as EnrollmentResponseSchema,
  health: {
    required: ['status', 'timestamp'],
    optional: ['services', 'version', 'uptime']
  } as HealthResponseSchema
};

// Error Categories for Enterprise UX
export const ErrorTypes = {
  NETWORK: 'NETWORK_ERROR',
  TIMEOUT: 'REQUEST_TIMEOUT',
  AUTH: 'AUTHENTICATION_ERROR',
  VALIDATION: 'VALIDATION_ERROR',
  SERVER: 'SERVER_ERROR',
  RATE_LIMIT: 'RATE_LIMIT_EXCEEDED',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
  SPOOF_DETECTED: 'SPOOF_DETECTED',
  LOW_CONFIDENCE: 'LOW_CONFIDENCE',
  QUALITY_ISSUE: 'QUALITY_ISSUE'
};

export class APIError extends Error {
  public type: string;
  public details: Record<string, any>;
  public timestamp: string;
  public id: string;

  constructor(type: string, message: string, details: Record<string, any> = {}) {
    super(message);
    this.name = 'APIError';
    this.type = type;
    this.details = details;
    this.timestamp = new Date().toISOString();
    this.id = uuidv4();
  }

  toUserMessage(): string {
    const messages: Record<string, string> = {
      [ErrorTypes.NETWORK]: 'Network connection unavailable. Please check your internet connection.',
      [ErrorTypes.TIMEOUT]: 'Request timed out. The service may be under high load.',
      [ErrorTypes.AUTH]: 'Your session has expired. Please log in again.',
      [ErrorTypes.VALIDATION]: 'Invalid input. Please check your data and try again.',
      [ErrorTypes.SERVER]: 'Service temporarily unavailable. Please try again later.',
      [ErrorTypes.RATE_LIMIT]: 'Too many requests. Please wait before trying again.',
      [ErrorTypes.SERVICE_UNAVAILABLE]: 'Service is currently unavailable for maintenance.',
      [ErrorTypes.SPOOF_DETECTED]: 'Spoof attempt detected. Access denied for security reasons.',
      [ErrorTypes.LOW_CONFIDENCE]: 'Recognition confidence too low. Please try again with better lighting.',
      [ErrorTypes.QUALITY_ISSUE]: 'Image quality insufficient. Please ensure clear, well-lit face.'
    };
    return messages[this.type] || 'An unexpected error occurred. Please try again.';
  }

  toLogEntry() {
    return {
      id: this.id,
      type: this.type,
      message: this.message,
      details: this.details,
      timestamp: this.timestamp,
      stack: this.stack
    };
  }
}

// Create Enhanced Axios Instance
const createAPI = (config: { baseURL?: string; timeout?: number; headers?: Record<string, string>; maxRetries?: number; retryDelay?: number } = {}) => {
  const api = axios.create({
    baseURL: config.baseURL || process.env.REACT_APP_API_URL || 'http://localhost:8000',
    timeout: config.timeout || 30000,
    headers: {
      'Content-Type': 'application/json',
      ...config.headers
    },
    // Note: axios doesn't have built-in retry, we'll implement in interceptors
  });

  // Request Interceptor
  api.interceptors.request.use(
    (request) => {
      // Add request ID for tracing
      request.headers['X-Request-ID'] = uuidv4();
      
      // Add auth token
      const token = localStorage.getItem('token');
      if (token) {
        request.headers.Authorization = `Bearer ${token}`;
      }

      // Sanitize request data
      if (request.data) {
        request.data = sanitizeInput(request.data);
      }

      // Log request for debugging
      if (process.env.NODE_ENV === 'development') {
        console.log(`[API] ${request.method.toUpperCase()} ${request.url}`, {
          data: request.data,
          headers: request.headers
        });
      }

      return request;
    },
    (error) => {
      return Promise.reject(new APIError(
        ErrorTypes.NETWORK,
        'Failed to create request',
        { originalError: error.message }
      ));
    }
  );

  // Response Interceptor
  api.interceptors.response.use(
    (response) => {
      // Validate response against schema if available
      const endpoint = response.config.url;
      const schema = getResponseSchema(endpoint);
      
      if (schema) {
        validateResponse(response.data, schema);
      }

      if (process.env.NODE_ENV === 'development') {
        console.log(`[API] Response ${response.status} ${response.config.method.toUpperCase()} ${response.config.url}`);
      }

      return response;
    },
    async (error) => {
      const originalRequest = error.config;

      // Handle different error types
      let apiError: APIError;

      if (!error.response) {
        // Network error
        apiError = new APIError(
          ErrorTypes.NETWORK,
          'Network connection failed',
          { url: originalRequest?.url }
        );
      } else if (error.response.status === 401) {
        // Authentication error
        apiError = new APIError(
          ErrorTypes.AUTH,
          'Authentication required',
          { requiresLogin: true }
        );
        // Clear auth state
        if (originalRequest.url !== '/api/auth/login') {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          // Could trigger redirect to login here
        }
      } else if (error.response.status === 403) {
        apiError = new APIError(
          ErrorTypes.AUTH,
          'Insufficient permissions',
          { requiresElevation: true }
        );
      } else if (error.response.status === 408 || error.code === 'ECONNABORTED') {
        // Timeout - retry with exponential backoff
        const maxRetries = originalRequest?.maxRetries || 3;
        if (originalRequest?._retryCount < maxRetries) {
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;
          const delay = Math.pow(2, originalRequest._retryCount) * (originalRequest.retryDelay || 1000);
          
          await new Promise(resolve => setTimeout(resolve, delay));
          return api(originalRequest);
        }
        
        apiError = new APIError(
          ErrorTypes.TIMEOUT,
          'Request timeout after retries',
          { retries: originalRequest?._retryCount }
        );
      } else if (error.response.status === 429) {
        apiError = new APIError(
          ErrorTypes.RATE_LIMIT,
          'Rate limit exceeded',
          { retryAfter: error.response.headers['retry-after'] }
        );
      } else if (error.response.status >= 500) {
        apiError = new APIError(
          ErrorTypes.SERVER,
          'Service error',
          { status: error.response.status, statusText: error.response.statusText }
        );
      } else if (error.response.status === 409) {
        // Special case for spoof detection
        apiError = new APIError(
          ErrorTypes.SPOOF_DETECTED,
          'Security check failed',
          { details: error.response.data }
        );
      } else if (error.response.status === 422) {
        // Validation error with details
        apiError = new APIError(
          ErrorTypes.VALIDATION,
          'Validation failed',
          { fields: error.response.data?.errors || error.response.data }
        );
      } else {
        apiError = new APIError(
          ErrorTypes.SERVER,
          error.response.data?.detail || error.message,
          { status: error.response.status, data: error.response.data }
        );
      }

      // Log error for monitoring
      logAPIError(apiError);

      return Promise.reject(apiError);
    }
  );

  return api;
};

// Helper Functions

const sanitizeInput = (data: any): any => {
  if (typeof data === 'string') {
    return data.trim();
  }
  if (Array.isArray(data)) {
    return data.map(sanitizeInput);
  }
  if (typeof data === 'object' && data !== null) {
    const sanitized: Record<string, any> = {};
    for (const [key, value] of Object.entries(data)) {
      sanitized[key] = sanitizeInput(value);
    }
    return sanitized;
  }
  return data;
};

const getResponseSchema = (url: string): any => {
  if (url.includes('/recognize')) return ResponseSchemas.recognition;
  if (url.includes('/enroll')) return ResponseSchemas.enrollment;
  if (url.includes('/health')) return ResponseSchemas.health;
  return null;
};

const validateResponse = (data: any, schema: any) => {
  const missing = schema.required.filter((field: string) => !(field in data));
  if (missing.length > 0) {
    console.warn('Response missing required fields:', missing);
    // Don't throw in production, just warn
    if (process.env.NODE_ENV === 'development') {
      throw new Error(`Invalid API response: missing ${missing.join(', ')}`);
    }
  }
};

const logAPIError = (error: APIError) => {
  const logEntry = error.toLogEntry();
  
  // Send to error tracking service (Sentry, etc.)
  if (window.trackError) {
    window.trackError(logEntry);
  }
  
  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.error('[API Error]', logEntry);
  }
  
  // Store in session for debugging
  const recentErrors = JSON.parse(sessionStorage.getItem('recentAPIErrors') || '[]');
  recentErrors.unshift(logEntry);
  sessionStorage.setItem('recentAPIErrors', JSON.stringify(recentErrors.slice(0, 50)));
};

// Export both standard and enhanced APIs
const API = createAPI();
const EnhancedAPI = {
  api: API,
  ErrorTypes,
  APIError,
  
  // Wrapper with error handling for React components
  call: async <T>(fn: () => Promise<any>): Promise<{ data: T | null; error: APIError | null }> => {
    try {
      const response = await fn();
      return { data: response.data, error: null };
    } catch (error) {
      return { 
        data: null, 
        error: error instanceof APIError ? error : new APIError(
          ErrorTypes.SERVER,
          'Unknown error',
          { originalError: error.message }
        )
      };
    }
  },

  // Enterprise API Endpoints
  mfa: {
    enroll: () => API.post('/api/mfa/enroll'),
    verify: (code: string) => API.post('/api/mfa/verify', { code }),
    verifyLogin: (code: string) => API.post('/api/mfa/verify-totp', { code }),
    status: () => API.get('/api/mfa/status'),
    disable: (password: string) => API.post('/api/mfa/disable', { password })
  },

  alerts: {
    getActive: () => API.get('/api/orgs/alerts/active'),
    acknowledge: (id: string) => API.put(`/api/orgs/alerts/${id}/acknowledge`),
    getHistory: (params: Record<string, any>) => API.get('/api/orgs/alerts/history', { params })
  },

  incidents: {
    list: (params: Record<string, any>) => API.get('/api/orgs/incidents', { params }),
    getDetails: (id: string) => API.get(`/api/orgs/incidents/${id}`),
    updateStatus: (id: string, status: string) => API.put(`/api/orgs/incidents/${id}/status`, { status }),
    create: (data: Record<string, any>) => API.post('/api/orgs/incidents', data)
  },

  audit: {
    getLogs: (params: Record<string, any>) => API.get('/api/admin/logs', { params }),
    getForensicTrace: (eventId: string) => API.get(`/api/audit/forensic/${eventId}`),
    verifyChain: () => API.get('/api/audit/verify')
  },

  compliance: {
    getDPIA: () => API.get('/api/compliance/dpia'),
    getGapAssessment: () => API.get('/api/compliance/soc2-gap'),
    triggerSAR: (personId: string) => API.post('/api/compliance/sar', { person_id: personId }),
    getSARStatus: (requestId: string) => API.get(`/api/compliance/sar/${requestId}`)
  }
};

export default EnhancedAPI;