from typing import Dict, List, Literal, Optional

import torch
from httpx import Client
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

    @property
    def newscatcher_client(self) -> Client:
        return DependencyManager().newscatcher_client

    def news_catcher_hook(self, client: dict) -> Dict:
        response = self.newscatcher_client.get(self.URL, params=client)
        return response.json()


class ProcessedData:
    def __init__(self):
        ...

    def process_data(self):
        ...
