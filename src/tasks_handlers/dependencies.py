import json

import httpx
import spacy
from httpx import Client
from loguru import logger
from singleton_decorator import singleton
from spacy import Language
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.constants import NEWSCATCHER_API_KEY, SPACY_MODEL_CORE


@singleton
class DependencyManager:
    """
    Define class with all dependencies.
    """

    sentimental_model: str = "ProsusAI/finbert"

    def __init__(self):
        self._clients = None
        self._newscatcher_client = None

        self._model = None
        self._tokenizer = None
        self._spacy_core_nlp = None

    @property
    def clients(self) -> dict:
        if self._clients is None:
            with open("clients.json", "r") as file:
                self._clients = json.load(file)
                logger.info("Client`s requirements initialized success.")
        return self._clients

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
                self.sentimental_model
            )
            logger.info(
                f"Tokenizer '{self.sentimental_model}' initialized success."
            )
        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.sentimental_model
            )
            logger.info(
                f"Model '{self.sentimental_model}' initialized success."
            )
        return self._tokenizer

    @property
    def spacy_core_nlp(self) -> Language:
        if self._spacy_core_nlp is None:
            self._spacy_core_nlp = spacy.load(SPACY_MODEL_CORE)
            logger.info(
                f"SPACY_MODEL_CORE model: {SPACY_MODEL_CORE} is loaded."
            )
        return self._spacy_core_nlp
