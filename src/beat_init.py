from celery.schedules import crontab
from loguru import logger

from src.celery_conf import AppCeleryConfig, celery_app
from src.constants import MONGO_COLLECTION_CLIENTS
from src.db import MongoDBInit


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender: AppCeleryConfig, **kwargs) -> None:
    logger.info("Connecting to the database from beat...")
    connection = MongoDBInit()
    connection.connect()
    connection.load_data_from_json("clients.json")

    schedule_data = connection.get_all_clients(MONGO_COLLECTION_CLIENTS)
    for client in schedule_data:
        update_schedule_from_db(sender, client)
        logger.info(
            f"Schedule for client '{client['client']}' updated success."
        )


def update_schedule_from_db(
    sender: AppCeleryConfig, client_data: dict
) -> None:
    schedule = sender.conf.beat_schedule.copy()

    task_name = f"task_for_{client_data['client']}"
    cron_args = parse_cron_string(client_data["cron"])
    schedule[task_name] = {
        "task": "clients_pipeline.tasks.run_task_chain",
        "schedule": crontab(**cron_args),
        "kwargs": {"client": client_data["client"]},
    }
    sender.conf.beat_schedule = schedule


def parse_cron_string(cron_str: str) -> dict:
    try:
        minute, hour, day_of_month, month, day_of_week = cron_str.split()
        return {
            "minute": minute,
            "hour": hour,
            "day_of_month": day_of_month,
            "month_of_year": month,
            "day_of_week": day_of_week,
        }
    except Exception as e:
        logger.error(f"Error parsing cron string {cron_str}: {e}")
        raise
