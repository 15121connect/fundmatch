"""
core/parser.py
Converts uploaded PDF or DOCX files into clean plain text.
"""

import io
import re
from pathlib import Path


def parse(file_bytes: bytes, filename: str) -> str:
    """
    Parse a PDF or DOCX file and return clean plain text.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename, used to detect format.

    Returns:
        Cleaned plain-text string.

    Raises:
        ValueError: If the file type is unsupported or parsing fails.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_bytes)
    elif ext == ".docx":
        return _parse_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Please upload a PDF or DOCX.")


def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required: pip install pdfplumber")

    text_parts = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    raw = "\n\n".join(text_parts)
    return _clean(raw)


def _parse_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required: pip install python-docx")

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    raw = "\n\n".join(paragraphs)
    return _clean(raw)


def _clean(text: str) -> str:
    """
    Normalise raw extracted text:
    - Collapse excessive whitespace and blank lines
    - Remove page numbers (standalone digits on a line)
    - Strip common header/footer noise
    - Normalise unicode quotes and dashes
    """
    # Normalise unicode punctuation
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")

    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Drop standalone page numbers
        if re.fullmatch(r"\d{1,4}", stripped):
            continue
        # Drop very short lines that are likely artefacts (single chars, dashes)
        if len(stripped) < 3 and stripped not in ("", ):
            continue
        cleaned.append(stripped)

    # Rejoin and collapse multiple blank lines to one
    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk(text: str, max_words: int = 300, overlap: int = 50) -> list[str]:
    """
    Split a long text into overlapping word-based chunks.
    Used to embed long proposals more accurately than encoding
    the whole document as a single vector.

    Args:
        text:      Clean proposal text.
        max_words: Maximum words per chunk.
        overlap:   Number of words to repeat at the start of each chunk
                   to preserve context across boundaries.

    Returns:
        List of text chunks.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = end - overlap

    return chunks


def word_count(text: str) -> int:
    return len(text.split())
