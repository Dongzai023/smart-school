"""Lock screen image management API routes."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.lock_image import LockScreenImage
from app.models.user import User
from app.services.auth_service import require_admin, get_current_user
from app.ws.manager import ws_manager

router = APIRouter(prefix="/images", tags=["锁屏画面"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@router.get("")
def list_images(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List all lock screen images."""
    images = db.query(LockScreenImage).all()
    return [
        {
            "id": img.id, "name": img.name, "file_name": img.file_name,
            "file_size": img.file_size, "is_default": img.is_default,
            "assigned_group_id": img.assigned_group_id,
            "url": f"/uploads/{img.file_name}",
            "created_at": img.created_at.isoformat() if img.created_at else None,
        }
        for img in images
    ]


@router.post("/upload", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    name: str = Form(...),
    assigned_group_id: Optional[int] = Form(None),
    is_default: bool = Form(False),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Upload a new lock screen image."""
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式，可选: {ALLOWED_EXTENSIONS}")

    # Read file content
    content = await file.read()
    if len(content) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="图片文件过大，最大10MB")

    # Generate unique filename
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # If setting as default, clear other defaults
    if is_default:
        db.query(LockScreenImage).filter(LockScreenImage.is_default == True).update({"is_default": False})

    # Create database record
    image = LockScreenImage(
        name=name,
        file_name=unique_name,
        file_path=file_path,
        file_size=len(content),
        is_default=is_default,
        assigned_group_id=assigned_group_id,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    # Notify agents to sync new image
    await ws_manager.broadcast_all({
        "type": "command",
        "action": "sync_lock_image",
        "params": {
            "image_id": image.id,
            "image_url": f"/uploads/{unique_name}",
            "assigned_group_id": assigned_group_id,
            "is_default": is_default,
        },
    })

    return {"id": image.id, "name": image.name, "file_name": unique_name}


@router.get("/file/{file_name}")
def serve_image(file_name: str):
    """Serve an image file for download/display."""
    file_path = os.path.join(settings.UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(file_path)


@router.put("/{image_id}/default")
async def set_default_image(image_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Set an image as the default lock screen."""
    image = db.query(LockScreenImage).filter(LockScreenImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    db.query(LockScreenImage).filter(LockScreenImage.is_default == True).update({"is_default": False})
    image.is_default = True
    db.commit()

    # Notify agents
    await ws_manager.broadcast_all({
        "type": "command",
        "action": "sync_lock_image",
        "params": {"image_id": image.id, "image_url": f"/uploads/{image.file_name}", "is_default": True},
    })
    return {"message": "设置成功"}


@router.delete("/{image_id}")
def delete_image(image_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """Delete a lock screen image."""
    image = db.query(LockScreenImage).filter(LockScreenImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    # Delete file
    if os.path.exists(image.file_path):
        os.remove(image.file_path)

    db.delete(image)
    db.commit()
    return {"message": "删除成功"}
