from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import get_settings

pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')
settings = get_settings()
ALGORITHM = 'HS256'

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({'sub': user_id, 'exp': expire}, settings.secret_key, algorithm=ALGORITHM)

def decode_access_token(token: str) -> str | None:
    try:
        return str(jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM]).get('sub'))
    except JWTError:
        return None

def new_reset_token() -> tuple[str, str]:
    raw = token_urlsafe(32)
    return raw, sha256(raw.encode()).hexdigest()

def token_hash(raw: str) -> str:
    return sha256(raw.encode()).hexdigest()
