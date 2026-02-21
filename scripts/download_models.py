from app.core.config import get_settings
from paddleocr import PaddleOCR


def main() -> None:
    settings = get_settings()
    PaddleOCR(use_angle_cls=True, lang=settings.ocr_lang, use_gpu=False, show_log=False)
    print(f"Modelos OCR prontos para lang={settings.ocr_lang}")


if __name__ == "__main__":
    main()
