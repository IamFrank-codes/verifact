import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def uid() -> str:
    return str(uuid.uuid4())

def now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    verifications: Mapped[list['Verification']] = relationship(back_populates='user', cascade='all, delete-orphan')

class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Article(Base):
    __tablename__ = 'articles'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(String(300), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(300), nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str] = mapped_column(String(60), default='not_applicable')
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

class Verification(Base):
    __tablename__ = 'verifications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    article_id: Mapped[str | None] = mapped_column(ForeignKey('articles.id'), nullable=True)
    input_type: Mapped[str] = mapped_column(String(20))
    original_input: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='queued')
    stage: Mapped[str] = mapped_column(String(80), default='Queued for verification')
    evidence_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_band: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    policy_version: Mapped[str] = mapped_column(String(50), default='1.0.0')
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(40), default='local-fixture')
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped['User'] = relationship(back_populates='verifications')
    article: Mapped['Article | None'] = relationship()
    claims: Mapped[list['Claim']] = relationship(back_populates='verification', cascade='all, delete-orphan')
    score_record: Mapped['VerificationScore | None'] = relationship(back_populates='verification', cascade='all, delete-orphan', uselist=False)
    provider_runs: Mapped[list['ProviderRun']] = relationship(cascade='all, delete-orphan')

class Claim(Base):
    __tablename__ = 'claims'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    verification_id: Mapped[str] = mapped_column(ForeignKey('verifications.id'), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(60), default='factual')
    importance: Mapped[float] = mapped_column(Float, default=1.0)
    checkable: Mapped[bool] = mapped_column(Boolean, default=True)
    extraction_rationale: Mapped[str] = mapped_column(Text, default='Identified as a checkable factual statement.')
    verdict: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_coverage: Mapped[str | None] = mapped_column(String(200), nullable=True)
    freshness_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification: Mapped['Verification'] = relationship(back_populates='claims')
    evidence: Mapped[list['Evidence']] = relationship(back_populates='claim', cascade='all, delete-orphan')

class Source(Base):
    __tablename__ = 'sources'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    canonical_url: Mapped[str] = mapped_column(String(2048), unique=True)
    name: Mapped[str] = mapped_column(String(300))
    domain: Mapped[str] = mapped_column(String(300), index=True)
    source_type: Mapped[str] = mapped_column(String(100), default='Unknown')
    quality_class: Mapped[str] = mapped_column(String(30), default='Unknown')
    policy_version: Mapped[str] = mapped_column(String(50), default='1.0.0')
    policy_rule: Mapped[str] = mapped_column(String(160), default='default_unknown')
    policy_rationale: Mapped[str] = mapped_column(Text, default='No matching policy rule; classified as Unknown.')

class Evidence(Base):
    __tablename__ = 'evidence'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    claim_id: Mapped[str] = mapped_column(ForeignKey('claims.id'), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id'))
    relationship_type: Mapped[str] = mapped_column(String(30), default='contextual')
    excerpt: Mapped[str] = mapped_column(Text)
    relevance: Mapped[str] = mapped_column(Text)
    published_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    provider: Mapped[str] = mapped_column(String(100))
    fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    claim: Mapped['Claim'] = relationship(back_populates='evidence')
    source: Mapped['Source'] = relationship()

class VerificationScore(Base):
    __tablename__ = 'verification_scores'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    verification_id: Mapped[str] = mapped_column(ForeignKey('verifications.id'), unique=True)
    eligible: Mapped[bool] = mapped_column(Boolean)
    eligibility_reason: Mapped[str] = mapped_column(Text)
    formula_version: Mapped[str] = mapped_column(String(50), default='1.0.0')
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    verification: Mapped['Verification'] = relationship(back_populates='score_record')

class ProviderRun(Base):
    __tablename__ = 'provider_runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    verification_id: Mapped[str] = mapped_column(ForeignKey('verifications.id'), index=True)
    provider: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
