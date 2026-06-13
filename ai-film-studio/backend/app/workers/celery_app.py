from celery import Celery
from app.config import get_settings
settings = get_settings()
celery_app = Celery("ai_film_studio", broker=settings.redis_url, backend=settings.redis_url)

@celery_app.task
def ping() -> str:
    return "pong"
