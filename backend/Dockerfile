FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ cmake git \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-cpu.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-cpu.txt

FROM python:3.12-slim-bookworm

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential g++ cmake git \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app ./app

RUN mkdir -p /app/models /app/data

LABEL org.opencontainers.image.title="AI-F Backend CPU" \
    org.opencontainers.image.version="1.0"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/healthz/ || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
