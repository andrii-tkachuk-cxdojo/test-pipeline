from typing import Dict

from celery import chain, signals
from celery.signals import task_failure
from loguru import logger

# from celery.signals import task_success
from src.celery_conf import celery_app
from src.tasks_handlers import DefineSentiment, DependencyManager, HttpHook

logger.add(
    "logging/pipeline.log",
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
    _ = manager.spacy_core_nlp


@celery_app.task(name="clients_pipeline.tasks.run_task_chain")
def run_task_chain() -> None:
    for client in DependencyManager().clients:
        task_chain = chain(
            task_newscatcher_hook.s(client=client)
            | task_process_news_data.s()
            | task_make_decision.s()
        )
        task_chain.apply_async()


@celery_app.task(
    name="newscatcher_hook",
    bind=True,
    retry_backoff=True,
    max_retries=3,
    retry_backoff_max=60,
)
def task_newscatcher_hook(self, **kwargs) -> Dict:
    logger.info("HTTP hook to newscatcher in process...")
    newscatcher_data = HttpHook().news_catcher_hook(
        params=kwargs["client"]["newscatcher_params"]
    )
    if newscatcher_data["articles"]:
        logger.info(
            f"Found {len(newscatcher_data['articles'])} actual data in NewsCatcher"
        )
    else:
        logger.warning(
            "Unfortunately, the actual data in NewsCatcher not found."
        )
    return {
        "client": kwargs["client"],
        "newscatcher_data": newscatcher_data["articles"],
    }


@celery_app.task(
    name="process_news_data",
    bind=True,
    retry_backoff=True,
    max_retries=5,
    retry_backoff_max=120,
)
def task_process_news_data(self, data: Dict) -> Dict:
    logger.info(
        f"Processing data from NewsCatcher for client: {data['client']['client']}"
    )
    if data["client"]["nlp"] and data["newscatcher_data"]["articles"]:
        for article in data["newscatcher_data"]["articles"]:
            sentimental = DefineSentiment().process_text(article["content"])
            article.update({"sentimental": sentimental})
    return data


@celery_app.task(name="make_decision")
def task_make_decision(data: Dict) -> None:
    logger.info(
        f"Start send data for '{data['client']['client']}' to '{data['client']['send_to']}'"
    )
    ...


# @task_success.connect(sender=task_quality_check)
# def task_success_handler(sender, result, **kwargs) -> None:
#     logger.info("Signal calls, that mean quality_check is SUCCESS")


@task_failure.connect(sender=run_task_chain)
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
