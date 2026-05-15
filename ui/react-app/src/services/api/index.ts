/**
 * API barrel export
 */
export { default as apiClient } from './client';
export { APIError, ErrorTypes } from './client';
export type { ErrorType } from './client';

export {
  authAPI,
  recognitionAPI,
  enrollmentAPI,
  analyticsAPI,
  healthAPI,
  auditAPI,
  incidentAPI,
  alertAPI,
  complianceAPI,
  mfaAPI,
  adminAPI,
  cameraAPI,
  paymentAPI,
  aiAPI,
  webhookAPI,
} from './endpoints';

export type {
  APIResponse,
  PaginatedResponse,
  HealthStatus,
  DependencyStatus,
  AnalyticsData,
  ThreatData,
  SessionData,
  EventData,
  IncidentData,
  AlertData,
} from './types';
