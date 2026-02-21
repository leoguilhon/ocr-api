from functools import lru_cache

import cv2
import numpy as np
import pypdfium2 as pdfium

from app.core.config import Settings, get_settings
from app.ocr.schemas import Block, OcrPdfPage


class OcrEngine:
    def __init__(self, settings: Settings):
        from paddleocr import PaddleOCR

        self.settings = settings
        self._ocr = PaddleOCR(use_angle_cls=True, lang=settings.ocr_lang, use_gpu=False, show_log=False)

    @property
    def info(self) -> str:
        return f"PaddleOCR(lang={self.settings.ocr_lang},cpu)"

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        if not self.settings.enable_preprocess:
            return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        denoised = cv2.fastNlMeansDenoising(gray, h=12)
        return denoised

    def ocr_image(self, image: np.ndarray) -> list[Block]:
        processed = self._preprocess(image)
        result = self._ocr.ocr(processed, cls=True)
        lines = result[0] if result else []
        blocks: list[Block] = []
        for line in lines:
            if not line or len(line) < 2:
                continue
            bbox, detail = line
            text = str(detail[0]) if isinstance(detail, (list, tuple)) and detail else ""
            confidence = float(detail[1]) if isinstance(detail, (list, tuple)) and len(detail) > 1 else 0.0
            blocks.append(
                Block(
                    bbox=[[float(point[0]), float(point[1])] for point in bbox],
                    text=text.strip(),
                    confidence=round(max(min(confidence, 1.0), 0.0), 4),
                )
            )
        return blocks

    def ocr_pdf(self, pdf_bytes: bytes) -> list[OcrPdfPage]:
        document = pdfium.PdfDocument(pdf_bytes)
        total_pages = len(document)
        if total_pages > self.settings.pdf_max_pages:
            raise ValueError(
                f"PDF possui {total_pages} paginas e excede o limite permitido de {self.settings.pdf_max_pages}."
            )

        pages: list[OcrPdfPage] = []
        for index in range(total_pages):
            page = document[index]
            bitmap = page.render(scale=2.0).to_numpy()
            image = cv2.cvtColor(bitmap, cv2.COLOR_RGB2BGR)
            blocks = self.ocr_image(image)
            pages.append(OcrPdfPage(page=index + 1, blocks=blocks))
        return pages


@lru_cache
def get_engine() -> OcrEngine:
    return OcrEngine(settings=get_settings())
