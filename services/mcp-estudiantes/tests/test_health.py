from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)  # sin 'with': el lifespan del MCP solo corre en el servidor real


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
