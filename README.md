# test-pipeline
For start (by default celery beat initially setup all users from ```client.json``` to MongoDB and will run the cron tasks at ```"Europe/Kiev"``` time zone (defined in ```celery_conf.py```) in the defined client`s time.)
```shell
docker-compose up --build
```
```.env
CELERY_BACKEND_URL=mongodb://username:password@celery-mongodb:27017/
CELERY_BROKER_URL=amqp://newscatcher:R6881t0q@celery-rabbitmq:5672/

MONGO_USER=username
MONGO_PASSWORD=password
MONGO_PORT=27017
MONGO_HOST=celery-mongodb
MONGO_DB=etl-db
MONGO_COLLECTION_NEWS=news
MONGO_COLLECTION_CLIENTS=clients

# Flower for monitorin tasks
FLOWER_USER=newscatcher_admin
FLOWER_PASSWORD=...
FLOWER_PORT=6655

NEWSCATCHER_API_KEY=...

# Model to divide text into sentences 
SPACY_MODEL_CORE=en_core_web_trf

# For AWS SecretManager
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
```
## Simple logic scheme of test-pipeline
![scheme](images/scheme.png)
