# SYNTHETIC fixture
FROM python:3.12-slim
RUN apt-get update && apt-get install -y openssl
# RUN openssl genrsa 1024   HN commented out
RUN openssl req -x509 -newkey rsa:2048 -sha1 -nodes \
    -keyout /tmp/ledger.key -out /tmp/ledger.crt -subj "/CN=ledger.test" -days 1
RUN echo "openssl genrsa 2048 is old" && openssl version
COPY . /app
