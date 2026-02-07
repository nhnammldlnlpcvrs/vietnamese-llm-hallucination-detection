# backend/main.py
import os
import time
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.predict import router as predict_router
from loguru import logger

# Monitoring and Tracing
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, StaticSampler

logger.remove()
logger.add(
    sys.stdout, 
    format="{time} | {level} | {extra[trace_id]} | {message}",
    serialize=True,
    level="INFO"
)

resource = Resource.create(attributes={
    "service.name": "hallucination-detector-backend",
    "deployment.environment": os.getenv("ENVIRONMENT", "production")
})

sampler = ALWAYS_OFF if os.getenv("DISABLE_MODEL") == "true" else ALWAYS_ON

provider = TracerProvider(
    resource=resource,
    sampler=sampler
)



if os.getenv("DISABLE_MODEL") == "true":
    processor = BatchSpanProcessor(ConsoleSpanExporter()) 
else:
    jaeger_url = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger-collector.observability:4317")
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=jaeger_url, insecure=True))

provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI(title="Hallucination Detection API - Production Ready")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()
    trace_id = (
        format(span_context.trace_id, "032x")
        if span_context and span_context.is_valid
        else None
    )
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    
    logger.bind(trace_id=trace_id).info(
        f"Path: {request.url.path} Method: {request.method} Status: {response.status_code} Latency: {process_time:.2f}ms"
    )
    return response

Instrumentator().instrument(app).expose(app)

FastAPIInstrumentor.instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router, prefix="/api", tags=["Hallucination"])