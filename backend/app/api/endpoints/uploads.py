import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.models import User

router = APIRouter(tags=["uploads"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/tmp/scout_uploads"))


@router.post("/uploads/{chatbot_id}", status_code=status.HTTP_201_CREATED)
async def upload_file(
    chatbot_id: str,
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    allowed_types = {"image/png", "image/jpeg", "image/gif", "application/pdf", "text/plain"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    file_id = str(uuid.uuid4())
    ext = Path(file.filename or "file").suffix
    dest = UPLOAD_DIR / user.organization_id / chatbot_id
    dest.mkdir(parents=True, exist_ok=True)
    save_path = dest / f"{file_id}{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "url": f"/uploads/{save_path.name}",
    }
