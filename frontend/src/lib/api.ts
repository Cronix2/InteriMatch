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

// --- Emails ---
export const generateEmail = (matchingResultId: string) =>
  api.post("/emails/generate", { matching_result_id: matchingResultId });

export const getEmail = (emailId: string) => api.get(`/emails/${emailId}`);

export const updateEmail = (
  emailId: string,
  data: { subject?: string; body?: string; status?: string }
) => api.put(`/emails/${emailId}`, data);

export default api;
