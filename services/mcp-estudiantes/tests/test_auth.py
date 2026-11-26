from fastapi.testclient import TestClient
from sqlalchemy import update

from app.db import SessionLocal
from app.main import app
from app.models import Profile

client = TestClient(app)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_me_sin_token_es_401():
    assert client.get("/me").status_code == 401


def test_me_token_invalido_es_401():
    assert client.get("/me", headers=auth("no-es-un-jwt")).status_code == 401


def test_me_token_expirado_es_401(make_token):
    assert client.get("/me", headers=auth(make_token(expires_in=-10))).status_code == 401


def test_me_crea_perfil_en_primer_login(make_token):
    r = client.get("/me", headers=auth(make_token(sub="nuevo", email="nuevo@campus.test")))
    assert r.status_code == 200
    assert r.json() == {"user_id": "nuevo", "email": "nuevo@campus.test", "role": "user", "plan": "free"}


def test_ruta_admin_requiere_rol(make_token):
    token = make_token(sub="rol-test", email="rol@campus.test")
    assert client.get("/admin/ping", headers=auth(token)).status_code == 403
    with SessionLocal() as db:
        db.execute(update(Profile).where(Profile.user_id == "rol-test").values(role="admin"))
        db.commit()
    assert client.get("/admin/ping", headers=auth(token)).status_code == 200


def test_chat_sin_token_es_401():
    r = client.post("/chat", json={"messages": [{"role": "user", "content": "hola"}]})
    assert r.status_code == 401


def test_chat_valida_entrada(make_token):
    r = client.post("/chat", headers=auth(make_token()), json={"messages": [{"role": "system", "content": "x"}]})
    assert r.status_code == 422
