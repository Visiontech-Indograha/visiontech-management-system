"""
Rate limit token bucket in-memory per IP dan per pengguna (riset 01, F-19).

Berlaku untuk satu instance API saja: status bucket hidup di memori proses. Bila kelak
multi-instance, tiap proses punya bucket sendiri dan keputusan penyimpanan bersama
mengikuti ADR (tabel PostgreSQL atau Redis).

Mode bawaan `RATE_LIMIT_ENFORCE=false` hanya MENCATAT (log WARNING) saat bucket habis dan
membiarkan permintaan lewat. Set `true` untuk menolak dengan 429 + header `Retry-After`.
"""

from __future__ import annotations

import ipaddress
import logging
import math
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Request

from app.core import system_settings
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import verify_jwt_token

logger = logging.getLogger(__name__)

GROUP_AUTH = "auth"  # /auth/login, /auth/refresh
GROUP_FILE_URL = "file_url"  # /files/{id}/url
GROUP_UPLOAD = "upload"  # unggahan berkas, logo ekspor, logo tim
GROUP_FACE = "face"  # seluruh /face/*
GROUP_SETUP = "setup"  # /setup/* (penyiapan awal; selalu ditegakkan)

# Batas memori: di atas ini bucket yang sudah penuh dibuang; bila masih penuh, dibuang yang terlama.
MAX_TRACKED_BUCKETS = 50_000


@dataclass
class _Bucket:
    tokens: float
    updated: float


