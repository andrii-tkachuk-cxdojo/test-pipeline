from typing import Dict, List, Optional, Tuple, Union

from bson import ObjectId
from loguru import logger
from pymongo.errors import BulkWriteError

from src.constants import MONGO_COLLECTION_CLIENTS, MONGO_COLLECTION_NEWS
from src.db import MongoDBInit
from src.tasks_handlers import ClusterizationSentences, DefineSentiment
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


class NlpProcesData:
    def __init__(self, clients_news: List[dict], code_word: str):
        self.clients_news = clients_news
        self.code_word = code_word
        self.db_service = MongoDBServices()
        self.cluster_service = ClusterizationSentences()
        self.sentiment_service = DefineSentiment()

    def handle_articles(self) -> None:
        for article in self.clients_news:
            sentiments_list = self.process_article(
                article["content"], self.code_word
            )
            self.db_service.update_article_sentiment(
                article["_id"], sentiments_list
            )

    def process_article(self, article: str, code_word: str) -> List[Tuple]:
        sentiments_list = []
        sents = self.cluster_service.get_clusters(article_text=article)
        for sent in sents:
            if code_word.lower() in sent.lower():
                sentiment = self.sentiment_service.process_text(text=sent)
                sentiments_list.append((sent, sentiment))
            else:
                sentiments_list.append((sent,))
        return sentiments_list
