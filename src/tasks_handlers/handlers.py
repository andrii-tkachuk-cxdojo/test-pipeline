from typing import List, Tuple

from src.utils import ClusterizationSentences, DefineSentiment, MongoDBServices


class NlpProcesData:
    def __init__(self, clients_news: List[dict], code_word: str):
        self.clients_news = clients_news
        self.code_word = code_word
        self.db_service = MongoDBServices()
        self.cluster_service = ClusterizationSentences()
        self.sentiment_service = DefineSentiment()

    def handle_articles(self) -> None:
        for article in self.clients_news:
            if "sentiment" in article:
                continue

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
        return sentiments_list
