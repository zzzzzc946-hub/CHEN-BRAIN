FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-server.txt /app/requirements-server.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements-server.txt

COPY content_link_collector.py /app/content_link_collector.py
COPY config.server.example.json /app/config.example.json

EXPOSE 8787

CMD ["python", "content_link_collector.py", "webhook-server", "--host", "0.0.0.0", "--port", "8787"]
