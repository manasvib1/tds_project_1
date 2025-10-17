# Dockerfile — build image for Hugging Face Space (Docker runtime)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install system deps (git + GitHub CLI + curl)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git curl gnupg ca-certificates build-essential procps && \
    # Install GH CLI (needed by gh_api.py)
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && \
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list && \
    apt-get update && apt-get install -y --no-install-recommends gh && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements & install (we reference api/requirements.txt)
COPY api/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copy app code
COPY api /app/api
COPY .env.example /app/.env.example

# Make sure uvicorn runs on HF port 7860
EXPOSE 7860

# small startup script to print debug info then run uvicorn
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
