import asyncio
import hashlib
import tempfile
import time
import zipfile
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_SIZE_BYTES = 512 * 1024 * 1024
UPLOAD_TEMP_DIR = Path(tempfile.gettempdir()) / "yuxi-uploads"


async def write_upload_to_buffer(
    upload: UploadFile,
    buffer,
    *,
    max_size_bytes: int,
    too_large_message: str,
    chunk_size: int = 1024 * 1024,
) -> int:
    await upload.seek(0)
    written = 0

    while chunk := await upload.read(chunk_size):
        written += len(chunk)
        if written > max_size_bytes:
            raise ValueError(too_large_message)
        await buffer.write(chunk)

    return written


async def read_upload_with_limit(
    upload: UploadFile,
    *,
    max_size_bytes: int,
    too_large_message: str,
    chunk_size: int = 1024 * 1024,
) -> bytes:
    await upload.seek(0)
    written = 0
    chunks: list[bytes] = []

    while chunk := await upload.read(chunk_size):
        written += len(chunk)
        if written > max_size_bytes:
            raise ValueError(too_large_message)
        chunks.append(chunk)

    return b"".join(chunks)


async def write_upload_to_path(
    upload: UploadFile,
    dest: Path,
    *,
    max_size_bytes: int,
    too_large_message: str,
    mode: str = "wb",
    chunk_size: int = 1024 * 1024,
) -> int:
    async with aiofiles.open(dest, mode) as buffer:
        return await write_upload_to_buffer(
            upload,
            buffer,
            max_size_bytes=max_size_bytes,
            too_large_message=too_large_message,
            chunk_size=chunk_size,
        )


async def calculate_path_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    def calculate() -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            while chunk := file.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()

    return await asyncio.to_thread(calculate)


async def validate_upload_file_type(path: Path, filename: str) -> None:
    suffix = Path(filename).suffix.lower()

    def validate() -> None:
        with path.open("rb") as file:
            header = file.read(16)

        valid = True
        if suffix == ".pdf":
            valid = header.startswith(b"%PDF-")
        elif suffix == ".xls":
            valid = header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        elif suffix in {".docx", ".xlsx", ".pptx", ".zip"}:
            valid = zipfile.is_zipfile(path)
            if valid and suffix != ".zip":
                required_prefix = {".docx": "word/", ".xlsx": "xl/", ".pptx": "ppt/"}[suffix]
                try:
                    with zipfile.ZipFile(path) as archive:
                        names = archive.namelist()
                    valid = "[Content_Types].xml" in names and any(name.startswith(required_prefix) for name in names)
                except (OSError, zipfile.BadZipFile):
                    valid = False
        elif suffix in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}:
            expected_formats = {
                ".jpg": {"JPEG"},
                ".jpeg": {"JPEG"},
                ".png": {"PNG"},
                ".bmp": {"BMP"},
                ".tiff": {"TIFF"},
                ".tif": {"TIFF"},
            }
            try:
                with Image.open(path) as image:
                    image.verify()
                    valid = image.format in expected_formats[suffix]
            except (OSError, UnidentifiedImageError):
                valid = False
        elif suffix in {".txt", ".md", ".csv", ".html", ".htm", ".json"}:
            valid = b"\x00" not in header and not header.startswith((b"MZ", b"\x7fELF"))

        if not valid:
            raise ValueError("文件真实类型与后缀不匹配")

    await asyncio.to_thread(validate)


async def cleanup_stale_upload_files(
    directory: Path = UPLOAD_TEMP_DIR,
    *,
    older_than_seconds: int = 24 * 60 * 60,
    now: float | None = None,
) -> int:
    def cleanup() -> int:
        directory.mkdir(parents=True, exist_ok=True)
        cutoff = (now if now is not None else time.time()) - older_than_seconds
        removed = 0
        for path in directory.iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        return removed

    return await asyncio.to_thread(cleanup)
