"""
src/pulse/fabric/upstash_redis_store.py

Optional Upstash Redis / Redis adapter using redis.asyncio.
Never required at import time; gracefully warns if unconfigured.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .store_interface import StoreInterface


class UpstashRedisStore(StoreInterface):
    """
    Redis adapter for distributed job state and event streaming.
    Supports Upstash Redis (via standard redis-py protocol with TLS).
    """

    def __init__(self, redis_url: str) -> None:
        try:
            import redis.asyncio as aioredis
        except ImportError:
            raise ImportError("redis package required for UpstashRedisStore. Run: pip install redis")

        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def save_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        key = f"pulse:job:{job_id}"
        await self._client.set(key, json.dumps(job_data))

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        key = f"pulse:job:{job_id}"
        raw = await self._client.get(key)
        if raw:
            return json.loads(raw)
        return None

    async def append_event(self, job_id: str, event_data: Dict[str, Any]) -> int:
        stream_key = f"pulse:events:{job_id}"
        # Redis RPUSH into list or XADD into stream
        # Using counter + list for strict integer cursor numbering
        cursor_key = f"pulse:cursor:{job_id}"
        cursor = await self._client.incr(cursor_key)
        record = dict(event_data)
        record["cursor"] = cursor
        await self._client.rpush(stream_key, json.dumps(record))
        return cursor

    async def get_events_since(self, job_id: str, cursor: int = 0) -> List[Dict[str, Any]]:
        stream_key = f"pulse:events:{job_id}"
        # Fetch items from index cursor to end
        raw_items = await self._client.lrange(stream_key, cursor, -1)
        return [json.loads(item) for item in raw_items]

    async def close(self) -> None:
        await self._client.aclose()
