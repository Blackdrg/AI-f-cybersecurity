import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 30000,
});

// Interceptor to add auth token
API.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor for standard response format
API.interceptors.response.use(
  (response) => {
    if (response.data && response.data.success === false) {
      return Promise.reject(new Error(response.data.error || "Unknown error"));
    }
    return response;
  },
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.error || error.message;
    return Promise.reject(new Error(message));
  }
);

export const login = async (email, password) => {
  const res = await API.post(`/api/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`);
  if (res.data.access_token) {
    localStorage.setItem("token", res.data.access_token);
    localStorage.setItem("user", JSON.stringify(res.data.user));
  }
  return res.data;
};

export const recognize = async (file, options = {}) => {
  const formData = new FormData();
  formData.append("image", file);
  
  // Add other options
  Object.keys(options).forEach(key => {
    formData.append(key, options[key]);
  });

  const res = await API.post("/api/recognize", formData);
  return res.data;
};

export const enroll = async (files, name, consent, options = {}) => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append("images", file);
  });
  formData.append("name", name);
  formData.append("consent", consent);
  
  // Add other options
  Object.keys(options).forEach(key => {
    formData.append(key, options[key]);
  });

  const res = await API.post("/api/enroll", formData);
  return res.data;
};

export const checkHealth = async () => {
  const res = await API.get("/health");
  return res.data;
};

export const checkDependencies = async () => {
  const res = await API.get("/api/dependencies");
  return res.data;
};

// Analytics APIs
export const getAnalytics = async (timeframe = '24h') => {
  const res = await API.get(`/api/analytics?timeframe=${timeframe}`);
  return res.data;
};

export const getRiskTrends = async () => {
  const res = await API.get('/api/analytics/risk-trends');
  return res.data;
};

export const getConfidenceDistribution = async () => {
  const res = await API.get('/api/analytics/confidence-distribution');
  return res.data;
};

// Events & Monitoring
export const getRecognitionEvents = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await API.get(`/api/events?${query}`);
  return res.data;
};

export const getLiveEvents = async (cameraId) => {
  const res = await API.get(`/api/events/live${cameraId ? `?camera_id=${cameraId}` : ''}`);
  return res.data;
};

// Decision Explanation
export const getDecisionExplanation = async (decisionId) => {
  const res = await API.get(`/api/explanations/${decisionId}`);
  return res.data;
};

export const getBiasReport = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await API.get(`/api/bias-report?${query}`);
  return res.data;
};

// Compliance & Governance
export const getComplianceStatus = async () => {
  const res = await API.get('/api/compliance/status');
  return res.data;
};

export const getPolicies = async () => {
  const res = await API.get('/api/policies');
  return res.data;
};

export const updatePolicy = async (policyId, data) => {
  const res = await API.put(`/api/policies/${policyId}`, data);
  return res.data;
};

// Deepfake Analysis
export const getDeepfakeThreats = async () => {
  const res = await API.get('/api/deepfake/threats');
  return res.data;
};

export const analyzeDeepfake = async (data) => {
  const res = await API.post('/api/deepfake/analyze', data);
  return res.data;
};

// Session Monitoring
export const getActiveSessions = async () => {
  const res = await API.get('/api/sessions/active');
  return res.data;
};

export const getSessionDetails = async (sessionId) => {
  const res = await API.get(`/api/sessions/${sessionId}`);
  return res.data;
};

export const terminateSession = async (sessionId) => {
  const res = await API.post(`/api/sessions/${sessionId}/terminate`);
  return res.data;
};

// Identity Management
export const getIdentities = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await API.get(`/api/identities?${query}`);
  return res.data;
};

export const getIdentity = async (id) => {
  const res = await API.get(`/api/identities/${id}`);
  return res.data;
};

export const updateIdentity = async (id, data) => {
  const res = await API.put(`/api/identities/${id}`, data);
  return res.data;
};

export default API;
