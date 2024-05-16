import json
import time
from abc import ABC, abstractmethod

import boto3
from google.cloud import pubsub_v1
from loguru import logger

from src.utils import SecretsManager


class SendingStrategy(ABC):
    def __init__(self, client_id: str):
        self.credentials = None
        self.client_id = client_id

    def load_env(self):
        self.credentials = SecretsManager().get_secret(self.client_id)

    @abstractmethod
    def send(self, data):
        pass


class SQSSendStrategy(SendingStrategy):
    def send(self, data):
        sqs = boto3.client(
            "sqs",
            aws_access_key_id=self.credentials["access_key_id"],
            aws_secret_access_key=self.credentials["secret_access_key"],
            region_name=self.credentials["region"],
        )
        response = sqs.send_message(
            QueueUrl=self.credentials["queue_url"],
            MessageBody=json.dumps(data),
        )
        logger.info(f"Message sent to SQS: {response}")


class S3SendStrategy(SendingStrategy):
    def send(self, data):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=self.credentials["access_key_id"],
            aws_secret_access_key=self.credentials["secret_access_key"],
            region_name=self.credentials["region"],
        )
        response = s3.put_object(
            Bucket=self.credentials["bucket_name"],
            Key=f"data_{int(time.time())}.json",
            Body=json.dumps(data),
        )
        logger.info(f"Data uploaded to S3: {response}")


class GooglePubSubSendStrategy(SendingStrategy):
    def send(self, data):
        publisher = pubsub_v1.PublisherClient.from_service_account_json(
            self.credentials["service_account_json"]
        )
        topic_path = publisher.topic_path(
            self.credentials["project_id"], self.credentials["topic_id"]
        )
        data = json.dumps(data).encode("utf-8")
        response = publisher.publish(topic_path, data)
        logger.info(f"Message sent to Google Pub/Sub: {response.result()}")


class SendingStrategyFactory:
    @staticmethod
    def get_strategy(
        client_id: str,
        sending_mode: str = "auto",
    ) -> SendingStrategy:
        strategies = {
            "sqs": SQSSendStrategy,
            "s3": S3SendStrategy,
            "pub/sub": GooglePubSubSendStrategy,
        }
        strategy_class = strategies.get(sending_mode)
        if not strategy_class:
            raise ValueError(f"Unknown sort mode: {sending_mode}")
        return strategy_class(client_id=client_id)
