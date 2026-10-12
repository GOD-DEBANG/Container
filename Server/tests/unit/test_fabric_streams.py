"""
tests/unit/test_fabric_streams.py

Unit tests for State Fabric and Streaming components:
  - L1Cache LRU eviction and TTL expiry
  - RequestCoalescer SingleFlight concurrency suppression
  - MemoryStore durable sequence numbering and queries
  - DeltaEncoder compute and apply diffs
  - EventBuffer ring buffer
  - SSEStreamer formatting
"""

import asyncio
import time
import pytest

from pulse.fabric.l1_cache import L1Cache
from pulse.fabric.coalescing import RequestCoalescer
from pulse.fabric.memory_store import MemoryStore
from pulse.streams.delta_encoder import DeltaEncoder
from pulse.streams.event_buffer import EventBuffer
from pulse.streams.sse import SSEStreamer


class TestL1Cache:
    def test_l1_cache_lru_and_ttl(self):
        cache = L1Cache(capacity=2, default_ttl_seconds=0.1)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") == 1 # Accessed 'a', 'b' is oldest

        cache.set("c", 3) # Evicts 'b'
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3

        # TTL expiration
        time.sleep(0.15)
        assert cache.get("a") is None


class TestRequestCoalescer:
    @pytest.mark.asyncio
    async def test_singleflight_coalescing(self):
        coalescer = RequestCoalescer()
        call_count = 0

        async def expensive_loader():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return "shared_result"

        # Launch 5 concurrent calls with same key
        tasks = [
            coalescer.execute("same_key", expensive_loader)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

        assert all(r == "shared_result" for r in results)
        assert call_count == 1 # Only executed ONCE


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_store_jobs_and_event_cursors(self):
        store = MemoryStore()
        await store.save_job("job_1", {"status": "QUEUED"})

        j = await store.get_job("job_1")
        assert j["status"] == "QUEUED"

        c1 = await store.append_event("job_1", {"msg": "started"})
        c2 = await store.append_event("job_1", {"msg": "chunk_1"})
        assert c1 == 1
        assert c2 == 2

        events = await store.get_events_since("job_1", cursor=1)
        assert len(events) == 1
        assert events[0]["msg"] == "chunk_1"


class TestDeltaStreams:
    def test_delta_encoder_roundtrip(self):
        state1 = {"status": "RUNNING", "progress": 0.1, "temp": "foo"}
        state2 = {"status": "RUNNING", "progress": 0.5} # temp deleted, progress updated

        delta = DeltaEncoder.compute_delta(state1, state2)
        assert delta["set"] == {"progress": 0.5}
        assert delta["del"] == ["temp"]

        rebuilt = DeltaEncoder.apply_delta(state1, delta)
        assert rebuilt == state2

    def test_event_buffer_capacity(self):
        buf = EventBuffer(capacity_per_job=3)
        for i in range(5):
            buf.append("j1", {"cursor": i + 1, "val": i})

        events = buf.get_since("j1", cursor=0)
        assert len(events) == 3 # Capped at 3 most recent

    def test_sse_streamer_formatting(self):
        formatted = SSEStreamer.format_sse_event(
            event_type="pulse_progress",
            data={"ratio": 0.5},
            event_id=42,
        )
        assert "id: 42\n" in formatted
        assert "event: pulse_progress\n" in formatted
        assert 'data: {"ratio": 0.5}\n\n' in formatted

        heartbeat = SSEStreamer.format_heartbeat()
        assert heartbeat == ": ping\n\n"
