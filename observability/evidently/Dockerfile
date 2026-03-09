FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    "numpy<2.0" \
    "evidently==0.4.33" \
    "fastapi==0.109.0" \
    "uvicorn==0.27.0" \
    "prometheus-client==0.19.0" \
    "pandas==2.1.4"

COPY drift_service.py .

EXPOSE 8001

CMD ["python", "drift_service.py"]