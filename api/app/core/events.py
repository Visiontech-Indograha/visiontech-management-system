"""
app/core/events.py
Penyiaran peristiwa waktu nyata (SSE) di dalam proses (Rencana Kerja v3, T8).

BATASAN: broker hidup di memori SATU proses uvicorn. Produksi menjalankan satu proses; bila nanti memakai banyak
worker, ganti penyiaran ini dengan Postgres LISTEN/NOTIFY (antarmuka `publish`/`subscribe` tetap).

Peristiwa hanya disiarkan SETELAH transaksi berhasil commit (lihat `db/session.py:unit_of_work`); bila rollback,
peristiwa dibuang. Isi peristiwa tidak membawa data pribadi selain yang sudah ada di notifikasi penerimanya.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

QUEUE_SIZE = 100
PENDING_KEY = "pending_events"
AFTER_COMMIT_KEY = "after_commit_callbacks"


class EventBroker:
    """Penyiar peristiwa per pengguna: tiap sambungan SSE memegang satu antrean berukuran terbatas."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, user_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=QUEUE_SIZE)
        self._subscribers.setdefault(str(user_id), set()).add(queue)
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        queues = self._subscribers.get(str(user_id))
        if queues is None:
            return
        queues.discard(queue)
        if not queues:
            self._subscribers.pop(str(user_id), None)

    def publish(self, user_ids: Iterable[str], event: dict[str, Any]) -> None:
        """Kirim ke semua sambungan para pengguna. Antrean penuh → peristiwa terlama dibuang (klien lambat)."""
        for user_id in {str(u) for u in user_ids}:
            for queue in tuple(self._subscribers.get(user_id, ())):
                if queue.full():
                    queue.get_nowait()
                queue.put_nowait(event)

    def subscriber_count(self) -> int:
        return sum(len(q) for q in self._subscribers.values())


broker = EventBroker()


def queue_event(db: AsyncSession, user_ids: Iterable[str], topic: str, data: dict[str, Any]) -> None:
    """Antrekan peristiwa pada sesi; disiarkan hanya bila transaksi commit (`flush_events`)."""
    users = sorted({str(u) for u in user_ids if u})
    if users:
        db.info.setdefault(PENDING_KEY, []).append((users, {"topic": topic, "data": data}))


def queue_after_commit(db: AsyncSession, callback: Callable[[], None]) -> None:
    """Jalankan `callback` hanya setelah transaksi commit (mis. hapus objek MinIO). Rollback = dibuang."""
    db.info.setdefault(AFTER_COMMIT_KEY, []).append(callback)


def flush_events(db: AsyncSession) -> None:
    """Siarkan peristiwa tertunda dan jalankan callback pasca-commit setelah commit berhasil."""
    for callback in db.info.pop(AFTER_COMMIT_KEY, []):
        try:
            callback()
        except Exception:
            logger.exception("Callback pasca-commit gagal")
    for users, event in db.info.pop(PENDING_KEY, []):
        broker.publish(users, event)


def discard_events(db: AsyncSession) -> None:
    """Buang peristiwa tertunda (rollback)."""
    db.info.pop(PENDING_KEY, None)
    db.info.pop(AFTER_COMMIT_KEY, None)
