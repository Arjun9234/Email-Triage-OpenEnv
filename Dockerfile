# Runtime-only build to reduce external image pulls and validator flakiness.
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY server/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

COPY server/ server/
COPY openenv.yaml ./openenv.yaml

RUN mkdir -p server/.runtime

# HF Spaces uses port 7860 for docker apps.
EXPOSE 7860

CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7860"]
