FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    libyaml-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create fedadmin user and group with UID/GID 5000
RUN groupadd -g 5000 fedadmin && useradd -u 5000 -g fedadmin -m -s /bin/bash fedadmin

# Create log directory for fedadmin user
RUN mkdir -p /var/log/fedadmin && chown fedadmin:fedadmin /var/log/fedadmin

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY .env.dev.example .env

# Change ownership of /app directory to fedadmin user
RUN chown -R fedadmin:fedadmin /app

EXPOSE 5000

# Fix ownership at startup (volume mount may override) and run as fedadmin
CMD ["sh", "-c", "chown -R fedadmin:fedadmin /app && su - fedadmin -s /bin/bash -c 'cd /app && flask run --host=0.0.0.0'"]
