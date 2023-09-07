FROM python:3.9-slim

WORKDIR /app
COPY . /app

ENV GRID_CAPACITY_PANDAPOWER_BACKEND=1
RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    pip install .[ppfull]
RUN pip cache purge && rm -rf /app/*
