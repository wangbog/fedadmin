import uuid
import os
import shutil
import re
import magic
from typing import Callable, List, Optional
from werkzeug.datastructures import FileStorage


# MIME type definitions for different file types
MIME_TYPES = {
    "image": [
        "image/png",
        "image/jpeg",
        "image/webp",
    ],
    "xml": [
        "text/xml",
        "application/xml",
        "application/samlmetadata+xml",
    ],
}


def safe_ext(filename):
    """Extract and validate file extension."""
    _, ext = os.path.splitext(filename)
    ext = ext.lower().strip(".")
    if re.match(r"^[a-z0-9]{1,10}$", ext):
        return ext
    return ""


def idp_metadata_namegen(model, file_data):
    """Generate filename for IdP metadata file."""
    ext = safe_ext(file_data.filename)
    if not ext:
        raise ValueError("Invalid file extension")
    if model.idp_id:
        filename = f"idp-{model.idp_id}-metadata.{ext}"
    else:
        random_str = uuid.uuid4().hex[:8]
        filename = f"idp-{random_str}-metadata.{ext}"
    return f"private/members/{model.organization_id}/{filename}"


def sp_metadata_namegen(model, file_data):
    """Generate filename for SP metadata file."""
    ext = safe_ext(file_data.filename)
    if not ext:
        raise ValueError("Invalid file extension")
    if model.sp_id:
        filename = f"sp-{model.sp_id}-metadata.{ext}"
    else:
        random_str = uuid.uuid4().hex[:8]
        filename = f"sp-{random_str}-metadata.{ext}"
    return f"private/members/{model.organization_id}/{filename}"


def move_uploaded_file(
    storage_root: str,
    temp_relative: str,
    final_relative: str,
    old_relative: str = None,
    delete_old: bool = True,
) -> str:
    """
    Move a file from a temporary location to its final location,
    and optionally delete the old file if it exists and differs.

    Args:
        storage_root: Root storage directory (app.config['STORAGE_ROOT'])
        temp_relative: Relative path of the temporary file (as stored in model after upload)
        final_relative: Desired final relative path
        old_relative: Previous file path (to be deleted if exists and different)
        delete_old: Whether to delete old file

    Returns:
        final_relative (same as input, for convenience)

    Raises:
        ValueError: If target path is invalid (directory traversal attempt)
    """
    # Check whether the final path is within the storage_root to prevent directory traversal
    real_storage = os.path.realpath(storage_root)
    real_final = os.path.realpath(os.path.join(storage_root, final_relative))
    if not real_final.startswith(real_storage):
        raise ValueError("Invalid target path")

    # If paths are the same, no need to move
    if temp_relative == final_relative:
        return final_relative

    temp_path = os.path.join(storage_root, temp_relative)
    final_path = os.path.join(storage_root, final_relative)

    if not os.path.exists(temp_path):
        return final_relative  # Nothing to move

    # Ensure target directory exists
    os.makedirs(os.path.dirname(final_path), exist_ok=True)

    # Move the file
    shutil.move(temp_path, final_path)

    # Delete old file if requested and it's different from the new one
    if delete_old and old_relative and old_relative != final_relative:
        old_path = os.path.join(storage_root, old_relative)
        if os.path.exists(old_path):
            os.remove(old_path)

    return final_relative


def validate_mime_type(
    file_storage: FileStorage,
    allowed_mime_types: List[str],
    file_type_name: str = "File",
    content_checker: Optional[Callable[[bytes], bool]] = None,
) -> None:
    """
    Validate the MIME type of an uploaded file.

    Args:
        file_storage: The uploaded file storage object.
        allowed_mime_types: List of allowed MIME types.
        file_type_name: Human-readable name for the file type (for error messages).
        content_checker: Optional callback function that takes file content (bytes)
            and returns True if the content matches the expected format. This is used
            as a fallback when libmagic cannot correctly identify the file type.
            Useful for text-based formats like XML that libmagic may misidentify.

    Raises:
        ValueError: If the file is empty or has an invalid MIME type.
    """
    if not file_storage or not isinstance(file_storage, FileStorage):
        raise ValueError(f"{file_type_name} is required.")

    # Read a sample of the file to detect MIME type
    file_storage.seek(0)
    sample = file_storage.read(4096)
    file_storage.seek(0)  # Reset position

    if not sample:
        raise ValueError(f"Uploaded {file_type_name.lower()} is empty.")

    # Detect MIME type using python-magic
    mime = magic.from_buffer(sample, mime=True)

    if mime in allowed_mime_types:
        return

    # Fallback: if a content checker is provided, use it to validate content
    # This handles cases where libmagic cannot correctly identify text-based formats
    if content_checker is not None:
        if content_checker(sample):
            return

    raise ValueError(
        f"Invalid {file_type_name.lower()} type: {mime}. "
        f"Allowed types: {', '.join(allowed_mime_types)}"
    )


def validate_image(file_storage: FileStorage) -> None:
    """Validate that a file is an allowed image type."""
    validate_mime_type(file_storage, MIME_TYPES["image"], "Image")


def validate_xml(file_storage: FileStorage) -> None:
    """Validate that a file is an allowed XML type."""
    validate_mime_type(
        file_storage,
        MIME_TYPES["xml"],
        "XML file",
        content_checker=_looks_like_xml,
    )


# ============================================================================
# Private helper functions
# ============================================================================


def _looks_like_xml(content: bytes) -> bool:
    """Check if content looks like XML based on common patterns."""
    try:
        text = content.decode("utf-8", errors="ignore").strip()
        return text.startswith("<?xml") or text.startswith("<")
    except Exception:
        return False
