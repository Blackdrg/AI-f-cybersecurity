FROM python:3.14.0-slim-bullseye

WORKDIR /app

# Ensure non-interactive install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies with version locking
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx=20.3.5-1 \
    libglib2.0-0=2.66.8-1 \
    libsm6=1.2.3-1 \
    libxext6=1.3.4-1 \
    libxrender-dev=0.9.10-1 \
    libgomp1=10.2.1-6 \
    && rm -rf /var/lib/apt/lists/*

# Strict dependency install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==23.3.1 && \
    pip install --no-cache-dir -r requirements.txt

# Copy app directory
COPY app ./app

# Create necessary directories
RUN mkdir -p /app/models /app/data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]