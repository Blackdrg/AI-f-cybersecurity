import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from "axios";

// Response wrapper interface
export interface APIResponse<T = any> {
  success: boolean;
  data: T;
  error: string | null;
}

const API: AxiosInstance = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 30000,
});

// Interceptor to add auth token
API.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Check sessionStorage first (preferred), fallback to localStorage for transition
    const token = sessionStorage.getItem("token") || localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor for standard response format
API.interceptors.response.use(
  (response: AxiosResponse) => {
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

export const login = async (email: string, password: string): Promise<any> => {
  const res = await API.post(`/api/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`);
  if (res.data.access_token) {
    // Security fix: Use sessionStorage instead of localStorage for JWT token
    // This mitigates XSS attacks from exfiltrating tokens
    // For production, implement httpOnly cookies for true XSS protection
    sessionStorage.setItem("token", res.data.access_token);
    sessionStorage.setItem("user", JSON.stringify(res.data.user));

    // Also store in localStorage for backwards compatibility during transition
    localStorage.setItem("user", JSON.stringify(res.data.user));
  }
  return res.data;
};

// Logout function to clear tokens
export const logout = () => {
  sessionStorage.removeItem("token");
  sessionStorage.removeItem("user");
  localStorage.removeItem("user");
};

export const recognize = async (file: File, options: Record<string, any> = {}): Promise<any> => {
  const formData = new FormData();
  formData.append("image", file);
  
  Object.keys(options).forEach(key => {
    formData.append(key, options[key]);
  });

  const res = await API.post("/api/recognize", formData);
  return res.data;
};

export const enroll = async (files: File[], name: string, consent: boolean, options: Record<string, any> = {}): Promise<any> => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append("images", file);
  });
  formData.append("name", name);
  formData.append("consent", consent.toString());
  
  Object.keys(options).forEach(key => {
    formData.append(key, options[key]);
  });

  const res = await API.post("/api/enroll", formData);
  return res.data;
};

export const getAuditLogs = async (params: Record<string, any> = {}): Promise<any> => {
  const query = new URLSearchParams(params).toString();
  const res = await API.get(`/api/admin/logs${query ? '?' + query : ''}`);
  return res.data;
};

// ... and so on for other methods
// Exporting the full list of methods as needed for the UI

export const getAnalytics = async (timeframe: string = '24h') => {
  const res = await API.get(`/api/analytics?timeframe=${timeframe}`);
  return res.data;
};

export const getIdentities = async (params: Record<string, any> = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await API.get(`/api/identities?${query}`);
  return res.data;
};

export const checkHealth = async () => {
  const res = await API.get("/api/health");
  return res.data;
};

export default API;
