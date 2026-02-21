import uuid
from datetime import datetime, timezone
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.ocr import router as ocr_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.state.started_at = datetime.now(timezone.utc)


@app.on_event("startup")
def startup_event() -> None:
    app.state.started_at = datetime.now(timezone.utc)
    logger.info("Application started", extra={"service": settings.app_name, "version": settings.app_version})


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        status_code = response.status_code if response else 500
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-MS"] = str(duration_ms)


def _error_payload(request: Request, *, code: str, message: str) -> dict:
    request_id = getattr(request.state, "request_id", "unknown")
    return {"request_id": request_id, "error": {"code": code, "message": message}}


def _friendly_validation_error(exc: RequestValidationError) -> tuple[str, str]:
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Dados de requisicao invalidos.")
    location = first_error.get("loc", ())

    if "file" in location and "Expected UploadFile" in message:
        return (
            "INVALID_FILE_UPLOAD",
            "Envie o campo 'file' como arquivo em multipart/form-data (nao como texto).",
        )
    if "file" in location and "Field required" in message:
        return ("MISSING_FILE", "O campo obrigatorio 'file' nao foi enviado.")
    return ("VALIDATION_ERROR", message)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
    else:
        payload = _error_payload(request, code="HTTP_ERROR", message=str(exc.detail))
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    code, message = _friendly_validation_error(exc)
    payload = _error_payload(request, code=code, message=message)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled error",
        extra={"request_id": getattr(request.state, "request_id", "unknown"), "error_code": "INTERNAL_ERROR"},
    )
    payload = _error_payload(request, code="INTERNAL_ERROR", message="Erro interno inesperado.")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": settings.app_name}


app.include_router(health_router)
app.include_router(ocr_router)
