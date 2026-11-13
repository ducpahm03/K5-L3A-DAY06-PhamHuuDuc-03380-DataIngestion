"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split text into overlapping character windows and retain page metadata."""
    text = page.text
    if not text:
        return []

    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    start = 0
    chunk_idx = 0

    while start < len(text):
        end = min(len(text), start + size)
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunk_id = f"{page.document_id}_p{page.page}_fix_{chunk_idx:03d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata={
                        **page.metadata,
                        "chunk_strategy": "fixed_size",
                        "start_char": start,
                        "end_char": end,
                        "char_count": len(chunk_text)
                    }
                )
            )
            chunk_idx += 1

        if end >= len(text):
            break
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs, and retain page metadata."""
    text = page.text
    if not text:
        return []

    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [text]

    chunks: list[Chunk] = []
    current_buf: list[str] = []
    current_len = 0
    chunk_idx = 0

    def flush_buf():
        nonlocal current_buf, current_len, chunk_idx
        if not current_buf:
            return
        combined_text = "\n\n".join(current_buf).strip()
        if combined_text:
            chunk_id = f"{page.document_id}_p{page.page}_para_{chunk_idx:03d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=combined_text,
                    metadata={
                        **page.metadata,
                        "chunk_strategy": "by_paragraph",
                        "char_count": len(combined_text)
                    }
                )
            )
            chunk_idx += 1
        current_buf = []
        current_len = 0

    for para in raw_paragraphs:
        # If single paragraph exceeds max_size, flush existing buffer and split paragraph
        if len(para) > max_size:
            flush_buf()
            start = 0
            step = max_size - 100
            while start < len(para):
                end = min(len(para), start + max_size)
                sub_text = para[start:end].strip()
                if sub_text:
                    chunk_id = f"{page.document_id}_p{page.page}_para_{chunk_idx:03d}"
                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            document_id=page.document_id,
                            source=page.source,
                            page=page.page,
                            text=sub_text,
                            metadata={
                                **page.metadata,
                                "chunk_strategy": "by_paragraph",
                                "char_count": len(sub_text),
                                "is_split_paragraph": True
                            }
                        )
                    )
                    chunk_idx += 1
                if end >= len(para):
                    break
                start += step
        else:
            # Check if adding this paragraph exceeds max_size
            added_len = len(para) + (2 if current_buf else 0)
            if current_len + added_len > max_size and current_buf:
                flush_buf()
            current_buf.append(para)
            current_len += added_len

    flush_buf()
    return chunks
