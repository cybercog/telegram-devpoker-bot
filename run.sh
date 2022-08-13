#!/bin/bash -ex

NAME=devpoker-bot
DB_LOCATION=/db
DB_NAME=devpoker_bot.db

docker build -t ${NAME} .
docker rm -f ${NAME} || true
docker run --name ${NAME} -d --restart=unless-stopped -e DEVPOKER_BOT_API_TOKEN=${DEVPOKER_BOT_API_TOKEN} -e DEVPOKER_BOT_DB_PATH=${DB_LOCATION}/${DB_NAME} -v ~/.devpoker_bot/:${DB_LOCATION} ${NAME}
docker logs -f ${NAME}
