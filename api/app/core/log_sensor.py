"""Filter log akses uvicorn: sensor token penerima Hikvision di path (/hikvision/events/<token> -> .../***)."""
from __future__ import annotations

import logging
import re

_POLA = re.compile(r"(/hikvision/events/)[^/?\s\"]+")


def sensor_path(teks: str) -> str:
    return _POLA.sub(r"\1***", teks)


class SensorTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(sensor_path(a) if isinstance(a, str) else a for a in record.args)
        if isinstance(record.msg, str):
            record.msg = sensor_path(record.msg)
        return True
