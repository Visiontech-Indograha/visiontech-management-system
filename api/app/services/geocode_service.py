"""
app/services/geocode_service.py
Cari kota/tempat → koordinat (revisi PM 2026-09-26) lewat Nominatim/OpenStreetMap. Dipanggil dari
backend (bukan peramban) agar CSP web tetap `connect-src 'self'` dan kebijakan pemakaian Nominatim
dipatuhi: User-Agent jelas, ≤ 1 permintaan/detik, hasil di-cache.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import AppError, ValidationError

CACHE_TTL = 24 * 3600
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_lock = asyncio.Lock()
_last_call = 0.0

UNAVAILABLE = "Pencarian lokasi sedang tidak tersedia. Tetapkan titik langsung di peta."


async def _fetch(query: str) -> list[dict[str, Any]]:
    """
    Satu panggilan jaringan ke API eksternal Nominatim (dipisahkan agar mudah diganti di uji tiruan/mock).
    
    Args:
        query: Teks kata kunci.
        
    Returns:
        Daftar dictionary JSON hasil balasan dari Nominatim.
    """
    async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": settings.GEOCODER_USER_AGENT}) as client:
        res = await client.get(settings.GEOCODER_URL, params={
            "q": query, "format": "jsonv2", "limit": 8, "countrycodes": "id", "accept-language": "id",
        })
        res.raise_for_status()
        return list(res.json())


class GeocodeService:
    """Layanan geocoding untuk mengubah teks alamat atau tempat menjadi koordinat peta."""

    async def search(self, query: str) -> list[dict[str, Any]]:
        """
        Mencari koordinat lokasi berdasarkan teks kata kunci menggunakan Nominatim/OpenStreetMap.
        Hasil pencarian akan disimpan di dalam cache untuk mengurangi panggilan ke server eksternal.

        Args:
            query: Teks pencarian lokasi.

        Returns:
            Daftar dictionary berisi nama, latitude, longitude, dan tipe lokasi.

        Raises:
            ValidationError: Jika teks pencarian kurang dari 3 karakter.
            AppError: Jika layanan geocoding sedang tidak dapat diakses.
        """
        global _last_call
        # Membersihkan spasi yang berlebihan pada kata kunci pencarian
        q = " ".join(query.split())
        if len(q) < 3:
            raise ValidationError("Ketik minimal 3 huruf untuk mencari lokasi.")
        key = q.lower()
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return hit[1]
        async with _lock:                                   # ≤ 1 permintaan/detik ke Nominatim
            wait = 1.0 - (time.monotonic() - _last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                raw = await _fetch(q)
            except (httpx.HTTPError, ValueError):
                raise AppError("GEOCODER_UNAVAILABLE", UNAVAILABLE, status=503) from None
            finally:
                _last_call = time.monotonic()
        results = [{
            "name": str(r.get("display_name", "")),
            "lat": float(r["lat"]),
            "lng": float(r["lon"]),
            "type": str(r.get("addresstype") or r.get("type") or ""),
        } for r in raw if "lat" in r and "lon" in r]
        _cache[key] = (time.monotonic(), results)
        return results
