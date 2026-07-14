# ==========================================================================
# PostgreSQL com init de role da aplicação (sem bind-mount frágil).
# ==========================================================================
FROM postgres:16-alpine

COPY init-app-role.sh /docker-entrypoint-initdb.d/00-init-app-role.sh
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/00-init-app-role.sh \
    && chmod +x /docker-entrypoint-initdb.d/00-init-app-role.sh
