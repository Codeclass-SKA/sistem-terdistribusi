FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install necessary packages for terminal interaction (readline and potentially python-dev)
RUN apt-get update && apt-get install -y --no-install-recommends readline-common libreadline-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . .
