import os
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
from app.config import UPLOAD_DIR


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _is_pdf_url(url: str, content_type: str = "") -> bool:
    from urllib.parse import urlparse
    path = urlparse(url).path.lower()
    if path.endswith(".pdf"):
        return True
    if "application/pdf" in content_type.lower():
        return True
    return False


def extract_text_from_url(url: str) -> tuple[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=60, stream=True)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")

    if _is_pdf_url(url, content_type):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            text = extract_text_from_pdf(tmp_path)
            title = os.path.basename(url.split("?")[0]) or url
            if not text.strip():
                raise ValueError("Could not extract text from the PDF at this URL.")
            return text, title
        finally:
            os.unlink(tmp_path)

    full_content = resp.content
    soup = BeautifulSoup(full_content, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    title = soup.title.string if soup.title else url
    text = soup.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    if not clean_text.strip():
        raise ValueError("No readable text content found at this URL.")

    return clean_text, title


def process_uploaded_file(filename: str, content: bytes) -> tuple[str, str]:
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)
    elif ext in (".txt", ".md", ".csv", ".json", ".log"):
        text = extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return text, filename
