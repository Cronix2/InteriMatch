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
export const login = (email: string, password: string, totp_code?: string) =>
  api.post("/auth/login", { email, password, totp_code: totp_code || undefined });

export const register = (email: string, password: string, full_name: string) =>
  api.post("/auth/register", { email, password, full_name });

// --- 2FA ---
export const setup2FA = () => api.post("/auth/2fa/setup");

export const verify2FA = (code: string) =>
  api.post("/auth/2fa/verify", { code });

export const disable2FA = (code: string) =>
  api.post("/auth/2fa/disable", { code });

// --- CV ---
export const uploadCV = (file: File, force?: string, duplicateCandidateId?: string) => {
  const formData = new FormData();
  formData.append("file", file);
  if (force) formData.append("force", force);
  if (duplicateCandidateId) formData.append("duplicate_candidate_id", duplicateCandidateId);
  return api.post("/cv/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getExtractedProfile = (resumeId: string) =>
  api.get(`/cv/profile/${resumeId}`);

export const getCandidateProfile = (candidateId: string) =>
  api.get(`/cv/candidate/${candidateId}/profile`);

export const downloadAnonymizedCV = (candidateId: string) =>
  api.get(`/cv/candidate/${candidateId}/anonymized-cv`, { responseType: "blob" });

// --- Candidats ---
export const listCandidates = () => api.get("/candidates/");

export const getCandidate = (id: string) => api.get(`/candidates/${id}`);

export const listPipelineCandidates = () => api.get("/candidates/pipeline");

export const updateCandidateStatus = (candidateId: string, status: string) =>
  api.put(`/candidates/${candidateId}/processing-status`, { status });

export const deleteCandidate = (candidateId: string) =>
  api.delete(`/candidates/${candidateId}`);

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

export const getProposalCounts = () => api.get("/matching/proposals/counts");

export const getMatchingHistory = () => api.get("/matching/history");

// --- Emails ---
export const generateEmail = (matchingResultId: string) =>
  api.post("/emails/generate", { matching_result_id: matchingResultId });

export const getEmailByMatching = (matchingId: string) =>
  api.get(`/emails/by-matching/${matchingId}`);

export const getEmail = (emailId: string) => api.get(`/emails/${emailId}`);

export const updateEmail = (
  emailId: string,
  data: { subject?: string; body?: string; status?: string }
) => api.put(`/emails/${emailId}`, data);

export const downloadEmailEml = (emailId: string, candidateId: string) =>
  api.get(`/emails/${emailId}/download-eml`, {
    params: { candidate_id: candidateId },
    responseType: "blob",
  });

export const getCompanyContacts = (domain: string) =>
  api.get(`/emails/company-contacts/${encodeURIComponent(domain)}`);

export const getCompanyContactsByName = (companyName: string) =>
  api.get(`/emails/company-contacts-by-name`, { params: { company: companyName } });

export const updateEmailRecipients = (emailId: string, recruiterEmail: string) =>
  api.put(`/emails/${emailId}/recipients`, { recruiter_email: recruiterEmail });

export const sendEmail = (emailId: string, candidateId: string) =>
  api.post(`/emails/${emailId}/send`, null, { params: { candidate_id: candidateId } });

export const getSmtpStatus = () => api.get("/emails/smtp/status");

// --- Settings ---
export const getMe = () => api.get("/settings/me");

export const updateSettings = (data: {
  email?: string;
  first_name?: string;
  last_name?: string;
  company_name?: string;
  theme?: string;
  agency_address?: string;
  agency_phone?: string;
  agency_email?: string;
  agency_siret?: string;
  email_template?: string;
  ai_provider?: string;
  ai_api_key?: string;
  ai_model?: string;
  ai_base_url?: string;
  ai_temperature?: number;
  france_travail_client_id?: string;
  france_travail_client_secret?: string;
  hunter_api_key?: string;
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  smtp_use_tls?: boolean;
  smtp_from?: string;
}) => api.put("/settings/me", data);

export const getAiProviders = () => api.get("/settings/ai-providers");

export const changePassword = (
  current_password: string,
  new_password: string
) => api.put("/settings/me/password", { current_password, new_password });

// --- Dashboard ---
export const getDashboardStats = () => api.get("/dashboard/stats");
export const getApiMetrics = () => api.get("/dashboard/api-metrics");

// --- Upload groupé (ZIP) ---
export const uploadBulkCV = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/bulk-upload/upload-zip", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const getBulkJobs = () => api.get("/bulk-upload/jobs");

export const getBulkJobStatus = (jobId: string) =>
  api.get(`/bulk-upload/jobs/${jobId}`);

export const pauseBulkJob = (jobId: string) =>
  api.put(`/bulk-upload/jobs/${jobId}/pause`);

export const resumeBulkJob = (jobId: string) =>
  api.put(`/bulk-upload/jobs/${jobId}/resume`);

export const cancelBulkJob = (jobId: string) =>
  api.put(`/bulk-upload/jobs/${jobId}/cancel`);

// --- Recruteur ---
export const lookupRecruiter = (jobOfferId: string) =>
  api.get(`/recruiter/job/${jobOfferId}`);

export default api;
