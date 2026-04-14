import aiofiles
from pathlib import Path
from uuid import uuid4
from app.config import settings

async def save_file(file, case_id: str) -> str:
    upload_dir = Path(settings.UPLOAD_DIR) / case_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix if file.filename else ''
    filename = f"{uuid4()}{ext}"
    file_path = upload_dir / filename

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    return str(file_path)

async def delete_file(file_url: str) -> None:
    path = Path(file_url)
    if path.exists():
        path.unlink()
