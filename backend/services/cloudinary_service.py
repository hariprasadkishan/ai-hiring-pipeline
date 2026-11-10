import re
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from config.settings import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
)

# Initialize Cloudinary SDK
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)

def upload_resume(file_obj, student_id: str, opening_id: str, filename: str = "") -> str:
    """Uploads candidate resume (PDF or DOCX) to Cloudinary and returns secure URL."""
    is_docx = filename.lower().endswith(".docx")
    resource_type = "raw" if is_docx else "image"
    public_id = f"resume_{student_id}_{opening_id}"
    if is_docx:
        public_id += ".docx"

    upload_result = cloudinary.uploader.upload(
        file_obj,
        resource_type=resource_type,
        folder="candidate_resumes",
        public_id=public_id,
    )
    return upload_result.get("secure_url")

def generate_signed_pdf_download_url(pdf_url: str) -> str:
    """Extracts public ID and generates signed Cloudinary download URL."""
    if not pdf_url or not pdf_url.startswith("http"):
        return pdf_url
    resource_type = "raw" if ("/raw/upload/" in pdf_url or pdf_url.lower().endswith(".docx")) else "image"
    match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.pdf|\.docx)?$', pdf_url, re.IGNORECASE)
    public_id = match.group(1) if match else pdf_url

    fmt = None
    if resource_type == "image" and pdf_url.lower().endswith(".pdf"):
        fmt = "pdf"
    elif pdf_url.lower().endswith(".docx"):
        fmt = "docx"

    return cloudinary.utils.private_download_url(
        public_id=public_id,
        format=fmt,
        resource_type=resource_type,
        type="upload",
    )
