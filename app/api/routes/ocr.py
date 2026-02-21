from time import perf_counter

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.core.config import Settings, get_settings
from app.ocr.engine import OcrEngine, get_engine
from app.ocr.postprocess import extract_common_fields
from app.ocr.schemas import OcrFieldsResponse, OcrImageResponse, OcrPdfPage, OcrPdfResponse

router = APIRouter(prefix="/ocr", tags=["ocr"])

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
PDF_TYPES = {"application/pdf"}


def get_ocr_engine() -> OcrEngine:
    return get_engine()


async def _validate_upload(
    file: UploadFile, *, allowed_types: set[str], settings: Settings, request_id: str
) -> bytes:
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "request_id": request_id,
                "error": {
                    "code": "INVALID_FILE_TYPE",
                    "message": f"Tipo de arquivo invalido. Tipos permitidos: {', '.join(sorted(allowed_types))}.",
                },
            },
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "request_id": request_id,
                "error": {"code": "EMPTY_FILE", "message": "Arquivo vazio."},
            },
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "request_id": request_id,
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"Arquivo excede o limite de {settings.max_upload_mb}MB.",
                },
            },
        )
    return content


def _decode_image(image_bytes: bytes, request_id: str) -> np.ndarray:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "request_id": request_id,
                "error": {"code": "INVALID_IMAGE", "message": "Nao foi possivel decodificar a imagem enviada."},
            },
        )
    return image


@router.post("/image", response_model=OcrImageResponse)
async def ocr_image(
    request: Request,
    file: UploadFile = File(...),
    engine: OcrEngine = Depends(get_ocr_engine),
    settings: Settings = Depends(get_settings),
) -> OcrImageResponse:
    request_id = request.state.request_id
    start = perf_counter()
    payload = await _validate_upload(file, allowed_types=IMAGE_TYPES, settings=settings, request_id=request_id)
    image = _decode_image(payload, request_id=request_id)
    blocks = engine.ocr_image(image)
    elapsed_ms = round((perf_counter() - start) * 1000, 2)
    return OcrImageResponse(request_id=request_id, engine=engine.info, blocks=blocks, time_ms=elapsed_ms)


@router.post("/pdf", response_model=OcrPdfResponse)
async def ocr_pdf(
    request: Request,
    file: UploadFile = File(...),
    engine: OcrEngine = Depends(get_ocr_engine),
    settings: Settings = Depends(get_settings),
) -> OcrPdfResponse:
    request_id = request.state.request_id
    start = perf_counter()
    payload = await _validate_upload(file, allowed_types=PDF_TYPES, settings=settings, request_id=request_id)
    try:
        pages = engine.ocr_pdf(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "request_id": request_id,
                "error": {"code": "PDF_PAGE_LIMIT_EXCEEDED", "message": str(exc)},
            },
        ) from exc
    elapsed_ms = round((perf_counter() - start) * 1000, 2)
    return OcrPdfResponse(request_id=request_id, engine=engine.info, pages=pages, time_ms=elapsed_ms)


@router.post("/fields", response_model=OcrFieldsResponse)
async def ocr_fields(
    request: Request,
    file: UploadFile = File(...),
    engine: OcrEngine = Depends(get_ocr_engine),
    settings: Settings = Depends(get_settings),
) -> OcrFieldsResponse:
    request_id = request.state.request_id
    start = perf_counter()

    allowed = IMAGE_TYPES | PDF_TYPES
    payload = await _validate_upload(file, allowed_types=allowed, settings=settings, request_id=request_id)
    blocks = None
    pages: list[OcrPdfPage] | None = None

    if file.content_type in PDF_TYPES:
        try:
            pages = engine.ocr_pdf(payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "request_id": request_id,
                    "error": {"code": "PDF_PAGE_LIMIT_EXCEEDED", "message": str(exc)},
                },
            ) from exc
        merged_blocks = [block for page in pages for block in page.blocks]
        fields = extract_common_fields(merged_blocks)
    else:
        image = _decode_image(payload, request_id=request_id)
        blocks = engine.ocr_image(image)
        fields = extract_common_fields(blocks)

    elapsed_ms = round((perf_counter() - start) * 1000, 2)
    return OcrFieldsResponse(
        request_id=request_id,
        engine=engine.info,
        blocks=blocks,
        pages=pages,
        fields=fields,
        time_ms=elapsed_ms,
    )
