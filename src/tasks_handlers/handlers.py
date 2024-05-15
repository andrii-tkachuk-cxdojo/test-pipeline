from typing import List, Optional, Union

from bson import ObjectId
from pymongo.errors import BulkWriteError

from src.constants import MONGO_COLLECTION_CLIENTS, MONGO_COLLECTION_NEWS
from src.db import MongoDBInit
from src.tasks_handlers.dependencies import DependencyManager


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

    def get_clients_news(self, client_id: str) -> List[dict]:
        news_collection = self.connection.get_collection(MONGO_COLLECTION_NEWS)
        articles_cursor = news_collection.find(
            {"clients": client_id}, {"_id": 0, "clients": 0}
        )
        articles = [doc["article"] for doc in articles_cursor]
        return articles


class ComputeProcesData:
    def __init__(self):
        ...

    def process_data(self):
        ...
