/**
 * API Endpoints — Enterprise AI Platform
 *
 * All backend API calls in one place, fully typed.
 * Used by TanStack Query hooks and direct calls.
 */
import apiClient from './client';

// ─── Auth ───────────────────────────────────────────────────────

export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post(`/api/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`),

  logout: () => apiClient.post('/api/auth/logout'),

  me: () => apiClient.get('/api/users/me'),
};

// ─── Recognition ────────────────────────────────────────────────

export const recognitionAPI = {
  recognize: (file: File, options: Record<string, string> = {}) => {
    const formData = new FormData();
    formData.append('image', file);
    Object.entries(options).forEach(([key, value]) => formData.append(key, value));
    return apiClient.post('/api/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  recognizeStream: (file: File) => {
    const formData = new FormData();
    formData.append('image', file);
    return apiClient.post('/api/recognize/stream', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      responseType: 'stream',
    });
  },
};

// ─── Enrollment ─────────────────────────────────────────────────

export const enrollmentAPI = {
  enroll: (files: File[], name: string, consent: boolean, options: Record<string, string> = {}) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('images', file));
    formData.append('name', name);
    formData.append('consent', consent.toString());
    Object.entries(options).forEach(([key, value]) => formData.append(key, value));
    return apiClient.post('/api/enroll', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getIdentities: (params: Record<string, string> = {}) =>
    apiClient.get('/api/identities', { params }),
};

// ─── Analytics & Dashboard ──────────────────────────────────────

export const analyticsAPI = {
  getAnalytics: (timeframe = '24h') =>
    apiClient.get(`/api/analytics`, { params: { timeframe } }),

  getEvents: (orgId: string, limit = 50) =>
    apiClient.get(`/api/orgs/${orgId}/events`, { params: { limit } }),

  getActiveSessions: () => apiClient.get('/api/sessions/active'),

  getThreats: () => apiClient.get('/api/security/threats'),
};

// ─── Health ─────────────────────────────────────────────────────

export const healthAPI = {
  check: () => apiClient.get('/api/health'),
  checkDependencies: () => apiClient.get('/api/health/dependencies'),
};

// ─── Audit ──────────────────────────────────────────────────────

export const auditAPI = {
  getLogs: (params: Record<string, string> = {}) =>
    apiClient.get('/api/logs', { params }),

  getForensicTrace: (eventId: string) =>
    apiClient.get(`/api/audit/forensic/${eventId}`),

  verifyChain: () => apiClient.get('/api/audit/verify'),
};

// ─── Incidents & Alerts ─────────────────────────────────────────

export const incidentAPI = {
  list: (params: Record<string, string> = {}) =>
    apiClient.get('/api/orgs/incidents', { params }),

  getDetails: (id: string) => apiClient.get(`/api/orgs/incidents/${id}`),

  updateStatus: (id: string, status: string) =>
    apiClient.put(`/api/orgs/incidents/${id}/status`, { status }),

  create: (data: Record<string, unknown>) =>
    apiClient.post('/api/orgs/incidents', data),
};

export const alertAPI = {
  getActive: () => apiClient.get('/api/orgs/alerts/active'),

  acknowledge: (id: string) =>
    apiClient.put(`/api/orgs/alerts/${id}/acknowledge`),

  getHistory: (params: Record<string, string> = {}) =>
    apiClient.get('/api/orgs/alerts/history', { params }),
};

// ─── Compliance ─────────────────────────────────────────────────

export const complianceAPI = {
  getDPIA: () => apiClient.get('/api/compliance/dpia'),
  getGapAssessment: () => apiClient.get('/api/compliance/soc2-gap'),
  triggerSAR: (personId: string) =>
    apiClient.post('/api/compliance/sar', { person_id: personId }),
  getSARStatus: (requestId: string) =>
    apiClient.get(`/api/compliance/sar/${requestId}`),
};

// ─── MFA ────────────────────────────────────────────────────────

export const mfaAPI = {
  enroll: () => apiClient.post('/api/mfa/enroll'),
  verify: (code: string) => apiClient.post('/api/mfa/verify', { code }),
  verifyLogin: (code: string) => apiClient.post('/api/mfa/verify-totp', { code }),
  status: () => apiClient.get('/api/mfa/status'),
  disable: (password: string) => apiClient.post('/api/mfa/disable', { password }),
};

// ─── Admin ──────────────────────────────────────────────────────

export const adminAPI = {
  getUsers: (params: Record<string, string> = {}) =>
    apiClient.get('/api/admin/users', { params }),

  updateUserRole: (userId: string, role: string) =>
    apiClient.put(`/api/admin/users/${userId}/role`, { role }),

  getOrganizations: () => apiClient.get('/api/admin/organizations'),

  getSystemMetrics: () => apiClient.get('/api/admin/metrics'),
};

// ─── Cameras ────────────────────────────────────────────────────

export const cameraAPI = {
  list: () => apiClient.get('/api/cameras'),
  create: (data: Record<string, unknown>) => apiClient.post('/api/cameras', data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.put(`/api/cameras/${id}`, data),
  delete: (id: string) => apiClient.delete(`/api/cameras/${id}`),
};

// ─── Subscriptions & Payments ───────────────────────────────────

export const paymentAPI = {
  getPlans: () => apiClient.get('/api/plans'),
  subscribe: (planId: string) => apiClient.post('/api/subscriptions', { plan_id: planId }),
  getCurrentSubscription: () => apiClient.get('/api/subscriptions/current'),
  cancelSubscription: () => apiClient.delete('/api/subscriptions'),
  getUsage: () => apiClient.get('/api/usage'),
};

// ─── AI Assistant ───────────────────────────────────────────────

export const aiAPI = {
  chat: (message: string, context?: Record<string, unknown>) =>
    apiClient.post('/api/ai/chat', { message, context }),

  chatStream: (message: string, context?: Record<string, unknown>) =>
    apiClient.post('/api/ai/chat', { message, context, stream: true }, {
      responseType: 'stream',
    }),
};

// ─── Webhooks ───────────────────────────────────────────────────

export const webhookAPI = {
  list: () => apiClient.get('/api/webhooks'),
  create: (data: Record<string, unknown>) => apiClient.post('/api/webhooks', data),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.put(`/api/webhooks/${id}`, data),
  delete: (id: string) => apiClient.delete(`/api/webhooks/${id}`),
  test: (id: string) => apiClient.post(`/api/webhooks/${id}/test`),
};

// ─── Legacy compat: default export for gradual migration ────────

export default apiClient;
