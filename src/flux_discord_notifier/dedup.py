import asyncio
import time
from collections import OrderedDict


class DuplicateCache:
    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        if ttl_seconds < 1 or max_entries < 1:
            raise ValueError("deduplication limits must be positive")
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[str, float] = OrderedDict()
        self._lock = asyncio.Lock()

    async def reserve(self, key: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            while self._entries:
                oldest_key, expires_at = next(iter(self._entries.items()))
                if expires_at > now:
                    break
                self._entries.pop(oldest_key)

            expires_at = self._entries.get(key)
            if expires_at is not None and expires_at > now:
                return False

            self._entries[key] = now + self._ttl
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
            return True

    async def release(self, key: str) -> None:
        async with self._lock:
            self._entries.pop(key, None)
