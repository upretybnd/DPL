import os

from django import forms

MAX_UPLOAD_MB = 5
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DOCUMENT_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}


def validate_upload(upload, allowed_extensions):
    if not upload:
        return upload
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in allowed_extensions:
        allowed = ", ".join(sorted(e.lstrip(".").upper() for e in allowed_extensions))
        raise forms.ValidationError(f"Unsupported file type. Allowed: {allowed}.")
    if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise forms.ValidationError(f"File is too large. Maximum size is {MAX_UPLOAD_MB} MB.")
    return upload
