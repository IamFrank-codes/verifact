from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
import logging

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.db import Base, engine, get_db
from app.models import Claim, Evidence, PasswordResetToken, ProviderRun, User, Verification
from app.schemas import ForgotPasswordInput, LoginInput, RegisterInput, ResetPasswordInput, ShareInput, VerificationInput
from app.security import create_access_token, decode_access_token, hash_password, new_reset_token, token_hash, verify_password
from app.services.email import send_password_reset_email
from app.services.jobs import enqueue_verification, redis_ready
from app.services.verification import run_verification

logger = logging.getLogger('verifact')
settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        length = request.headers.get('content-length')
        if length and int(length) > settings.max_request_bytes:
            return JSONResponse({'detail': 'Request body is too large.'}, status_code=413)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if settings.is_production:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response


app = FastAPI(
    title='VeriFact API',
    version='1.1.0',
    description='Evidence-based claim verification. Scores are conditional on retrieved evidence and policy eligibility.',
    docs_url='/docs' if not settings.is_production else None,
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.host_list)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'X-Requested-With'],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception('Unhandled VeriFact request failure', extra={'path': request.url.path})
    return JSONResponse({'detail': 'VeriFact could not complete that request. Please retry.'}, status_code=500)


@app.on_event('startup')
def startup():
    # Development remains one-command friendly. Production schema changes are executed by Alembic.
    if not settings.is_production and settings.uses_sqlite:
        Base.metadata.create_all(bind=engine)


def user_out(user: User):
    return {'id': user.id, 'full_name': user.full_name, 'email': user.email, 'email_verified': user.email_verified}


def current_user(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail='Authentication is required.')
    user_id = decode_access_token(access_token)
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail='Your session has expired. Please sign in again.')
    return user


def source_out(source):
    return {'id': source.id, 'name': source.name, 'url': source.canonical_url, 'domain': source.domain, 'source_type': source.source_type, 'quality_class': source.quality_class, 'policy_version': source.policy_version, 'policy_rule': source.policy_rule, 'policy_rationale': source.policy_rationale}


def claim_out(claim: Claim):
    return {'id': claim.id, 'sequence': claim.sequence, 'text': claim.text, 'checkable': claim.checkable, 'claim_type': claim.claim_type, 'verdict': claim.verdict, 'explanation': claim.explanation, 'evidence_coverage': claim.evidence_coverage, 'freshness_note': claim.freshness_note, 'evidence': [{'id': e.id, 'relationship_type': e.relationship_type, 'excerpt': e.excerpt, 'relevance': e.relevance, 'published_at': e.published_at, 'retrieved_at': e.retrieved_at.isoformat(), 'provider': e.provider, 'fixture': e.fixture, 'source': source_out(e.source)} for e in claim.evidence]}


def verification_out(v: Verification, detail: bool = True):
    score_record = v.score_record
    result = {'id': v.id, 'input_type': v.input_type, 'original_input': v.original_input, 'status': v.status, 'stage': v.stage, 'evidence_status': v.evidence_status, 'summary': v.summary, 'score': v.score, 'score_band': v.score_band, 'coverage_pct': v.coverage_pct, 'policy_version': v.policy_version, 'is_public': v.is_public, 'public_id': v.public_id, 'mode': v.mode, 'error_message': v.error_message, 'created_at': v.created_at.isoformat(), 'completed_at': v.completed_at.isoformat() if v.completed_at else None, 'score_details': {'eligible': score_record.eligible, 'eligibility_reason': score_record.eligibility_reason, 'formula_version': score_record.formula_version, 'components': score_record.components} if score_record else None}
    if detail:
        result['article'] = {'url': v.article.url, 'title': v.article.title, 'author': v.article.author, 'publisher': v.article.publisher, 'published_at': v.article.published_at, 'extraction_status': v.article.extraction_status} if v.article else None
        result['claims'] = [claim_out(c) for c in sorted(v.claims, key=lambda item: item.sequence)]
        result['provider_runs'] = [{'provider': p.provider, 'status': p.status, 'message': p.message} for p in v.provider_runs]
    return result


