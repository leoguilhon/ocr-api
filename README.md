# ocr-api

API OCR pronta para produção, construída com FastAPI e PaddleOCR (CPU), utilizando simulação para cenários reais de documentos fiscais, recibos e formulários.

## Principais recursos

- OCR de imagens (`jpg`, `png`, `webp`) e PDFs.
- Carga única do modelo OCR (singleton) com reaproveitamento entre requests.
- Logging estruturado em JSON com `request_id` e tempo de processamento.
- Validação de tipo/tamanho de arquivo e erros padronizados.
- Extração de campos comuns (`date`, `total`, `cnpj/cpf`) com regex e heurísticas.
- Documentação automática em Swagger (`/docs`) e ReDoc (`/redoc`).
- Testes automatizados com `pytest`.

## Arquitetura

```text
app/
  main.py                  # bootstrap FastAPI, middleware, handlers de erro
  core/config.py           # configurações por ENV (Pydantic Settings)
  core/logging.py          # logging estruturado JSON
  api/routes/health.py     # endpoints de status
  api/routes/ocr.py        # endpoints OCR
  ocr/engine.py            # PaddleOCR singleton + OCR de imagem/pdf
  ocr/schemas.py           # contratos de request/response
  ocr/postprocess.py       # extração de campos por regex
tests/
  test_health.py
  test_ocr.py
scripts/download_models.py # pré-download de modelos OCR
```

## Endpoints

### `GET /`

Resposta:

```json
{"status":"ok","service":"ocr-api"}
```

### `GET /health`

Retorna status, uptime e versão.

### `POST /ocr/image`

Upload `multipart/form-data` com campo `file` (`image/jpeg`, `image/png`, `image/webp`).

Resposta inclui:
- `request_id`
- `engine`
- `blocks[]` com `text`, `confidence`, `bbox`
- `time_ms`

### `POST /ocr/pdf`

Upload `multipart/form-data` com `file` (`application/pdf`).

- Converte cada página em imagem via `pypdfium2`.
- Limite padrão de 10 páginas (configurável por `PDF_MAX_PAGES`).

Resposta:
- `pages[]` com blocos por página
- `request_id`, `engine`, `time_ms`

### `POST /ocr/fields`

Upload de imagem ou PDF.

Executa OCR + pós-processamento para extrair:
- `date`
- `total`
- `cnpj_cpf`

Cada campo retorna valor + confiança aproximada.

## Erros padronizados

Formato:

```json
{
  "request_id": "uuid",
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Tipo de arquivo invalido..."
  }
}
```

Mapeamento:
- `400`: arquivo inválido, imagem ilegível, limite de páginas PDF.
- `413`: arquivo acima de `MAX_UPLOAD_MB`.
- `422`: payload/campos inválidos.

## Rodando localmente

### 1) Requisitos

- Python 3.11+

### 2) Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\\Scripts\\activate  # Windows
pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
```

### 3) (Opcional) baixar modelos antes de subir

```bash
python scripts/download_models.py
```

### 4) Executar API

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger: `http://localhost:8000/docs`

## Exemplos curl

### OCR imagem

```bash
curl -X POST "http://localhost:8000/ocr/image" \
  -F "file=@./sample.png"
```

### OCR PDF

```bash
curl -X POST "http://localhost:8000/ocr/pdf" \
  -F "file=@./sample.pdf"
```

### OCR + campos

```bash
curl -X POST "http://localhost:8000/ocr/fields" \
  -F "file=@./nota-fiscal.png"
```

## Docker

### Build + run

```bash
docker compose up --build
```

API em `http://localhost:8080` ao rodar via Docker Compose.

## Deploy (alto nível)

### Azure App Service

1. Publicar imagem em container registry.
2. Criar Web App for Containers.
3. Configurar variáveis de ambiente (`APP_VERSION`, `OCR_LANG`, etc.).
4. Habilitar health check em `/health`.

### Render

1. Criar serviço Web via Docker.
2. Definir `PORT=8000` e variáveis de ambiente.
3. Deploy automático por branch.
4. Monitorar logs JSON e endpoint `/health`.

## Decisões técnicas

- **FastAPI** pela performance, tipagem e documentação automática.
- **PaddleOCR CPU** para portabilidade sem GPU.
- **Singleton do engine** para evitar recarga de modelo por request.
- **pypdfium2** para rasterização eficiente de PDF.
- **Erros padronizados** para integração previsível no cliente.
- **Dependency override nos testes** para CI rápido e determinístico.
