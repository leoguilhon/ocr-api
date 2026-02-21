import re

from app.ocr.schemas import Block, ExtractedField

DATE_RE = re.compile(r"\b([0-3]?\d[/-][01]?\d[/-]\d{2,4})\b")
TOTAL_INLINE_RE = re.compile(
    r"\b(?:total|valor\s*(?:total)?|amount)\s*[:\-]?\s*(r\$\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+[.,]\d{2})\b",
    re.IGNORECASE,
)
TOTAL_VALUE_RE = re.compile(r"(r\$\s*)?(\d{1,3}(?:[.\s]\d{3})*,\d{2}|\d+[.,]\d{2})", re.IGNORECASE)
CPF_FORMATTED_RE = re.compile(r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b")
CNPJ_FORMATTED_RE = re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b")


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _format_cpf(digits: str) -> str:
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def _format_cnpj(digits: str) -> str:
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"


def _normalize_date(value: str) -> str:
    return value.replace("-", "/")


def _best_confidence(matches: list[tuple[str, float]]) -> ExtractedField | None:
    if not matches:
        return None
    value, conf = sorted(matches, key=lambda item: item[1], reverse=True)[0]
    return ExtractedField(value=value, confidence=round(min(max(conf, 0.2), 0.99), 3))


def extract_common_fields(blocks: list[Block]) -> dict[str, ExtractedField | None]:
    text_entries = [(_normalize_spaces(block.text), block.confidence) for block in blocks if block.text.strip()]
    date_candidates: list[tuple[str, float]] = []
    total_candidates: list[tuple[str, float]] = []
    cpf_candidates: list[tuple[str, float]] = []
    cnpj_candidates: list[tuple[str, float]] = []

    for text, conf in text_entries:
        for match in DATE_RE.findall(text):
            date_candidates.append((_normalize_date(match), conf))
        for _, match in TOTAL_INLINE_RE.findall(text):
            total_candidates.append((match.replace(" ", ""), conf))
        for match in CPF_FORMATTED_RE.findall(text):
            cpf_candidates.append((match, conf))
        for match in CNPJ_FORMATTED_RE.findall(text):
            cnpj_candidates.append((match, conf))

    # Handle numbers broken into adjacent OCR blocks, such as "TOTAL" + "10,00".
    keyword_indices = [index for index, (text, _) in enumerate(text_entries) if "total" in text.lower() or "valor" in text.lower()]
    for index in keyword_indices:
        for neighbor_idx in (index, index + 1, index + 2):
            if neighbor_idx >= len(text_entries):
                continue
            text, conf = text_entries[neighbor_idx]
            for _, match in TOTAL_VALUE_RE.findall(text):
                total_candidates.append((match.replace(" ", ""), conf))

    for text, conf in text_entries:
        compact = re.sub(r"\D", "", text)
        if len(compact) == 11:
            cpf_candidates.append((_format_cpf(compact), min(conf, 0.85)))
        if len(compact) == 14:
            cnpj_candidates.append((_format_cnpj(compact), min(conf, 0.85)))

    identifier = _best_confidence(cnpj_candidates) or _best_confidence(cpf_candidates)
    return {
        "date": _best_confidence(date_candidates),
        "total": _best_confidence(total_candidates),
        "cnpj_cpf": identifier,
    }
