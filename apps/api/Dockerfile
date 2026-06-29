FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.11.20

COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/migrations ./migrations
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "fastapi", "run", "src/veriflow_api/main.py", "--host", "0.0.0.0", "--port", "8000"]
