import boto3
import httpx
import spacy
from httpx import Client
from loguru import logger
from singleton_decorator import singleton
from spacy import Language
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.constants import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    NEWSCATCHER_API_KEY,
    SPACY_MODEL_CORE,
)
from src.db import MongoDBInit


@singleton
class DependencyManager:
    """
    Define class with all dependencies.
    """

    sentimental_model: str = "ProsusAI/finbert"

    def __init__(self):
        self._newscatcher_client = None

        self._model = None
        self._tokenizer = None
        self._spacy_core_nlp = None

        self._mongodb_connection = None
        self._boto3_secret_manager = None

    @property
    def boto3_secret_manager(self) -> boto3:
        if self._boto3_secret_manager is None:
            self._boto3_secret_manager = boto3.client(
                "secretsmanager",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION,
            )
            logger.info("AWS SecretManager boto3 client initialized success.")
        return self._boto3_secret_manager

    @property
    def mongodb_connection(self) -> MongoDBInit:
        if self._mongodb_connection is None:
            connection = MongoDBInit()
            connection.connect()
            self._mongodb_connection = connection
        return self._mongodb_connection

    @property
    def newscatcher_client(self) -> Client:
        if self._newscatcher_client is None:
            self._newscatcher_client = httpx.Client(
                headers={"x-api-token": NEWSCATCHER_API_KEY}
            )
            logger.info("NewsCatcher Client initialized success.")
        return self._newscatcher_client

    @property
    def model(self) -> AutoModelForSequenceClassification:
        if self._model is None:
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.sentimental_model, force_download=True
            )
            logger.info(
                f"Model '{self.sentimental_model}' initialized success."
            )
        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.sentimental_model, force_download=True
            )
            logger.info(
                f"Tokenizer '{self.sentimental_model}' initialized success."
            )
        return self._tokenizer

    @property
    def spacy_core_nlp(self) -> Language:
        if self._spacy_core_nlp is None:
            self._spacy_core_nlp = spacy.load(SPACY_MODEL_CORE)
            logger.info(
                f"Spacy model '{SPACY_MODEL_CORE}' initialized success."
            )
        return self._spacy_core_nlp

    def __del__(self):
        if self._mongodb_connection:
            self._mongodb_connection.close()
