import os

from celery import chain, signals
from celery.signals import task_failure
from loguru import logger

# from celery.signals import task_success
from src.celery_conf import celery_app
from src.dependencies import DependencyManager
from src.tasks_handlers import NlpProcesData, SendingStrategyFactory
from src.utils import HttpHook, MongoDBServices

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

    if os.getenv("WORKER") == "cpu":
        _ = manager.spacy_core_nlp
        _ = manager.model
        _ = manager.tokenizer

    if os.getenv("WORKER") == "sending":
        _ = manager.boto3_secret_manager


@celery_app.task(name="clients_pipeline.tasks.run_task_chain")
def run_task_chain(**kwargs) -> None:
    task_chain = chain(
        task_newscatcher_hook.si(client_id=kwargs["client_id"])
        | task_ml_process_news_data.si(client_id=kwargs["client_id"])
        | task_send_data.si(client_id=kwargs["client_id"])
    )
    task_chain.apply_async()


@celery_app.task(
    name="newscatcher_hook",
    bind=True,
    retry_backoff=True,
    max_retries=3,
    retry_backoff_max=60,
)
def task_newscatcher_hook(self, **kwargs) -> None:
    newscatcher_params = MongoDBServices().get_specific_client_data(
        client_id=kwargs["client_id"], data="newscatcher_params"
    )
    newscatcher_data = HttpHook().newscatcher_hook(params=newscatcher_params)
    if newscatcher_data["articles"]:
        logger.info(
            f"Found '{len(newscatcher_data['articles'])}' actual news for client '{kwargs['client_id']}' in NewsCatcher"
        )
        logger.info("Checking news for exist in previous clients...")
        MongoDBServices().check_or_add_news(
            client_id=kwargs["client_id"], news=newscatcher_data["articles"]
        )
    else:
        logger.warning(
            "Unfortunately, the actual data in NewsCatcher not found."
        )


@celery_app.task(
    name="ml_process_news_data",
    bind=True,
    retry_backoff=True,
    max_retries=5,
    retry_backoff_max=120,
)
def task_ml_process_news_data(self, **kwargs) -> None:
    client_data = MongoDBServices().get_specific_client_data(
        client_id=kwargs["client_id"]
    )
    logger.info(
        f"Checked NLP requirement for client_id '{kwargs['client_id']}'"
    )

    if client_data["nlp"]:
        clients_news = MongoDBServices().get_clients_news(
            client_id=kwargs["client_id"], nlp=client_data["nlp"]
        )
        if clients_news:
            NlpProcesData(
                clients_news=clients_news,
                code_word=client_data["newscatcher_params"]["q"],
            ).handle_articles()
            logger.info(
                f"Processed with NLP for client '{kwargs['client_id']}' success."
            )
        else:
            logger.warning("Unfortunately, the actual data for NLP not found.")
    else:
        logger.info(f"Client '{kwargs['client_id']}' not needed NLP.")


@celery_app.task(
    name="send_data",
    bind=True,
    retry_backoff=True,
    max_retries=3,
    retry_backoff_max=60,
)
def task_send_data(self, **kwargs) -> None:
    client_data = MongoDBServices().get_specific_client_data(
        client_id=kwargs["client_id"]
    )
    strategy = SendingStrategyFactory().get_strategy(
        sending_mode=client_data["send_to"], client_id=kwargs["client_id"]
    )

    clients_news = MongoDBServices().get_clients_news(
        client_id=kwargs["client_id"],
        nlp=client_data["nlp"],
        exclude_object_id=True,
    )
    if clients_news:
        strategy.send(clients_news)
    else:
        strategy.send("Unfortunately, the actual data for you not found.")
    logger.info(
        f"Data for client_id '{kwargs['client_id']}' sent and pipeline is finished"
    )


# @task_success.connect(sender=task_quality_check)
# def task_success_handler(sender, result, **kwargs) -> None:
#     logger.info("Signal calls, that mean quality_check is SUCCESS")


@task_failure.connect(sender=run_task_chain)
@task_failure.connect(sender=task_newscatcher_hook)
@task_failure.connect(sender=task_ml_process_news_data)
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
