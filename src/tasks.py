import os
from typing import Dict

from celery import chain, signals
from celery.signals import task_failure
from loguru import logger

# from celery.signals import task_success
from src.celery_conf import celery_app
from src.tasks_handlers import (
    DefineSentiment,
    DependencyManager,
    HttpHook,
    MongoDBServices,
)

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
    _ = manager.mongodb_connection

    if os.getenv("WORKER") == "io":
        _ = manager.newscatcher_client

    # if os.getenv("WORKER") == "cpu":
    #     _ = manager.spacy_core_nlp
    #     _ = manager.model
    #     _ = manager.tokenizer

    if os.getenv("WORKER") == "sending":
        ...
        # _ = manager.boto3_client
        # _ = manager.google_client


@celery_app.task(name="clients_pipeline.tasks.run_task_chain")
def run_task_chain(**kwargs) -> None:
    task_chain = chain(
        task_newscatcher_hook.s(client=kwargs["client_id"])
        | task_specific_process_news_data.s()
        | task_send_data.s()
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
    newscatcher_params = MongoDBServices().get_specific_client_data(
        client_id=kwargs["client_id"], data="newscatcher_params"
    )
    newscatcher_data = HttpHook().newscatcher_hook(params=newscatcher_params)
    if newscatcher_data["articles"]:
        logger.info(
            f"Found {len(newscatcher_data['articles'])} actual news for client '{kwargs['client_id']}' in NewsCatcher"
        )
        logger.info("Checking news for exist in previous clients...")
        MongoDBServices().check_or_add_news(
            client_id=kwargs["client_id"], news=newscatcher_data["articles"]
        )
    else:
        logger.warning(
            "Unfortunately, the actual data in NewsCatcher not found."
        )
    return {
        "client": kwargs["client_id"],
    }


@celery_app.task(
    name="specific_process_news_data",
    bind=True,
    retry_backoff=True,
    max_retries=5,
    retry_backoff_max=120,
)
def task_specific_process_news_data(self, data: Dict) -> Dict:
    logger.info(f"Processing client`s data for client: {data['client']}")

    clients_news = MongoDBServices().get_clients_news(client=data["client"])

    if data["client"]["nlp"]:
        for article in clients_news:
            sentimental = DefineSentiment().process_text(article["content"])
            article.update({"sentimental": sentimental})
        logger.info("Processed with NLP success.")
    return data


@celery_app.task(name="send_data")
def task_send_data(data: Dict) -> None:
    logger.info(
        f"Start send data for '{data['client']['client']}' to '{data['client']['send_to']}'"
    )
    ...


# @task_success.connect(sender=task_quality_check)
# def task_success_handler(sender, result, **kwargs) -> None:
#     logger.info("Signal calls, that mean quality_check is SUCCESS")


@task_failure.connect(sender=run_task_chain)
@task_failure.connect(sender=task_newscatcher_hook)
@task_failure.connect(sender=task_specific_process_news_data)
@task_failure.connect(sender=task_send_data)
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
