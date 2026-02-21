from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api.routes.ocr import get_ocr_engine
from app.main import app
from app.ocr.schemas import Block


class MockEngine:
    info = "MockOCR(cpu)"

    def ocr_image(self, _image):
        return [
            Block(
                bbox=[[0.0, 0.0], [100.0, 0.0], [100.0, 20.0], [0.0, 20.0]],
                text="TOTAL 10,00",
                confidence=0.99,
            )
        ]

    def ocr_pdf(self, _bytes):
        return []


class FieldsMockEngine:
    info = "MockOCR(cpu)"

    def ocr_image(self, _image):
        return [
            Block(
                bbox=[[0.0, 0.0], [90.0, 0.0], [90.0, 20.0], [0.0, 20.0]],
                text="DATA 12/01/2026",
                confidence=0.97,
            ),
            Block(
                bbox=[[0.0, 25.0], [90.0, 25.0], [90.0, 45.0], [0.0, 45.0]],
                text="TOTAL",
                confidence=0.95,
            ),
            Block(
                bbox=[[95.0, 25.0], [180.0, 25.0], [180.0, 45.0], [95.0, 45.0]],
                text="10,00",
                confidence=0.96,
            ),
            Block(
                bbox=[[0.0, 50.0], [190.0, 50.0], [190.0, 70.0], [0.0, 70.0]],
                text="12345678000195",
                confidence=0.94,
            ),
        ]

    def ocr_pdf(self, _bytes):
        return []


def _create_test_image() -> bytes:
    image = Image.new("RGB", (320, 120), color=(255, 255, 255))
    drawer = ImageDraw.Draw(image)
    drawer.text((10, 40), "TOTAL 10,00", fill=(0, 0, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_ocr_image_upload_returns_blocks() -> None:
    app.dependency_overrides[get_ocr_engine] = lambda: MockEngine()
    client = TestClient(app)
    try:
        payload = _create_test_image()
        response = client.post("/ocr/image", files={"file": ("teste.png", payload, "image/png")})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "request_id" in body
    assert body["engine"] == "MockOCR(cpu)"
    assert len(body["blocks"]) >= 1


def test_ocr_image_rejects_string_instead_of_file() -> None:
    app.dependency_overrides[get_ocr_engine] = lambda: MockEngine()
    client = TestClient(app)
    try:
        response = client.post("/ocr/image", data={"file": "nao-e-arquivo"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_FILE_UPLOAD"


def test_ocr_fields_extracts_structured_fields() -> None:
    app.dependency_overrides[get_ocr_engine] = lambda: FieldsMockEngine()
    client = TestClient(app)
    try:
        payload = _create_test_image()
        response = client.post("/ocr/fields", files={"file": ("teste.png", payload, "image/png")})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["fields"]["date"]["value"] == "12/01/2026"
    assert body["fields"]["total"]["value"] == "10,00"
    assert body["fields"]["cnpj_cpf"]["value"] == "12.345.678/0001-95"
