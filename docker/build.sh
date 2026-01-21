# docker/build.sh

#!/bin/bash

SERVICE=$1
TAG=$2
docker build -t ${REGISTRY}/${SERVICE}:${TAG} -f ${SERVICE}/Dockerfile .
docker push ${REGISTRY}/${SERVICE}:${TAG}