from typing import Dict

from celery import chain, signals
from celery.signals import task_failure
from loguru import logger

# from celery.signals import task_success
from src.celery_conf import celery_app
from src.tasks_handlers import DefineSentimental, DependencyManager

logger.add(
    "../logging/pipeline.log",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
    level="DEBUG",
    enqueue=True,
    serialize=False,
)


@signals.worker_process_init.connect
def setup_model(signal, sender, **kwargs):
    manager = DependencyManager()
    _ = manager.model
    _ = manager.tokenizer
    _ = manager.newscatcher_client
    _ = manager.clients


@celery_app.task(name="clients_pipeline.tasks.run_task_chain")
def run_task_chain() -> None:
    for client in DependencyManager().clients:
        task_chain = chain(
            task_newscatcher_hook.s(client=client)
            | task_process_news_data.s()
            | task_make_decision.s()
        )
        task_chain.apply_async()


@celery_app.task(name="newscatcher_hook")
def task_newscatcher_hook(**kwargs) -> Dict:
    logger.info("HTTP hook to newscatcher in process...")
    # data = HttpHook().news_catcher_hook(client=kwargs['client'])
    logger.info("Got data from newscatcher.")
    return {"client": kwargs["client"], "data": "Hi, man! You are stupid!"}


@celery_app.task(name="process_news_data")
def task_process_news_data(data: Dict) -> Dict:
    logger.info(
        f"Processing data from NewsCatcher for client: {data['client']['client']}"
    )
    if data["client"]["nlp"]:
        sentimental = DefineSentimental().process_text(data["data"])
        data.update({"sentimental": sentimental})

    return data


@celery_app.task(name="make_decision")
def task_make_decision(data: Dict) -> None:
    logger.info(
        f"Start send data for '{data['client']['client']}' to '{data['client']['to']}'"
    )
    ...


# @task_success.connect(sender=task_quality_check)
# def task_success_handler(sender, result, **kwargs) -> None:
#     logger.info("Signal calls, that mean quality_check is SUCCESS")


@task_failure.connect(sender=task_newscatcher_hook)
@task_failure.connect(sender=task_process_news_data)
@task_failure.connect(sender=task_make_decision)
def task_failure_handler(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    **other_kwargs,
):
    error_data = {
        "task_name": sender.name,
        "task_id": task_id,
        "exception": str(exception),
        "args": args,
        "kwargs": kwargs,
        "traceback": str(traceback),
    }
    logger.error(f"Task {sender.name} with ID {task_id} failed:\n{error_data}")
