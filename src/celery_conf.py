from celery import Celery
from celery.schedules import crontab

from src.constants import CELERY_BACKEND_URL, CELERY_BROKER_URL


class BaseCeleryConfig:
    broker_url = CELERY_BROKER_URL
    result_backend = CELERY_BACKEND_URL

    result_extended = True
    result_expires = 3600

    task_track_started = True
    task_acks_late = True
    task_default_expires = 3600
    task_reject_on_worker_lost = True

    task_time_limit = 3600
    task_soft_time_limit = 3600

    worker_send_task_events = True
    worker_start_timeout = 120
    worker_lost_wait = 60

    broker_heartbeat = 30
    broker_connection_timeout = 120
    broker_connection_max_retries = 2
    broker_connection_retry_on_startup = True


class AppCeleryConfig(BaseCeleryConfig):
    worker_prefetch_multiplier = 3
    worker_concurrency = 3


def create_celery_app(name, config_class, task_routes) -> Celery:
    app = Celery(name, include=["src.tasks"])
    app.config_from_object(config_class)
    app.conf.task_routes = task_routes
    app.conf.beat_schedule = {
        "clients_pipeline.tasks.run_task_chain": {
            "task": "clients_pipeline.tasks.run_task_chain",
            "schedule": crontab(hour=8, minute=0),
        },
    }
    return app


celery_app = create_celery_app(
    "celery_etl_newscatcher",
    AppCeleryConfig,
    {
        "clients_pipeline.tasks.run_task_chain": {"queue": "handle"},
        "newscatcher_hook": {"queue": "handle"},
        "process_news_data": {"queue": "handle"},
        "make_decision": {"queue": "handle"},
    },
)
