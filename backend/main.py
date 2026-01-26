# backend/main.py
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
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger.remove()
logger.add(
    sys.stdout, 
    format="{time} | {level} | {message}", 
    serialize=True
)

resource = Resource.create(attributes={
    "service.name": "hallucination-detector-backend",
    "deployment.environment": "production"
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger-collector.observability:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

app = FastAPI(title="Hallucination Detection API - Production Ready")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    current_span = trace.get_current_span()
    trace_id = format(current_span.get_span_context().trace_id, '032x')
    
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