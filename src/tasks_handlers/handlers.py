from typing import Dict, List, Literal, Optional, Union

import torch
from bson import ObjectId
from loguru import logger
from pymongo.errors import BulkWriteError

from src.constants import MONGO_COLLECTION_CLIENTS, MONGO_COLLECTION_NEWS
from src.db import MongoDBInit
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


class MongoDBServices:
    def __init__(self, connection: Optional[MongoDBInit] = None):
        if connection:
            self.connection = connection
        else:
            self.connection = DependencyManager().mongodb_connection

    def get_all_clients(self) -> list:
        clients_collection = self.connection.get_collection(
            MONGO_COLLECTION_CLIENTS
        )
        return list(clients_collection.find())

    def get_specific_client_data(
        self, client_id: str, data: str
    ) -> Union[str, list]:
        client_data_collection = self.connection.get_collection(
            MONGO_COLLECTION_CLIENTS
        )
        client_data = client_data_collection.find_one(
            {"_id": ObjectId(client_id)}
        )
        return client_data[data] if client_data else None

    def check_or_add_news(self, client_id: str, articles: List[dict]) -> None:
        news_collection = self.connection.get_collection(MONGO_COLLECTION_NEWS)
        added_news_ids = []

        titles_sources = [
            {"title": article["title"], "source": article["source"]}
            for article in articles
        ]
        existing_articles = list(news_collection.find({"$or": titles_sources}))

        existing_articles_dict = {
            f"{article['title']}_{article['source']}": article
            for article in existing_articles
        }

        new_articles = []

        for article in articles:
            key = f"{article['title']}_{article['source']}"
            if key in existing_articles_dict:
                existing_article = existing_articles_dict[key]
                if client_id not in existing_article.get("clients", []):
                    news_collection.update_one(
                        {"_id": existing_article["_id"]},
                        {"$addToSet": {"clients": client_id}},
                    )
            else:
                article["clients"] = [client_id]
                new_articles.append(article)

        if new_articles:
            try:
                insert_result = news_collection.insert_many(new_articles)
                added_news_ids.extend(
                    [
                        str(inserted_id)
                        for inserted_id in insert_result.inserted_ids
                    ]
                )
            except BulkWriteError as bwe:
                logger.error(f"Bulk write error: {bwe.details}")

        return added_news_ids

    def get_clients_news(self, client_id: str) -> List[dict]:
        news_collection = self.connection.get_collection(MONGO_COLLECTION_NEWS)
        return list(news_collection.find({"clients": client_id}))


class ProcessedData:
    def __init__(self):
        ...

    def process_data(self):
        ...