class TokenBucketLimiter:
    """Token bucket: kapasitas = limit per menit (burst penuh), isi ulang = limit / 60 per detik."""

    def __init__(
        self,
        per_minute: Mapping[str, int],
        *,
        clock: Callable[[], float] = time.monotonic,
        max_buckets: int = MAX_TRACKED_BUCKETS,
    ) -> None:
        for group, limit in per_minute.items():
            if limit <= 0:
                raise ValueError(f"limit rate limit untuk {group!r} harus > 0")
        self._limits = dict(per_minute)
        self._clock = clock
        self._max_buckets = max_buckets
        self._buckets: dict[tuple[str, str], _Bucket] = {}

    def hit(self, group: str, key: str) -> int:
        """Ambil satu token. Kembalikan 0 bila diizinkan, atau jumlah detik tunggu (>= 1) bila habis."""
        capacity = float(self._limits[group])
        rate = capacity / 60.0
        now = self._clock()
        bucket_key = (group, key)
        bucket = self._buckets.get(bucket_key)
        if bucket is None:
            if len(self._buckets) >= self._max_buckets:
                self._prune(now)
            bucket = _Bucket(tokens=capacity, updated=now)
            self._buckets[bucket_key] = bucket
        else:
            bucket.tokens = min(capacity, bucket.tokens + (now - bucket.updated) * rate)
            bucket.updated = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return 0
        return max(1, math.ceil((1.0 - bucket.tokens) / rate))

    def _prune(self, now: float) -> None:
        for (group, key), bucket in list(self._buckets.items()):
            capacity = float(self._limits[group])
            if bucket.tokens + (now - bucket.updated) * capacity / 60.0 >= capacity:
                del self._buckets[(group, key)]  # penuh = sama dengan keadaan baru, aman dibuang
        if len(self._buckets) >= self._max_buckets:
            for bucket_key in list(self._buckets)[: max(1, self._max_buckets // 10)]:
                del self._buckets[bucket_key]


class RateLimitedError(AppError):
    """Permintaan ditolak karena bucket habis (hanya saat RATE_LIMIT_ENFORCE=true)."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(
            "TOO_MANY_REQUESTS",
            "Terlalu banyak permintaan. Coba lagi beberapa saat lagi.",
            status=429,
            details={"retry_after_seconds": retry_after},
            headers={"Retry-After": str(retry_after)},
        )


_limiter: TokenBucketLimiter | None = None


def get_limiter() -> TokenBucketLimiter:
    global _limiter
    if _limiter is None:
        _limiter = TokenBucketLimiter(
            {
                GROUP_AUTH: settings.RATE_LIMIT_AUTH_PER_MIN,
                GROUP_FILE_URL: settings.RATE_LIMIT_FILE_URL_PER_MIN,
                GROUP_UPLOAD: settings.RATE_LIMIT_UPLOAD_PER_MIN,
                GROUP_FACE: settings.RATE_LIMIT_FACE_PER_MIN,
                GROUP_SETUP: settings.RATE_LIMIT_SETUP_PER_MIN,
            }
        )
    return _limiter


def set_limiter(limiter: TokenBucketLimiter | None) -> None:
    """Ganti limiter global (dipakai tes). `None` = bangun ulang dari settings pada pemakaian berikutnya."""
    global _limiter
    _limiter = limiter


@lru_cache(maxsize=8)
def _parse_trusted(raw: str) -> tuple[_Network, ...]:
    networks: list[_Network] = []
    for item in raw.split(","):
        item = item.strip()
        if item:
            networks.append(ipaddress.ip_network(item, strict=False))
    return tuple(networks)


def _parse_ip(value: str) -> _IPAddr | None:
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


_IPAddr = ipaddress.IPv4Address | ipaddress.IPv6Address
_Network = ipaddress.IPv4Network | ipaddress.IPv6Network


def _is_trusted(ip: _IPAddr, networks: tuple[_Network, ...]) -> bool:
    return any(ip in network for network in networks)


def client_ip(request: Request) -> str:
    """
    IP klien untuk rate limit. X-Forwarded-For dibaca hanya bila koneksi langsung berasal dari
    proxy di TRUSTED_PROXY_IPS. Hop dibaca dari kanan; hop pertama yang bukan proxy tepercaya
    adalah klien. Header yang rusak diabaikan (kembali ke IP koneksi).
    """
    peer = request.client.host if request.client else "unknown"
    networks = _parse_trusted(settings.TRUSTED_PROXY_IPS)
    peer_ip = _parse_ip(peer)
    if not networks or peer_ip is None or not _is_trusted(peer_ip, networks):
        return peer

    hops: list[_IPAddr] = []
    for raw_hop in request.headers.get("x-forwarded-for", "").split(","):
        if not raw_hop.strip():
            continue
        parsed = _parse_ip(raw_hop)
        if parsed is None:
            return peer
        hops.append(parsed)
    if not hops:
        return peer
    for hop in reversed(hops):
        if not _is_trusted(hop, networks):
            return str(hop)
    return str(hops[0])


def _user_id(request: Request) -> str | None:
    """`sub` dari access token sah di header Bearer. Token tidak sah = tidak ada identitas pengguna."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    try:
        claims = verify_jwt_token(token.strip())
    except jwt.PyJWTError:
        return None
    sub = claims.get("sub")
    return str(sub) if sub else None


def rate_limit(group: str, *, always: bool = False) -> Callable[[Request], Awaitable[None]]:
    """Dependency FastAPI: konsumsi token per IP dan (bila ada) per pengguna untuk `group`.
    `always=True`: selalu menolak 429 saat habis, tanpa memandang RATE_LIMIT_ENFORCE."""

    async def guard(request: Request) -> None:
        limiter = get_limiter()
        subjects = [("ip", client_ip(request))]
        user = _user_id(request)
        if user is not None:
            subjects.append(("user", user))

        for scope, key in subjects:
            retry_after = limiter.hit(group, f"{scope}:{key}")
            if retry_after == 0:
                continue
            if always or system_settings.rate_limit_enforce():
                raise RateLimitedError(retry_after)
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            logger.warning(
                "rate limit terlampaui (catat saja): grup=%s lingkup=%s kunci=%s retry_after=%ss rute=%s",
                group,
                scope,
                key,
                retry_after,
                path,
            )

    return guard
