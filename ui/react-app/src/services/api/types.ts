/**
 * API Response Types
 *
 * Centralized type definitions for API responses.
 */

// ─── Generic Wrappers ───────────────────────────────────────────

export interface APIResponse<T = unknown> {
  success: boolean;
  data: T;
  error: string | null;
}

export interface PaginatedResponse<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// ─── Health ─────────────────────────────────────────────────────

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unconfigured';
  production_systems?: boolean;
  timestamp?: string;
  version?: string;
  uptime?: number;
}

export interface DependencyStatus {
  overall: 'healthy' | 'degraded' | 'unhealthy' | 'unconfigured';
  dependencies: Record<string, string>;
}

// ─── Analytics ──────────────────────────────────────────────────

export interface AnalyticsData {
  recognition_count: number;
  enroll_count: number;
  active_sessions: number;
  false_accepts: number;
  false_rejects: number;
  avg_confidence: number;
  deepfake_detected: number;
}

// ─── Threats ────────────────────────────────────────────────────

export interface ThreatData {
  type: string;
  confidence: number;
  timestamp: string;
  source?: string;
  details?: Record<string, unknown>;
}

// ─── Sessions ───────────────────────────────────────────────────

export interface SessionData {
  person_name: string;
  device_id: string;
  last_active: string;
  confidence: number;
}

// ─── Events ─────────────────────────────────────────────────────

export interface EventData {
  timestamp: string;
  person_name: string;
  method: string;
  confidence: number;
  risk_score: number;
  decision: string;
}

// ─── Incidents ──────────────────────────────────────────────────

export interface IncidentData {
  id: string;
  title: string;
  status: 'open' | 'investigating' | 'resolved' | 'closed';
  severity: 'critical' | 'high' | 'medium' | 'low';
  created_at: string;
  updated_at: string;
  assignee?: string;
  description?: string;
}

// ─── Alerts ─────────────────────────────────────────────────────

export interface AlertData {
  id: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  timestamp: string;
  acknowledged: boolean;
}
