from celery import Celery

# from kombu import Exchange, Queue
from src.constants import CELERY_BACKEND_URL, CELERY_BROKER_URL

# default_queue_name = 'default'
# default_exchange_name = 'default'
# default_routing_key = 'default'
#
# sunshine_queue_name = 'sunshine'
# sunshine_routing_key = 'sunshine'
#
# moon_queue_name = 'moon'
# moon_routing_key = 'moon'
#
# default_exchange = Exchange(default_exchange_name, type='direct')
# default_queue = Queue(
#     default_queue_name,
#     default_exchange,
#     routing_key=default_routing_key)
#
# sunshine_queue = Queue(
#     sunshine_queue_name,
#     default_exchange,
#     routing_key=sunshine_routing_key)
#
# moon_queue = Queue(
#     moon_queue_name,
#     default_exchange,
#     routing_key=moon_queue_name)


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
    worker_prefetch_multiplier = 1  # For local start
    worker_concurrency = 3


def create_celery_app(name, config_class, task_routes) -> Celery:
    app = Celery(name, include=["src.tasks"])

    app.conf.mongodb_backend_settings = {
        "database": "etl-db",
        "taskmeta_collection": "celery-backend",
    }

    # app.conf.task_queues = (default_queue, sunshine_queue, moon_queue)
    #
    # app.conf.task_default_queue = default_queue_name
    # app.conf.task_default_exchange = default_exchange_name
    # app.conf.task_default_routing_key = default_routing_key

    app.config_from_object(config_class)
    app.conf.task_routes = task_routes
    # app.conf.timezone = "Europe/Kiev"
    return app


celery_app = create_celery_app(
    "celery_etl_newscatcher",
    AppCeleryConfig,
    {
        "clients_pipeline.tasks.run_task_chain": {"queue": "io-worker"},
        "newscatcher_hook": {"queue": "io-worker"},
        "specific_process_news_data": {"queue": "cpu-worker"},
        "send_data": {"queue": "sender-worker"},
    },
)
