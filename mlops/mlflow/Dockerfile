# mlops/mlflow/Dockerfile
FROM python:3.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    mlflow==2.11.3 \
    psycopg2-binary \
    gunicorn

EXPOSE 5000

CMD ["mlflow", "server", "--backend-store-uri", "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/mlflow", "--default-artifact-root", "/mlflow/artifacts", "--host", "0.0.0.0", "--port", "5000"]