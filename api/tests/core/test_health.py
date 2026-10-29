from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.version import APP_VERSION
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Di dalam context: satu event loop per uji, sehingga koneksi DB async tidak terikat loop yang sudah ditutup.
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": APP_VERSION}
    assert "X-Request-ID" in response.headers


def test_version_endpoint(client):
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    assert response.json() == {"version": APP_VERSION}

def test_ready_check(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "db": "ok", "version": APP_VERSION}
    assert "X-Request-ID" in response.headers


def test_ready_reports_503_when_db_unreachable(client, monkeypatch):
    import app.database.session as db_session

    class _Down:
        def connect(self):
            raise OSError("db mati")

    monkeypatch.setattr(db_session, "engine", _Down())
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
