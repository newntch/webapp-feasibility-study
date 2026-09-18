FROM ghcr.io/astral-sh/uv:0.12.9 AS uv

FROM python:3.12-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY manage.py ./
COPY src ./src
COPY public ./public
RUN DJANGO_SECRET_KEY=build-only /app/.venv/bin/python manage.py collectstatic --noinput

FROM python:3.12-slim
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/manage.py ./
COPY --from=build /app/src ./src
COPY --from=build /app/public ./public
COPY --from=build /app/staticfiles ./staticfiles
COPY docker-entrypoint.sh ./docker-entrypoint.sh
USER app
EXPOSE 4173
ENTRYPOINT ["/bin/sh", "/app/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/gunicorn", "config.wsgi:application", "--pythonpath", "src", "--bind", "0.0.0.0:4173", "--workers", "2"]
