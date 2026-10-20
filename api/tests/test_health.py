from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers

def test_ready_check():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "db": "ok"}
    assert "X-Request-ID" in response.headers


def test_ready_reports_503_when_db_unreachable(monkeypatch):
    import app.database.session as db_session

    class _Down:
        def connect(self):
            raise OSError("db mati")

    monkeypatch.setattr(db_session, "engine", _Down())
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
