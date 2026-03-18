import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Intercepteur pour ajouter le token JWT
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("interimatch_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Intercepteur réponse : redirection auto si token expiré (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      typeof window !== "undefined" &&
      !error.config?.url?.includes("/auth/") &&
      !error.config?.url?.includes("/settings/me")
    ) {
      localStorage.removeItem("interimatch_token");
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

// --- Auth ---
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password });

export const register = (email: string, password: string, full_name: string) =>
  api.post("/auth/register", { email, password, full_name });

// --- CV ---
export const uploadCV = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/cv/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getExtractedProfile = (resumeId: string) =>
  api.get(`/cv/profile/${resumeId}`);

// --- Candidats ---
export const listCandidates = () => api.get("/candidates/");

export const getCandidate = (id: string) => api.get(`/candidates/${id}`);

// --- Offres ---
export const searchJobOffers = (params: {
  keywords: string;
  location?: string;
  department?: string;
  contract_type?: string;
  max_results?: number;
}) => api.post("/job-offers/search", params);

// --- Matching ---
export const computeMatching = (params: {
  candidate_id: string;
  keywords?: string;
  location?: string;
  department?: string;
  contract_type?: string;
  max_results?: number;
}) => api.post("/matching/compute", params);

export const getCandidateMatchings = (candidateId: string) =>
  api.get(`/matching/candidate/${candidateId}`);

export const getMatchingHistory = () => api.get("/matching/history");

// --- Emails ---
export const generateEmail = (matchingResultId: string) =>
  api.post("/emails/generate", { matching_result_id: matchingResultId });

export const getEmail = (emailId: string) => api.get(`/emails/${emailId}`);

export const updateEmail = (
  emailId: string,
  data: { subject?: string; body?: string; status?: string }
) => api.put(`/emails/${emailId}`, data);

// --- Settings ---
export const getMe = () => api.get("/settings/me");

export const updateSettings = (data: {
  email?: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  theme?: string;
  ai_api_key?: string;
  ai_model?: string;
  ai_base_url?: string;
  ai_temperature?: number;
  france_travail_client_id?: string;
  france_travail_client_secret?: string;
}) => api.put("/settings/me", data);

export const changePassword = (
  current_password: string,
  new_password: string
) => api.put("/settings/me/password", { current_password, new_password });

// --- Dashboard ---
export const getDashboardStats = () => api.get("/dashboard/stats");

export default api;
