"""Generator payload PUSH Hikvision untuk tes.

CATATAN: berdasarkan dokumentasi Hikvision, belum dari perangkat; ganti dengan tangkapan asli.
Foto: JPEG kecil sintetis (gradasi), TANPA wajah nyata.
"""
from __future__ import annotations

import io
import json
from typing import Any

from PIL import Image

BOUNDARY = "MIME_boundary_simulasi"


def jpeg_kecil(ukuran: int = 16) -> bytes:
    img = Image.new("RGB", (ukuran, ukuran))
    img.putdata([(x * 8 % 256, y * 8 % 256, 128) for y in range(ukuran) for x in range(ukuran)])
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    return buf.getvalue()


def dokumen_event(*, waktu: str = "2026-11-13T08:01:05+07:00", minor: int = 75, major: int = 5,
                  karyawan: str | None = "EMP0001", kartu: str | None = None, serial_no: int | None = 1001,
                  mode: str = "face", jenis: str = "AccessControllerEvent") -> dict[str, Any]:
    blok: dict[str, Any] = {"deviceName": "Pintu Kantor", "majorEventType": major, "subEventType": minor,
                            "currentVerifyMode": mode}
    if karyawan is not None:
        blok["employeeNoString"] = karyawan
    if kartu is not None:
        blok["cardNo"] = kartu
    if serial_no is not None:
        blok["serialNo"] = serial_no
    return {"ipAddress": "192.168.88.13", "dateTime": waktu, "eventType": jenis, "AccessControllerEvent": blok}


def push_multipart(dokumen: dict[str, Any] | None = None, *, jpeg: bytes | None = None,
                   sertakan_gambar: bool = True) -> tuple[bytes, str]:
    dokumen = dokumen or dokumen_event()
    b = BOUNDARY.encode()
    bagian = [b"--" + b, b'Content-Disposition: form-data; name="event_log"', b"Content-Type: application/json",
              b"", json.dumps(dokumen).encode()]
    if sertakan_gambar:
        bagian += [b"--" + b, b'Content-Disposition: form-data; name="Picture"; filename="Picture.jpg"',
                   b"Content-Type: image/jpeg", b"", jpeg if jpeg is not None else jpeg_kecil()]
    bagian += [b"--" + b + b"--", b""]
    return b"\r\n".join(bagian), f"multipart/form-data; boundary={BOUNDARY}"


def push_json(dokumen: dict[str, Any] | None = None) -> tuple[bytes, str]:
    return json.dumps(dokumen or dokumen_event()).encode(), "application/json"


def push_xml(*, waktu: str = "2026-11-13T08:01:05+07:00", minor: int = 75,
             karyawan: str = "EMP0001") -> tuple[bytes, str]:
    xml = (f'<?xml version="1.0" encoding="UTF-8"?><EventNotificationAlert version="2.0">'
           f"<dateTime>{waktu}</dateTime><eventType>AccessControllerEvent</eventType><AccessControllerEvent>"
           f"<majorEventType>5</majorEventType><subEventType>{minor}</subEventType>"
           f"<employeeNoString>{karyawan}</employeeNoString><serialNo>1002</serialNo></AccessControllerEvent>"
           f"</EventNotificationAlert>")
    return xml.encode(), "application/xml"


def heartbeat() -> tuple[bytes, str]:
    return json.dumps({"dateTime": "2026-11-13T08:00:00+07:00", "eventType": "heartBeat"}).encode(), "application/json"
