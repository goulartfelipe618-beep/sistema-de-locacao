# ==========================================================================
# ERP Locadora — Imagem de produção (FastAPI + Celery)
# Build na VPS: docker compose build / docker compose up -d --build
# ==========================================================================
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=America/Sao_Paulo \
    PATH="/home/appuser/.local/bin:${PATH}"

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && sed -i 's/\r$//' /code/docker/entrypoint.sh \
    && find /code/scripts -type f -name '*.sh' -exec sed -i 's/\r$//' {} \; \
    && chmod +x /code/docker/entrypoint.sh \
    && find /code/scripts -type f -name '*.sh' -exec chmod +x {} \; \
    && chown -R appuser:appuser /code

USER appuser

EXPOSE 8000

ENTRYPOINT ["/code/docker/entrypoint.sh"]
CMD ["web"]
