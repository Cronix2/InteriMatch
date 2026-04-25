/**
 * Mock manuel de @/lib/api pour les tests.
 * Toutes les fonctions retournent une promesse résolue avec un payload neutre.
 * Utilisé via vi.mock("@/lib/api") dans vitest.setup.ts.
 */
import { vi } from "vitest";

const ok = <T>(data: T) => Promise.resolve({ data, status: 200, statusText: "OK", headers: {}, config: {} as Record<string, unknown> });

const emptySettings = {
  email: "test@example.com",
  settings: {
    first_name: "",
    last_name: "",
    company_name: "",
    theme: "light",
    agency_address: "",
    agency_phone: "",
    agency_email: "",
    agency_siret: "",
    email_template: "",
    ai_provider: "custom",
    ai_model: "",
    ai_base_url: "",
    ai_temperature: null,
    ai_api_key_set: false,
    france_travail_client_id: "",
    france_travail_secret_set: false,
    hunter_api_key_set: false,
    smtp_host: "",
    smtp_port: null,
    smtp_user: "",
    smtp_password_set: false,
    smtp_use_tls: true,
    smtp_from: "",
    setup_completed: true,
    totp_enabled: false,
  },
};

export const login = vi.fn(() => ok({ access_token: "tok", token_type: "bearer" }));
export const register = vi.fn(() => ok({ ok: true }));
export const setup2FA = vi.fn(() => ok({ qr_code: "data:image/png;base64,xxx", secret: "ABC" }));
export const verify2FA = vi.fn(() => ok({ ok: true }));
export const disable2FA = vi.fn(() => ok({ ok: true }));

export const uploadCV = vi.fn(() => ok({ candidate_id: "c1" }));
export const getExtractedProfile = vi.fn(() => ok({}));
export const getCandidateProfile = vi.fn(() => ok({ id: "c1", first_name: "", last_name: "", profile: { skills: [], experiences: [], education: [], desired_job_titles: [], languages: [] } }));
export const downloadAnonymizedCV = vi.fn(() => ok(new Blob([])));

export const listPipelineCandidates = vi.fn(() => ok([]));
export const updateCandidateStatus = vi.fn(() => ok({ ok: true }));
export const deleteCandidate = vi.fn(() => ok({ ok: true }));

export const searchJobOffers = vi.fn(() => ok([]));
export const computeMatching = vi.fn(() => ok({ matchings: [] }));
export const getCandidateMatchings = vi.fn(() => ok([]));
export const getProposalCounts = vi.fn(() => ok({}));
export const getMatchingHistory = vi.fn(() => ok([]));

export const generateEmail = vi.fn(() => ok({ id: "e1", subject: "S", body: "B", recruiter_email: null, status: "draft" }));
export const getEmailByMatching = vi.fn(() => Promise.reject({ response: { status: 404 } }));
export const getEmail = vi.fn(() => ok({}));
export const updateEmail = vi.fn(() => ok({}));
export const downloadEmailEml = vi.fn(() => ok(new Blob([])));
export const getCompanyContacts = vi.fn(() => ok([]));
export const getCompanyContactsByName = vi.fn(() => ok([]));
export const updateEmailRecipients = vi.fn(() => ok({}));
export const sendEmail = vi.fn(() => ok({ recipients: [], sent_at: null }));
export const getSmtpStatus = vi.fn(() => ok({ ready: false }));

export const getMe = vi.fn(() => ok(emptySettings));
export const updateSettings = vi.fn(() => ok({ ok: true }));
export const getAiProviders = vi.fn(() => ok([]));
export const changePassword = vi.fn(() => ok({ ok: true }));

export const getDashboardStats = vi.fn(() => ok({ total_candidates: 0, total_matchings: 0, total_emails: 0, recent_matchings: [] }));
export const getApiMetrics = vi.fn(() => ok({ daily: [], by_action: [] }));

export const uploadBulkCV = vi.fn(() => ok({ id: "j1" }));
export const getBulkJobs = vi.fn(() => ok([]));
export const getBulkJobStatus = vi.fn(() => ok({ id: "j1", status: "completed", total_files: 0, processed_files: 0, successful_files: 0, failed_files: 0, results: [] }));
export const pauseBulkJob = vi.fn(() => ok({ ok: true }));
export const resumeBulkJob = vi.fn(() => ok({ ok: true }));
export const cancelBulkJob = vi.fn(() => ok({ ok: true }));

export const lookupRecruiter = vi.fn(() => ok({ contact: {}, company_name: null }));

const api = {
  get: vi.fn(() => ok({})),
  post: vi.fn(() => ok({})),
  put: vi.fn(() => ok({})),
  delete: vi.fn(() => ok({})),
  interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
};
export default api;
