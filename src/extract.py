"""PDF text extraction with page numbers (via pypdf)."""

from pypdf import PdfReader


def extract_pages(pdf_path):
    """Return [{'page': 1-indexed int, 'text': str}, ...]."""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page": i + 1, "text": text})
    return pages
