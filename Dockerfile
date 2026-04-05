# Multi-stage build: Next.js frontend + Python backend
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY package*.json ./
RUN npm ci

COPY app app/
COPY lib lib/
COPY components components/
COPY hooks hooks/
COPY public public/
COPY tsconfig.json next.config.mjs postcss.config.mjs components.json ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim

WORKDIR /app

# Install minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy Python backend
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server server/

# Copy built frontend from builder
COPY --from=frontend-builder /build/.next .next
COPY --from=frontend-builder /build/public public

# Create runtime dir
RUN mkdir -p server/.runtime

ENV PYTHONUNBUFFERED=1

# HF Spaces uses port 7860!
EXPOSE 7860

CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7860"]
