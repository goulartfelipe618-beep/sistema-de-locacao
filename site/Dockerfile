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
RUN rm -f /etc/nginx/sites-enabled/default \
    && sed -i 's/\r$//' /entrypoint.sh \
    && chmod +x /entrypoint.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://127.0.0.1/ >/dev/null && curl -fsS http://127.0.0.1/bff/health >/dev/null || exit 1

CMD ["/entrypoint.sh"]
