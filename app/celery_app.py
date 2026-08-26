"""
Celery configuration for background pipeline processing.
Supports eager mode for local testing without Redis.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Redis connection
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Check if we should run in eager mode (for local testing without Redis)
EAGER_MODE = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

if EAGER_MODE:
    # Use in-memory broker and backend for testing
    celery_app = Celery(
        "analise_textos",
        broker="memory://",
        backend="cache+memory://",
        include=["pipeline.tasks"],
    )
    # Executa as tarefas inline (sem worker); sem isto o job fica
    # eternamente em "queued" pois ninguém consome o broker em memória.
    celery_app.conf.task_always_eager = True
else:
    celery_app = Celery(
        "analise_textos",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=["pipeline.tasks"],
    )

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="America/Sao_Paulo",
    enable_utc=True,
    # Task routing
    task_routes={
        "pipeline.tasks.run_pipeline": {"queue": "pipeline"},
    },
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result backend
    result_expires=86400,  # 24 hours
    # Beat schedule (for periodic tasks if needed)
    beat_schedule={
        # "cleanup-old-jobs": {
        #     "task": "pipeline.tasks.cleanup_old_jobs",
        #     "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        # },
    },
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["pipeline"])


@celery_app.task(bind=True, ignore_result=False)
def debug_task(self):
    """Debug task for testing."""
    print(f"Request: {self.request!r}")


if __name__ == "__main__":
    celery_app.start()