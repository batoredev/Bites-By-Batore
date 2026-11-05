FROM node:24-bookworm-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN uv sync --project backend --frozen --no-dev
COPY backend/app /app/backend/app
COPY resources /app/resources
COPY --from=web /web/dist /app/web/dist
RUN useradd --create-home batore && mkdir -p /app/data && chown -R batore:batore /app
USER batore
WORKDIR /app/backend
EXPOSE 8000
CMD ["/app/backend/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
