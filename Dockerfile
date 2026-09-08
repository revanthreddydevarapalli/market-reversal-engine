FROM python:3.12-slim

WORKDIR /app

# System deps needed for psycopg2 build (binary wheel normally suffices,
# but keep libpq for portability across architectures)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
