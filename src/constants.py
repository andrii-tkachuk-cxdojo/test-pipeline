from typing import Final

from environs import Env

env = Env()
env.read_env()

CELERY_BACKEND_URL: Final = env.str("CELERY_BACKEND_URL")
CELERY_BROKER_URL: Final = env.str("CELERY_BROKER_URL")
NEWSCATCHER_API_KEY: Final = env.str("NEWSCATCHER_API_KEY")
SPACY_MODEL_CORE: Final = env.str("SPACY_MODEL_CORE")

MONGO_COLLECTION_CLIENTS: Final = env.str("MONGO_COLLECTION_CLIENTS")
MONGO_COLLECTION_NEWS: Final = env.str("MONGO_COLLECTION_NEWS")
MONGO_DB: Final = env.str("MONGO_DB")
MONGO_HOST: Final = env.str("MONGO_HOST")
MONGO_PORT: Final = env.str("MONGO_PORT")
MONGO_USER: Final = env.str("MONGO_USER")
MONGO_PASSWORD: Final = env.str("MONGO_PASSWORD")

AWS_ACCESS_KEY_ID: Final = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY: Final = env.str("AWS_SECRET_ACCESS_KEY")
AWS_REGION: Final = env.str("AWS_REGION")
