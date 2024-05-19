from celery.schedules import crontab
from loguru import logger

from src.celery_conf import AppCeleryConfig, celery_app
from src.db import MongoDBInit
from src.utils import MongoDBServices


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender: AppCeleryConfig, **kwargs) -> None:
    logger.info("Connecting to the database from beat...")

    with MongoDBInit() as connection:
        try:
            connection.connect()
            connection.load_data_from_json("clients.json")
        except Exception:
            logger.warning("Client`s data already exist.")

        schedule_data = MongoDBServices(
            connection=connection
        ).get_all_clients()

    for client in schedule_data:
        update_schedule_from_db(sender, client)
        logger.info(
            f"Schedule for client_id '{client['_id']}' updated success."
        )


def update_schedule_from_db(
    sender: AppCeleryConfig, client_data: dict
) -> None:
    schedule = sender.conf.beat_schedule.copy()

    task_name = f"task_for_{client_data['_id']}"
    cron_args = parse_cron_string(client_data["cron"])
    schedule[task_name] = {
        "task": "clients_pipeline.tasks.run_task_chain",
        "schedule": crontab(**cron_args),
        "kwargs": {"client_id": str(client_data["_id"])},
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