def get_owned(db: Session, user: User, verification_id: str) -> Verification:
    v = db.query(Verification).options(joinedload(Verification.article), joinedload(Verification.claims).joinedload(Claim.evidence).joinedload(Evidence.source), joinedload(Verification.score_record), joinedload(Verification.provider_runs)).filter(Verification.id == verification_id, Verification.user_id == user.id).first()
    if not v:
        raise HTTPException(status_code=404, detail='Verification not found.')
    return v


@app.get('/health')
def health():
    return {'service': 'VeriFact API', 'status': 'ok', 'mode': settings.mode, 'environment': settings.environment}


@app.get('/ready')
def ready():
    checks = {'database': 'ok', 'redis': 'not-configured'}
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    except Exception:
        logger.exception('Database readiness check failed')
        checks['database'] = 'unavailable'
    if settings.redis_url:
        checks['redis'] = 'ok' if redis_ready() else 'unavailable'
    if any(value == 'unavailable' for value in checks.values()):
        return JSONResponse({'service': 'VeriFact API', 'status': 'not-ready', 'checks': checks}, status_code=503)
    return {'service': 'VeriFact API', 'status': 'ready', 'checks': checks}


@app.post('/api/v1/auth/register', status_code=201)
@limiter.limit(settings.rate_limit_signup)
def register(request: Request, payload: RegisterInput, response: Response, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=422, detail='Passwords do not match.')
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail='An account with this email already exists.')
    user = User(full_name=payload.full_name.strip(), email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token(user.id)
    response.set_cookie('access_token', token, httponly=True, secure=settings.secure_cookies, samesite='lax', max_age=settings.access_token_minutes * 60, path='/')
    return {'user': user_out(user)}


@app.post('/api/v1/auth/login')
@limiter.limit(settings.rate_limit_auth)
def login(request: Request, payload: LoginInput, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password.')
    token = create_access_token(user.id)
    response.set_cookie('access_token', token, httponly=True, secure=settings.secure_cookies, samesite='lax', max_age=settings.access_token_minutes * 60, path='/')
    return {'user': user_out(user)}


@app.post('/api/v1/auth/logout')
def logout(response: Response):
    response.delete_cookie('access_token', path='/')
    return {'message': 'Signed out of VeriFact.'}


@app.get('/api/v1/auth/me')
def me(user: User = Depends(current_user)):
    return {'user': user_out(user)}


@app.post('/api/v1/auth/forgot-password')
@limiter.limit(settings.rate_limit_auth)
def forgot_password(request: Request, payload: ForgotPasswordInput, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    dev_token = None
    if user:
        raw, hashed = new_reset_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hashed, expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
        db.commit()
        if settings.mode == 'local-fixture':
            dev_token = raw
        elif settings.smtp_configured:
            try:
                send_password_reset_email(user.email, raw)
            except Exception:
                logger.exception('Password-reset email delivery failed')
    result = {'message': 'If an account exists for that email, VeriFact has sent reset instructions.'}
    if dev_token:
        result['development_reset_token'] = dev_token
    return result


@app.post('/api/v1/auth/reset-password')
@limiter.limit(settings.rate_limit_auth)
def reset_password(request: Request, payload: ResetPasswordInput, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=422, detail='Passwords do not match.')
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash(payload.token), PasswordResetToken.used_at.is_(None)).first()
    expires_at = record.expires_at.replace(tzinfo=timezone.utc) if record and record.expires_at.tzinfo is None else (record.expires_at if record else None)
    if not record or not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail='This reset link is invalid or has expired.')
    user = db.get(User, record.user_id)
    user.password_hash = hash_password(payload.password); record.used_at = datetime.now(timezone.utc); db.commit()
    return {'message': 'Password updated. You can now sign in to VeriFact.'}


@app.post('/api/v1/verifications', status_code=202)
def create_verification(payload: VerificationInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if len(payload.content.strip()) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail='The submission exceeds the VeriFact input limit.')
    v = Verification(user_id=user.id, input_type=payload.input_type, original_input=payload.content.strip(), mode=settings.mode)
    db.add(v); db.commit(); db.refresh(v)
    if settings.mode in {'hybrid', 'production'}:
        try:
            job_id = enqueue_verification(v.id)
        except Exception:
            logger.exception('Could not queue verification job')
            v.status = 'failed'
            v.stage = 'Queue unavailable'
            v.error_message = 'VeriFact could not queue this verification. Please retry.'
            db.commit()
            raise HTTPException(status_code=503, detail='VeriFact verification processing is temporarily unavailable.')
        return {'id': v.id, 'job_id': job_id, 'mode': settings.mode, 'status': v.status, 'stage': v.stage, 'message': 'VeriFact accepted the submission and queued evidence processing.'}
    return {'id': v.id, 'mode': settings.mode, 'status': v.status, 'stage': v.stage, 'message': 'VeriFact accepted the local demonstration submission.'}


@app.post('/api/v1/verifications/{verification_id}/run-fixture')
def run_fixture_now(verification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if settings.mode != 'local-fixture':
        raise HTTPException(status_code=404, detail='This development helper is unavailable outside local fixture mode.')
    v = get_owned(db, user, verification_id)
    run_verification(db, v.id)
    return verification_out(get_owned(db, user, verification_id))


@app.get('/api/v1/verifications')
def list_verifications(q: str | None = None, evidence_status: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = db.query(Verification).options(joinedload(Verification.score_record)).filter(Verification.user_id == user.id)
    if q: query = query.filter(Verification.original_input.ilike(f'%{q}%'))
    if evidence_status: query = query.filter(Verification.evidence_status == evidence_status)
    rows = query.order_by(Verification.created_at.desc()).limit(100).all()
    eligible = [x.score for x in rows if x.score is not None]
    return {'items': [verification_out(x, detail=False) for x in rows], 'stats': {'total': len(rows), 'average_score': round(sum(eligible) / len(eligible), 1) if eligible else None, 'scored_reports': len(eligible), 'insufficient_evidence_reports': sum(1 for x in rows if x.evidence_status == 'Insufficient evidence — no overall score')}}


@app.get('/api/v1/verifications/{verification_id}')
def get_verification(verification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return verification_out(get_owned(db, user, verification_id))


@app.get('/api/v1/verifications/{verification_id}/status')
def verification_status(verification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = get_owned(db, user, verification_id)
    return {'id': v.id, 'status': v.status, 'stage': v.stage, 'error_message': v.error_message}


@app.delete('/api/v1/verifications/{verification_id}')
def delete_verification(verification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = get_owned(db, user, verification_id); db.delete(v); db.commit(); return {'message': 'Verification deleted.'}


@app.post('/api/v1/verifications/{verification_id}/share')
def share_verification(verification_id: str, payload: ShareInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    v = get_owned(db, user, verification_id)
    v.is_public = payload.is_public
    if payload.is_public and not v.public_id: v.public_id = token_urlsafe(18)
    db.commit(); db.refresh(v)
    return {'is_public': v.is_public, 'public_id': v.public_id, 'url': f'{settings.public_base_url}/verifact/reports/{v.public_id}' if v.is_public else None}


@app.patch('/api/v1/verifications/{verification_id}/share')
def update_share(verification_id: str, payload: ShareInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return share_verification(verification_id, payload, user, db)


@app.get('/api/v1/reports/{public_id}')
def public_report(public_id: str, db: Session = Depends(get_db)):
    v = db.query(Verification).options(joinedload(Verification.article), joinedload(Verification.claims).joinedload(Claim.evidence).joinedload(Evidence.source), joinedload(Verification.score_record), joinedload(Verification.provider_runs)).filter(Verification.public_id == public_id, Verification.is_public.is_(True)).first()
    if not v:
        raise HTTPException(status_code=404, detail='This VeriFact report is unavailable or private.')
    return verification_out(v)
