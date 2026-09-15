from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from app.api.deps import get_current_user
from app.models import User
from app.core.middleware import limiter
import os, uuid, hashlib, json, shutil

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

UPLOAD_DIR = "/app/uploads"
TMP_DIR = os.path.join(UPLOAD_DIR, "tmp")
FINAL_DIR = os.path.join(UPLOAD_DIR, "final")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)


@router.post("/init")
@limiter.limit("10/minute")
async def init_upload(
    request: Request,
    filename: str = Form(...),
    total_size: int = Form(...),
    total_chunks: int = Form(...),
    user: User = Depends(get_current_user),
):
    if total_size > 5 * 1024 * 1024 * 1024:  # Лимит 5 ГБ
        raise HTTPException(status_code=413, detail="File too large (max 5GB)")

    upload_id = str(uuid.uuid4())
    upload_path = os.path.join(TMP_DIR, upload_id)
    os.makedirs(upload_path, exist_ok=True)

    meta = {
        "filename": filename,
        "total_size": total_size,
        "total_chunks": total_chunks,
        "user_id": user.id,
        "uploaded_chunks": 0,
    }
    with open(os.path.join(upload_path, "meta.json"), "w") as f:
        json.dump(meta, f)

    return {"upload_id": upload_id, "message": "Upload initialized"}


@router.post("/chunk")
@limiter.limit("100/minute")
async def upload_chunk(
    request: Request,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    upload_path = os.path.join(TMP_DIR, upload_id)
    meta_file = os.path.join(upload_path, "meta.json")

    if not os.path.exists(meta_file):
        raise HTTPException(status_code=404, detail="Upload session not found")

    with open(meta_file, "r") as f:
        meta = json.load(f)

    if meta["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    chunk_path = os.path.join(upload_path, f"chunk_{chunk_index:06d}")
    with open(chunk_path, "wb") as f:
        f.write(await file.read())

    meta["uploaded_chunks"] += 1
    with open(meta_file, "w") as f:
        json.dump(meta, f)

    return {
        "chunk_index": chunk_index,
        "uploaded": meta["uploaded_chunks"],
        "total": meta["total_chunks"],
    }


@router.post("/complete")
@limiter.limit("10/minute")
async def complete_upload(
    request: Request,
    upload_id: str = Form(...),
    checksum: str = Form(...),
    user: User = Depends(get_current_user),
):
    upload_path = os.path.join(TMP_DIR, upload_id)
    meta_file = os.path.join(upload_path, "meta.json")

    if not os.path.exists(meta_file):
        raise HTTPException(status_code=404, detail="Upload session not found")

    with open(meta_file, "r") as f:
        meta = json.load(f)

    if meta["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if meta["uploaded_chunks"] != meta["total_chunks"]:
        raise HTTPException(status_code=400, detail="Missing chunks")

    final_filename = f"{uuid.uuid4().hex}_{meta['filename']}"
    final_path = os.path.join(FINAL_DIR, final_filename)

    sha256 = hashlib.sha256()
    with open(final_path, "wb") as out_file:
        for i in range(meta["total_chunks"]):
            chunk_path = os.path.join(upload_path, f"chunk_{i:06d}")
            with open(chunk_path, "rb") as in_file:
                while chunk := in_file.read(8192):
                    out_file.write(chunk)
                    sha256.update(chunk)

    if sha256.hexdigest() != checksum:
        os.remove(final_path)
        raise HTTPException(status_code=400, detail="Checksum mismatch")

    shutil.rmtree(upload_path)

    return {"message": "Upload complete", "filename": final_filename}
