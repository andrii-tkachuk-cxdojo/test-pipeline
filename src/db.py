import json

from loguru import logger
from pymongo import ASCENDING, MongoClient

from src.constants import (
    MONGO_COLLECTION_CLIENTS,
    MONGO_COLLECTION_NEWS,
    MONGO_DB,
    MONGO_HOST,
    MONGO_PASSWORD,
    MONGO_PORT,
    MONGO_USER,
)


class MongoDBInit:
    def __init__(self):
        self._mongo_client = None
        self._db = None

    def connect(self) -> MongoClient:
        if not self._mongo_client:
            MONGODB_URL = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"
            self._mongo_client = MongoClient(MONGODB_URL)
            self._db = self._mongo_client[MONGO_DB]
            self.setup_indexes()
            logger.info("MongoDB connection initialized successfully.")
        return self._mongo_client

    def setup_indexes(self):
        clients_collection = self._db[MONGO_COLLECTION_CLIENTS]
        clients_collection.create_index([("client", ASCENDING)], unique=True)

        news_collection = self._db[MONGO_COLLECTION_NEWS]
        news_collection.create_index([("source", ASCENDING)], unique=False)

    def get_collection(self, collection_name):
        return self._db[collection_name]

    def load_data_from_json(self, json_file_path):
        collection = self.get_collection(MONGO_COLLECTION_CLIENTS)
        with open(json_file_path, "r") as file:
            data = json.load(file)
            if isinstance(data, list):
                collection.insert_many(data)
            else:
                collection.insert_one(data)
            logger.info(
                f"Data from {json_file_path} loaded into collection {MONGO_COLLECTION_CLIENTS}"
            )

    def close_connection(self):
        if self._mongo_client:
            self._mongo_client.close()
            logger.info("MongoDB connection closed.")
