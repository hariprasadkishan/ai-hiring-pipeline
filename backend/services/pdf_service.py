import io
import httpx
from fastapi import HTTPException
from pypdf import PdfReader
import docx
from services.cloudinary_service import generate_signed_pdf_download_url

def extract_text_from_document_bytes(content: bytes, filename_hint: str = "") -> str:
    """Extracts text from PDF or DOCX binary payload."""
    if not content:
        return ""

    # Check for PDF
    if content.startswith(b"%PDF") or filename_hint.lower().endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            extracted_text = ""
            for page in reader.pages:
                extracted_text += (page.extract_text() or "") + "\n"
            return extracted_text.strip()
        except Exception as e:
            print(f"[Document Extractor] PDF extraction error: {e}")

    # Check for DOCX (PK zip header)
    if content.startswith(b"PK\x03\x04") or filename_hint.lower().endswith(".docx"):
        try:
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            paragraphs = [p.text for p in doc.paragraphs if p.text]
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if row_text:
                        paragraphs.append(row_text)
            return "\n".join(paragraphs).strip()
        except Exception as e:
            print(f"[Document Extractor] DOCX extraction error: {e}")

    # Fallback to plain text decode
    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""

def extract_text_from_pdf_url(pdf_url: str) -> str:
    """Generates an authenticated Cloudinary download URL and extracts PDF/DOCX text synchronously."""
    urls = [pdf_url]
    try:
        urls.append(generate_signed_pdf_download_url(pdf_url))
    except Exception:
        pass

    for url in urls:
        try:
            response = httpx.get(
                url,
                timeout=25.0,
                follow_redirects=True
            )
            if response.status_code == 200:
                extracted_text = extract_text_from_document_bytes(response.content, filename_hint=pdf_url)
                if extracted_text:
                    print(f"[Document Extractor] Successfully extracted {len(extracted_text)} characters from document.")
                    return extracted_text
        except Exception as e:
            print(f"[Document Extractor] Fetch attempt error for {url}: {e}")

    return ""

async def extract_text_from_pdf_url_async(pdf_url: str) -> str:
    """Asynchronously fetches PDF/DOCX from Cloudinary and extracts text without blocking."""
    urls = [pdf_url]
    try:
        urls.append(generate_signed_pdf_download_url(pdf_url))
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    extracted_text = extract_text_from_document_bytes(response.content, filename_hint=pdf_url)
                    if extracted_text:
                        print(f"[Document Extractor Async] Successfully extracted {len(extracted_text)} characters from document.")
                        return extracted_text
            except Exception as e:
                print(f"[Document Extractor Async] Fetch attempt error for {url}: {e}")

    return ""

def fetch_pdf_bytes(pdf_url: str) -> bytes:
    """Fetches raw PDF bytes via signed Cloudinary URL for streaming synchronously."""
    urls = [pdf_url]
    try:
        urls.append(generate_signed_pdf_download_url(pdf_url))
    except Exception:
        pass

    for url in urls:
        try:
            response = httpx.get(url, timeout=25.0, follow_redirects=True)
            if response.status_code == 200:
                return response.content
        except Exception:
            pass
    raise HTTPException(status_code=404, detail="Unable to retrieve resume file.")

async def fetch_pdf_bytes_async(pdf_url: str) -> bytes:
    """Fetches raw PDF bytes via signed Cloudinary URL for streaming asynchronously."""
    urls = [pdf_url]
    try:
        urls.append(generate_signed_pdf_download_url(pdf_url))
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.content
            except Exception:
                pass
    raise HTTPException(status_code=404, detail="Unable to retrieve resume file.")

