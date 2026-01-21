# mlflow/Dockerfile
FROM python:3.9-slim-bookworm
RUN pip install mlflow boto3 psycopg2-binary
EXPOSE 5000
CMD ["mlflow", "server", \
     "--backend-store-uri", "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:5432/mlflow", \
     "--default-artifact-root", "s3://${S3_BUCKET}/mlflow-artifacts", \
     "--host", "0.0.0.0"]