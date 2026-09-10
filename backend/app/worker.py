import logging
import time
from rq import Worker

from app.core.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Verification
from app.services.jobs import QUEUE_NAME, get_redis
from app.services.verification import run_verification

logger = logging.getLogger('verifact.worker')
settings = get_settings()


def run_verification_job(verification_id: str):
    db = SessionLocal()
    try:
        run_verification(db, verification_id)
    finally:
        db.close()


def local_polling_loop():
    """Compatibility path for one-command local fixture development without Redis."""
    while True:
        db = SessionLocal()
        try:
            queued = db.query(Verification).filter(Verification.status == 'queued').order_by(Verification.created_at).first()
            if queued:
                run_verification(db, queued.id)
            else:
                time.sleep(1)
        finally:
            db.close()


def main():
    if not settings.is_production and settings.uses_sqlite:
        Base.metadata.create_all(bind=engine)
    if settings.redis_url:
        worker = Worker([QUEUE_NAME], connection=get_redis(), name='verifact-worker')
        logger.info('Starting VeriFact Redis worker')
        worker.work(with_scheduler=True)
    else:
        logger.warning('Redis is not configured; using local polling fallback.')
        local_polling_loop()


if __name__ == '__main__':
    main()
