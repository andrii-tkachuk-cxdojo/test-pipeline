from celery import Celery
from celery.schedules import crontab
from loguru import logger

# from kombu import Exchange, Queue
from src.constants import (
    CELERY_BACKEND_URL,
    CELERY_BROKER_URL,
    MONGO_COLLECTION_CLIENTS,
)
from src.db import MongoDBService

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
    worker_prefetch_multiplier = 3
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
    app.conf.timezone = "Europe/Kiev"
    return app


celery_app = create_celery_app(
    "celery_etl_newscatcher",
    AppCeleryConfig,
    {
        "clients_pipeline.tasks.run_task_chain": {"queue": "handle"},
        "newscatcher_hook": {"queue": "handle"},
        "making_decision": {"queue": "making-decision"},
        "process_news_data": {"queue": "handle"},
        "send_data": {"queue": "handle"},
    },
)


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    connection = MongoDBService()
    connection.connect()
    connection.load_data_from_json("../clients.json", MONGO_COLLECTION_CLIENTS)

    schedule_data = connection.get_all_clients(MONGO_COLLECTION_CLIENTS)
    for client in schedule_data:
        logger.info(
            f"Schedule for client '{client['client']}' updated success."
        )
        update_schedule_from_db(sender, client)


def update_schedule_from_db(sender, db_data):
    schedule = {}
    for client in db_data:
        task_name = f"task_for_{client['client']}"
        cron_args = parse_cron_string(client["cron"])
        schedule[task_name] = {
            "task": "clients_pipeline.tasks.run_task_chain",
            "schedule": crontab(**cron_args),
            "kwargs": {"client": client["client"]},
        }
    sender.conf.beat_schedule = schedule


def parse_cron_string(cron_str):
    minute, hour, day_of_month, month, day_of_week = cron_str.split()
    return {
        "minute": minute,
        "hour": hour,
        "day_of_month": day_of_month,
        "month_of_year": month,
        "day_of_week": day_of_week,
    }
