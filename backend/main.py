import logging
import time
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.predict import router as predict_router

# Monitoring and Tracing
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.resources import RESOURCE_ATTRIBUTES, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "message":"%(message)s", "trace_id":"%(otelTraceID)s"}',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
from loguru import logger
import sys

logger.remove()

logger.add(sys.stdout, format="{time} {level} {message}", serialize=True)
resource = Resource.create(attributes={
    "service.name": "hallucination-detector-backend"
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
    
    logger.info(
        f"Path: {request.url.path} Method: {request.method} Status: {response.status_code} Latency: {process_time:.2f}ms",
        extra={"otelTraceID": trace_id}
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False
    )