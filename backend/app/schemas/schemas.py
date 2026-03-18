"""
InteriMatch AI - Schémas Pydantic (validation entrée/sortie API)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


# ─── Candidat ────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    availability: str | None = None

class CandidateResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    location: str | None
    availability: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Profil extrait ─────────────────────────────────────────────────────────

class ExperienceItem(BaseModel):
    title: str
    company: str | None = None
    duration: str | None = None
    description: str | None = None

class EducationItem(BaseModel):
    diploma: str
    school: str | None = None
    year: str | None = None

class ExtractedProfileResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    skills: list[str]
    experiences: list[ExperienceItem]
    education: list[EducationItem]
    certifications: list[str]
    languages: list[str]
    mobility: str | None
    profile_summary: str | None
    years_of_experience: int | None
    desired_job_titles: list[str]
    extracted_at: datetime
    model_config = {"from_attributes": True}


# ─── CV ──────────────────────────────────────────────────────────────────────

class ResumeResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    file_name: str
    file_type: str | None
    imported_at: datetime
    model_config = {"from_attributes": True}

class CVUploadResponse(BaseModel):
    resume: ResumeResponse
    candidate: CandidateResponse
    extracted_profile: ExtractedProfileResponse


# ─── Offre d'emploi ─────────────────────────────────────────────────────────

class JobOfferResponse(BaseModel):
    id: uuid.UUID
    api_source_id: str
    title: str
    company_name: str | None
    location: str | None
    postal_code: str | None
    description: str | None
    required_skills: list[str]
    contract_type: str | None
    experience_level: str | None
    publication_date: datetime | None
    salary_info: str | None
    model_config = {"from_attributes": True}

class JobSearchRequest(BaseModel):
    keywords: str
    location: str | None = None
    department: str | None = None
    contract_type: str | None = None
    experience: str | None = None
    distance: int | None = None
    max_results: int = Field(default=20, le=100)


# ─── Matching ────────────────────────────────────────────────────────────────

class MatchingResultResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_offer_id: uuid.UUID
    global_score: float
    skills_score: float
    experience_score: float
    location_score: float
    education_score: float
    job_title_score: float
    explanation: str | None
    computed_at: datetime
    job_offer: JobOfferResponse | None = None
    model_config = {"from_attributes": True}

class MatchingRequest(BaseModel):
    candidate_id: uuid.UUID
    keywords: str | None = None
    location: str | None = None
    department: str | None = None
    contract_type: str | None = None
    max_results: int = Field(default=10, le=50)


# ─── Email ───────────────────────────────────────────────────────────────────

class GeneratedEmailResponse(BaseModel):
    id: uuid.UUID
    matching_result_id: uuid.UUID
    subject: str
    body: str
    recruiter_email: str | None = None
    status: str
    generated_at: datetime
    validated_at: datetime | None
    model_config = {"from_attributes": True}

class EmailGenerateRequest(BaseModel):
    matching_result_id: uuid.UUID

class EmailUpdateRequest(BaseModel):
    subject: str | None = None
    body: str | None = None
    status: str | None = None


# ─── User Settings ───────────────────────────────────────────────────────────

class UserSettingsResponse(BaseModel):
    first_name: str = ""
    last_name: str = ""
    company_name: str = ""
    theme: str = "system"
    agency_address: str = ""
    agency_phone: str = ""
    agency_email: str = ""
    agency_siret: str = ""
    email_template: str = ""
    ai_model: str = ""
    ai_base_url: str = ""
    ai_temperature: float | None = None
    ai_api_key_set: bool = False
    france_travail_client_id: str = ""
    france_travail_secret_set: bool = False
    totp_enabled: bool = False

class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    settings: UserSettingsResponse
    model_config = {"from_attributes": True}

class UserSettingsUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    theme: str | None = None
    agency_address: str | None = None
    agency_phone: str | None = None
    agency_email: str | None = None
    agency_siret: str | None = None
    email_template: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_base_url: str | None = None
    ai_temperature: float | None = None
    france_travail_client_id: str | None = None
    france_travail_client_secret: str | None = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

class DashboardStatsResponse(BaseModel):
    total_candidates: int = 0
    total_matchings: int = 0
    total_emails: int = 0
    emails_validated: int = 0
    average_score: float = 0.0
    recent_matchings: list[dict] = []
