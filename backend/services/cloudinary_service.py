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

def upload_resume(file_obj, student_id: str, opening_id: str) -> str:
    """Uploads candidate resume PDF to Cloudinary and returns secure URL."""
    upload_result = cloudinary.uploader.upload(
        file_obj,
        resource_type="image",
        folder="phd_resumes",
        public_id=f"resume_{student_id}_{opening_id}",
    )
    return upload_result.get("secure_url")

def generate_signed_pdf_download_url(pdf_url: str) -> str:
    """Extracts public ID and generates signed Cloudinary download URL."""
    resource_type = "raw" if "/raw/upload/" in pdf_url else "image"
    match = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.pdf)?$', pdf_url, re.IGNORECASE)
    public_id = match.group(1) if match else pdf_url

    return cloudinary.utils.private_download_url(
        public_id=public_id,
        format="pdf" if resource_type == "image" else None,
        resource_type=resource_type,
        type="upload",
    )
