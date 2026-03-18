"""
InteriMatch AI - Modèles SQLAlchemy
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ─── Utilisateur ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="recruiter")  # admin, recruiter, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)

    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    company_name = Column(String(255), default="")
    theme = Column(String(20), default="system")  # light, dark, system

    # IA overrides
    ai_api_key = Column(String(500), default="")
    ai_model = Column(String(100), default="")
    ai_base_url = Column(String(500), default="")
    ai_temperature = Column(Float, nullable=True)

    # France Travail overrides
    france_travail_client_id = Column(String(255), default="")
    france_travail_client_secret = Column(String(255), default="")

    # 2FA
    totp_enabled = Column(Boolean, default=False)
    totp_secret = Column(String(255), nullable=True)

    updated_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="settings")


# ─── Candidat ───────────────────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    phone = Column(String(50))
    location = Column(String(255))
    availability = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    matching_results = relationship("MatchingResult", back_populates="candidate", cascade="all, delete-orphan")


# ─── CV ─────────────────────────────────────────────────────────────────────

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20))  # pdf, docx
    file_path = Column(String(500), nullable=False)
    raw_text = Column(Text)
    imported_at = Column(DateTime(timezone=True), default=utcnow)

    candidate = relationship("Candidate", back_populates="resumes")
    extracted_profile = relationship("ExtractedProfile", back_populates="resume", uselist=False, cascade="all, delete-orphan")


# ─── Profil extrait par IA ──────────────────────────────────────────────────

class ExtractedProfile(Base):
    __tablename__ = "extracted_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False, unique=True)

    skills = Column(JSON, default=list)            # ["Python", "SQL", ...]
    experiences = Column(JSON, default=list)        # [{"title": "...", "company": "...", "duration": "..."}]
    education = Column(JSON, default=list)          # [{"diploma": "...", "school": "...", "year": "..."}]
    certifications = Column(JSON, default=list)
    languages = Column(JSON, default=list)
    mobility = Column(String(255))
    profile_summary = Column(Text)
    years_of_experience = Column(Integer)
    desired_job_titles = Column(JSON, default=list)

    extracted_at = Column(DateTime(timezone=True), default=utcnow)

    resume = relationship("Resume", back_populates="extracted_profile")


# ─── Offre d'emploi ─────────────────────────────────────────────────────────

class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_source_id = Column(String(100), unique=True, index=True)  # ID France Travail
    title = Column(String(500), nullable=False)
    company_name = Column(String(255))
    location = Column(String(255))
    postal_code = Column(String(10))
    description = Column(Text)
    required_skills = Column(JSON, default=list)
    contract_type = Column(String(50))
    experience_level = Column(String(100))
    publication_date = Column(DateTime(timezone=True))
    salary_info = Column(String(255))
    raw_data = Column(JSON)  # Données brutes de l'API

    fetched_at = Column(DateTime(timezone=True), default=utcnow)

    matching_results = relationship("MatchingResult", back_populates="job_offer")


# ─── Résultat de matching ───────────────────────────────────────────────────

class MatchingResult(Base):
    __tablename__ = "matching_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    job_offer_id = Column(UUID(as_uuid=True), ForeignKey("job_offers.id"), nullable=False)

    global_score = Column(Float, nullable=False)
    skills_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    job_title_score = Column(Float, default=0.0)
    explanation = Column(Text)

    computed_at = Column(DateTime(timezone=True), default=utcnow)

    candidate = relationship("Candidate", back_populates="matching_results")
    job_offer = relationship("JobOffer", back_populates="matching_results")
    generated_email = relationship("GeneratedEmail", back_populates="matching_result", uselist=False, cascade="all, delete-orphan")


# ─── Email généré ───────────────────────────────────────────────────────────

class GeneratedEmail(Base):
    __tablename__ = "generated_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matching_result_id = Column(UUID(as_uuid=True), ForeignKey("matching_results.id"), nullable=False, unique=True)

    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default="draft")  # draft, validated, sent
    generated_at = Column(DateTime(timezone=True), default=utcnow)
    validated_at = Column(DateTime(timezone=True), nullable=True)

    matching_result = relationship("MatchingResult", back_populates="generated_email")


# ─── Journal d'audit ────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(100))
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)
