import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from yuxi.services.operation_log_service import log_operation


async def audit_upload(
    *,
    db: AsyncSession,
    user_id: int | None,
    entry: str,
    filename: str,
    result: str,
    size: int | None = None,
    detected_type: str | None = None,
    content_hash: str | None = None,
    reason: str | None = None,
) -> None:
    details = {
        "entry": entry,
        "filename": Path(filename).name,
        "result": result,
    }
    optional = {
        "size": size,
        "detected_type": detected_type,
        "content_hash": content_hash,
        "reason": reason,
    }
    details.update({key: value for key, value in optional.items() if value is not None})
    await log_operation(
        db,
        user_id,
        "file_upload",
        json.dumps(details, ensure_ascii=False, sort_keys=True),
    )
