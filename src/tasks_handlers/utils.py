import base64
import json
from typing import Dict, List, Literal, Optional

import boto3
import torch
from loguru import logger

from src.tasks_handlers.dependencies import DependencyManager


class ClusterizationSentences:
    def __init__(self):
        self.spacy_core_nlp = DependencyManager().DependencyManager

    def get_clusters(self, article_text: str) -> Optional[List[str]]:
        doc = self.spacy_core_nlp(article_text)
        sents = [sent.text for sent in doc.sents]
        logger.info(f"Count sentences of text: {len(sents)}")
        return sents


class DefineSentiment:
    def __init__(self):
        self.model = DependencyManager().model
        self.tokenizer = DependencyManager().tokenizer

    def process_text(
        self, text: str
    ) -> Literal["positive", "negative", "neutral"]:
        inputs = self.tokenizer(text, return_tensors="pt")

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=-1)

        predicted_sentiment = self.model.config.id2label[
            probabilities.argmax().item()
        ]
        return predicted_sentiment


class HttpHook:
    URL: str = "https://v3-api.newscatcherapi.com/api/search"

    def __init__(self):
        self.newscatcher_client = DependencyManager().newscatcher_client

    def newscatcher_hook(self, params: dict) -> Dict:
        response = self.newscatcher_client.get(self.URL, params=params)
        return response.json()


class SecretsManager:
    @staticmethod
    def get_secret(client_id: str):
        client = boto3.client("secretsmanager")
        try:
            response = client.get_secret_value(SecretId=client_id)
            if "SecretString" in response:
                return json.loads(response["SecretString"])
            else:
                decoded_binary_secret = base64.b64decode(
                    response["SecretBinary"]
                )
                return json.loads(decoded_binary_secret)
        except Exception as e:
            logger.error(f"Error retrieving secret {client_id}: {str(e)}")
            return None
