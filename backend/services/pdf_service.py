import io
import httpx
from pypdf import PdfReader
from services.cloudinary_service import generate_signed_pdf_download_url

def extract_text_from_pdf_url(pdf_url: str) -> str:
    """Generates an authenticated Cloudinary download URL and extracts PDF text synchronously."""
    try:
        print(f"[PDF Extractor] Processing URL: {pdf_url}")
        download_url = generate_signed_pdf_download_url(pdf_url)
        print(f"[PDF Extractor] Generated signed API URL: {download_url}")

        response = httpx.get(
            download_url,
            timeout=25.0,
            follow_redirects=True
        )
        response.raise_for_status()

        if not response.content.startswith(b"%PDF"):
            print("[PDF Extractor Error] Downloaded payload is not a valid PDF file stream.")
            return ""

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)

        extracted_text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            extracted_text += page_text + "\n"

        extracted_text = extracted_text.strip()
        print(f"[PDF Extractor] Successfully extracted {len(extracted_text)} characters from {len(reader.pages)} page(s).")
        return extracted_text

    except Exception as e:
        print(f"[PDF Extractor Exception] Failed to extract PDF text: {str(e)}")
        return ""

async def extract_text_from_pdf_url_async(pdf_url: str) -> str:
    """Asynchronously fetches PDF from Cloudinary and extracts text using pypdf without blocking."""
    try:
        download_url = generate_signed_pdf_download_url(pdf_url)

        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            response = await client.get(download_url)
            response.raise_for_status()

        if not response.content.startswith(b"%PDF"):
            print("[PDF Extractor Error] Downloaded payload is not a valid PDF file stream.")
            return ""

        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)

        extracted_text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            extracted_text += page_text + "\n"

        extracted_text = extracted_text.strip()
        print(f"[PDF Extractor Async] Successfully extracted {len(extracted_text)} characters from {len(reader.pages)} page(s).")
        return extracted_text

    except Exception as e:
        print(f"[PDF Extractor Async Exception] Failed to extract PDF text: {str(e)}")
        return ""

def fetch_pdf_bytes(pdf_url: str) -> bytes:
    """Fetches raw PDF bytes via signed Cloudinary URL for streaming synchronously."""
    download_url = generate_signed_pdf_download_url(pdf_url)
    response = httpx.get(download_url, timeout=25.0, follow_redirects=True)
    response.raise_for_status()
    return response.content

async def fetch_pdf_bytes_async(pdf_url: str) -> bytes:
    """Fetches raw PDF bytes via signed Cloudinary URL for streaming asynchronously."""
    download_url = generate_signed_pdf_download_url(pdf_url)
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        response = await client.get(download_url)
        response.raise_for_status()
        return response.content
