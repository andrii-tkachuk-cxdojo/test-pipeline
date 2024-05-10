from typing import Final

from environs import Env

env = Env()
env.read_env()

CELERY_BACKEND_URL: Final = env.str("CELERY_BACKEND_URL")
CELERY_BROKER_URL: Final = env.str("CELERY_BROKER_URL")
NEWSCATCHER_API_KEY: Final = env.str("NEWSCATCHER_API_KEY")
SPACY_MODEL_CORE: Final = env.str("SPACY_MODEL_CORE")
