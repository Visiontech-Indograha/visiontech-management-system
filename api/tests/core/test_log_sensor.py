import logging

from app.core.log_sensor import SensorTokenFilter, sensor_path


def test_token_disensor_query_tetap():
    assert sensor_path("/api/v1/hikvision/events/abc123_-X?a=1") == "/api/v1/hikvision/events/***?a=1"
    assert sensor_path("/api/v1/auth/me") == "/api/v1/auth/me"


def test_filter_menyensor_args_log_akses():
    args = ("POST", "/x/hikvision/events/RAHASIA")
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, "%s %s", args, None)
    SensorTokenFilter().filter(rec)
    assert "RAHASIA" not in rec.getMessage()
    assert rec.getMessage().endswith("/hikvision/events/***")
