from pydantic import BaseModel, Field


class Block(BaseModel):
    bbox: list[list[float]]
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class OcrImageResponse(BaseModel):
    request_id: str
    engine: str
    blocks: list[Block]
    time_ms: float


class OcrPdfPage(BaseModel):
    page: int
    blocks: list[Block]


class OcrPdfResponse(BaseModel):
    request_id: str
    engine: str
    pages: list[OcrPdfPage]
    time_ms: float


class ExtractedField(BaseModel):
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class OcrFieldsResponse(BaseModel):
    request_id: str
    engine: str
    blocks: list[Block] | None = None
    pages: list[OcrPdfPage] | None = None
    fields: dict[str, ExtractedField | None]
    time_ms: float
