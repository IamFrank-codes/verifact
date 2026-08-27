import logging
from redis import Redis
from rq import Queue
from app.core.config import get_settings

logger = logging.getLogger('verifact.jobs')
settings = get_settings()
QUEUE_NAME = 'verifact-verifications'


def get_redis() -> Redis:
    if not settings.redis_url:
        raise RuntimeError('Redis is not configured.')
    return Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=20)


def enqueue_verification(verification_id: str) -> str:
    queue = Queue(QUEUE_NAME, connection=get_redis(), default_timeout=settings.request_timeout_seconds)
    job = queue.enqueue('app.worker.run_verification_job', verification_id, job_timeout=settings.request_timeout_seconds, result_ttl=3600, failure_ttl=86400)
    logger.info('Queued verification job %s for verification %s', job.id, verification_id)
    return job.id


def redis_ready() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:
        return False
