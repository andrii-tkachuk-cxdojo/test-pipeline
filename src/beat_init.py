from celery.schedules import crontab
from loguru import logger

from celery_conf import celery_app
from constants import MONGO_COLLECTION_CLIENTS
from db import MongoDBService


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    connection = MongoDBService()
    connection.connect()

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
