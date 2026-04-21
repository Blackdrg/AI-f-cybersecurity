import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
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

export default API;
