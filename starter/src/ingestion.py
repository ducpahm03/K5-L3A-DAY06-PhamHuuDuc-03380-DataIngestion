"""Read and normalize source data."""
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC), repair hyphenated line breaks, and collapse spaces."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    # Join hyphenated line breaks e.g. read-\nonly -> read-only
    text = re.sub(r"(\w+)-\n(\w+)", r"\1-\2", text)
    # Collapse multiple whitespace characters into single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace 3 or more consecutive newlines with 2 newlines (preserve paragraphs)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def determine_section(page_num: int) -> str:
    """Map physical page inside Chapter 1 to its curriculum section."""
    if page_num <= 20:
        return "1.1_history"
    elif page_num <= 25:
        return "1.2_hardware_network"
    elif page_num <= 39:
        return "1.3_cloud_iot"
    elif page_num <= 44:
        return "1.4_security_ethics"
    else:
        return "1.5_review"


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each page from the PDF, normalize text, and retain metadata."""
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {path}")

    reader = PdfReader(str(path))
    pages: list[DocumentPage] = []

    for idx, pdf_page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = pdf_page.extract_text() or ""
        clean_text = normalize_text(raw_text)

        section = determine_section(page_num)
        page_obj = DocumentPage(
            document_id=document_id,
            source=source,
            page=page_num,
            text=clean_text,
            metadata={
                "section": section,
                "chapter": 1,
                "char_length": len(clean_text)
            }
        )
        pages.append(page_obj)

    return pages
