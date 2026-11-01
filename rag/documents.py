"""Extract searchable, page-aware passages from uploaded PDF documents with strict security checks."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Use pymupdf directly (modern API) with backward compatibility alias
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

import security

MAX_FILE_BYTES = 15 * 1024 * 1024  # 15 MiB per uploaded file
MAX_FILES = 5
MAX_TOTAL_PAGES = 200


@dataclass(frozen=True)
class Chunk:
    doc_name: str
    page: int  # one-indexed page number
    text: str
    chunk_id: str


def clean_text(raw: str) -> str:
    """Preserve words while smoothing line breaks and excess whitespace."""
    text = raw.replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 180) -> list[str]:
    """Create overlapping character chunks, preferring natural word breaks."""
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller")

    text = clean_text(text)
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Avoid severing a word unless the input has no spaces at all.
            last_space = text.rfind(" ", start + int(chunk_size * 0.65), end)
            if last_space != -1:
                end = last_space
        value = text[start:end].strip()
        if value:
            chunks.append(value)
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        start = next_start
    return chunks


def read_pdf(data: bytes, filename: str) -> tuple[list[Chunk], int]:
    """Validate and extract the document as chunks with sanitized filename and page metadata."""
    # Strict security validation on the raw bytes and filename
    is_valid, error_msg = security.validate_pdf_bytes(data, filename, max_bytes=MAX_FILE_BYTES)
    if not is_valid:
        raise ValueError(error_msg)

    safe_name = security.sanitize_filename(filename)

    try:
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("Could not parse this PDF. The document may be corrupted or encrypted.") from exc

    with pdf:
        if pdf.needs_pass:
            raise ValueError("Password-protected PDFs are not supported for security reasons.")
        count = len(pdf)
        if count > MAX_TOTAL_PAGES:
            raise ValueError(f"PDF exceeds the {MAX_TOTAL_PAGES}-page limit (it has {count} pages).")
        
        results: list[Chunk] = []
        for page_idx in range(count):
            content = pdf[page_idx].get_text("text", sort=True)
            for part_idx, part in enumerate(chunk_text(content)):
                results.append(
                    Chunk(
                        doc_name=safe_name,
                        page=page_idx + 1,
                        text=part,
                        chunk_id=f"{safe_name}:p{page_idx+1}:c{part_idx+1}",
                    )
                )
    return results, count
