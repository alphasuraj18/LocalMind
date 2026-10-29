from pathlib import Path

import pymupdf
from docx import Document


def load_pdf(path: str) -> str:
    document = pymupdf.open(path)
    pages = [page.get_text() for page in document]
    document.close()
    return "\n\n".join(pages).strip()


def load_docx(path: str) -> str:
    document = Document(path)
    return "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ).strip()


def load_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def load_document(path: str) -> str:
    file_path = Path(path)
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return load_pdf(path)

    if extension == ".docx":
        return load_docx(path)

    if extension == ".txt":
        return load_txt(path)

    raise ValueError(
        f"Unsupported file type: {extension}. "
        "Supported types: .pdf, .docx, .txt"
    )

