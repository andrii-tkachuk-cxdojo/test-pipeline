# test-pipeline
For start (by default in ```celery_conf.py``` defined run cron task at ```08:30 "Europe/Kiev"``` time zone.)
```shell
docker-compose up --build
```
```.env
CELERY_BACKEND_URL=redis://celery-redis:6379/10
CELERY_BROKER_URL=amqp://newscatcher:password@celery-rabbitmq:5672/

REDIS_PORT=6379

RABBITMQ_DEFAULT_USER=newscatcher
RABBITMQ_DEFAULT_PASS=password
RABBITMQ_PORT=5672
# RABBITMQ_PORT_WEB=15672

FLOWER_USER=newscatcher_admin
FLOWER_PASSWORD=Qt3FoG0xRKX08iTSEHlk1A6
FLOWER_PORT=6655

NEWSCATCHER_API_KEY=...
SPACY_MODEL_CORE=en_core_web_trf
```
## Simple logic scheme of test-pipeline
![scheme](images/sсheme.png)
