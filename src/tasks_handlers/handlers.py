from typing import Dict, List, Literal, Optional, Union

import torch
from httpx import Client
from loguru import logger

from src.constants import MONGO_COLLECTION_CLIENTS
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

    @property
    def newscatcher_client(self) -> Client:
        return DependencyManager().newscatcher_client

    def news_catcher_hook(self, client: dict) -> Dict:
        response = self.newscatcher_client.get(self.URL, params=client)
        return response.json()


class MongoDBServices:
    def __init__(self):
        self.connection = DependencyManager().mongodb_connection

    def get_all_clients(self) -> list:
        clients_collection = self.connection.get_collection(
            MONGO_COLLECTION_CLIENTS
        )
        return list(clients_collection.find())

    def get_specific_client_data(
        self, client: str, data: str
    ) -> Union[str, list]:
        client_data_collection = self.connection.get_collection(
            MONGO_COLLECTION_CLIENTS
        )
        client_data = client_data_collection.find_one({"client": client})
        return client_data[data] if client_data else None

    def check_or_add_news(self, client: str, news: list):
        ...

    def get_clients_news(self, client: str):
        ...


class ProcessedData:
    def __init__(self):
        ...

    def process_data(self):
        ...
