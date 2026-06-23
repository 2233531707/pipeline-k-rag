import asyncio


class UploadAdmissionExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        super().__init__("大文件上传并发已达上限，请稍后重试")
        self.retry_after_seconds = retry_after_seconds


class UploadAdmission:
    def __init__(self, *, per_user_limit: int, global_limit: int, retry_after_seconds: int = 2):
        self.per_user_limit = per_user_limit
        self.global_limit = global_limit
        self.retry_after_seconds = retry_after_seconds
        self._active_total = 0
        self._active_by_user: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: str) -> None:
        async with self._lock:
            user_active = self._active_by_user.get(user_id, 0)
            if user_active >= self.per_user_limit or self._active_total >= self.global_limit:
                raise UploadAdmissionExceeded(self.retry_after_seconds)
            self._active_by_user[user_id] = user_active + 1
            self._active_total += 1

    async def release(self, user_id: str) -> None:
        async with self._lock:
            user_active = self._active_by_user[user_id] - 1
            if user_active:
                self._active_by_user[user_id] = user_active
            else:
                del self._active_by_user[user_id]
            self._active_total -= 1


large_upload_admission = UploadAdmission(per_user_limit=4, global_limit=8)
