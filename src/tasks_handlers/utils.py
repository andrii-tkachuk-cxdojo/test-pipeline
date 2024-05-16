import base64
import json
from typing import Dict, List, Literal, Optional, Union

import boto3
import torch
from bson import ObjectId
from loguru import logger
from pymongo.errors import BulkWriteError

from src.constants import MONGO_COLLECTION_CLIENTS, MONGO_COLLECTION_NEWS
from src.db import MongoDBInit
from src.dependencies import DependencyManager


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
        self, client_id: str, data: str = None
    ) -> Union[str, list]:
        client_data_collection = self.connection.get_collection(
            MONGO_COLLECTION_CLIENTS
        )
        client_data = client_data_collection.find_one(
            {"_id": ObjectId(client_id)}
        )
        return client_data[data] if data else client_data

    def check_or_add_news(self, client_id: str, news: List[dict]) -> None:
        news_collection = self.connection.get_collection(MONGO_COLLECTION_NEWS)

        titles_links = [
            {
                "article.title": article["title"],
                "article.link": article["link"],
            }
            for article in news
        ]
        existing_articles = list(news_collection.find({"$or": titles_links}))

        existing_articles_dict = {
            f"{article['article']['title']}_{article['article']['link']}": article
            for article in existing_articles
        }

        new_articles = []

        for article in news:
            key = f"{article['title']}_{article['link']}"
            if key in existing_articles_dict:
                existing_article = existing_articles_dict[key]
                if client_id not in existing_article.get("clients", []):
                    news_collection.update_one(
                        {"_id": existing_article["_id"]},
                        {"$addToSet": {"clients": client_id}},
                    )
            else:
                new_article = {"article": article, "clients": [client_id]}
                new_articles.append(new_article)

        if new_articles:
            try:
                news_collection.insert_many(new_articles)
            except BulkWriteError as bwe:
                print(f"Bulk write error: {bwe.details}")

    def get_clients_news(
        self, client_id: str, nlp: bool = False
    ) -> List[Dict]:
        news_collection = self.connection.get_collection(MONGO_COLLECTION_NEWS)
        projection = {"_id": 0, "clients": 0}
        if not nlp:
            projection["sentiment"] = 0

        articles_cursor = news_collection.find(
            {"clients": client_id}, {"_id": 0, "clients": 0}, projection
        )
        articles = [doc["article"] for doc in articles_cursor]
        return articles

    def update_article_sentiment(
        self, article_id: ObjectId, sentiment: List
    ) -> None:
        news_collection = self.connection.get_collection(MONGO_COLLECTION_NEWS)
        update_result = news_collection.update_one(
            {"_id": article_id}, {"$set": {"sentiment": sentiment}}
        )

        if update_result.modified_count:
            logger.info(
                f"Updated article {article_id} with sentiment: {sentiment}"
            )
        else:
            logger.warning(f"No updates made for article {article_id}")


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
