# test-pipeline
For start (by default celery beat initially setup all users from ```client.json``` to MongoDB and will run the cron tasks at ```"Europe/Kiev"``` time zone (defined in ```celery_conf.py```) in the defined client`s time.)
- For prod env, you should rechange ```.env.client*``` files for the Security Vault tool, for instance, AWS Vault and other similar.
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

RABBITMQ_DEFAULT_USER=newscatcher
RABBITMQ_DEFAULT_PASS=...
RABBITMQ_PORT=5672
# RABBITMQ_PORT_WEB=15672

FLOWER_USER=newscatcher_admin
FLOWER_PASSWORD=...
FLOWER_PORT=6655

NEWSCATCHER_API_KEY=...
SPACY_MODEL_CORE=en_core_web_trf
```
## Simple logic scheme of test-pipeline
![scheme](images/scheme.png)
