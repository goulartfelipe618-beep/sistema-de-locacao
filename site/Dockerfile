# Site institucional white-label (nginx + BFF) — um serviço Easypanel / Compose
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY bff/requirements.txt ./bff/
RUN pip install --no-cache-dir -r bff/requirements.txt

COPY bff/ ./bff/
COPY public/ /usr/share/nginx/html/
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1/bff/health || exit 1

CMD ["/entrypoint.sh"]
