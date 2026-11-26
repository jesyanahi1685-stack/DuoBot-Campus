"""Pruebas del flujo de pago. Stripe se simula, pero la FIRMA del webhook se verifica de verdad."""
import hashlib
import hmac
import json
import time

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import stripe_client
from app.billing import PROJECT
from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import Profile, Subscription

client = TestClient(app)
SECRET = "whsec_test_secret_for_unit_tests"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def sign(payload: bytes, secret: str = SECRET) -> str:
    ts = int(time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def sub_event(kind, user_id, status="active", sub_id=None, project=None, created=None, customer=None):
    project = PROJECT if project is None else project
    sub_id = sub_id or f"sub_{user_id}"  # los IDs de Stripe son unicos por usuario
    customer = customer or f"cus_{user_id}"
    return {
        "id": f"evt_{kind}_{status}_{created}",
        "type": f"customer.subscription.{kind}",
        "created": created or int(time.time()),
        "data": {"object": {"id": sub_id, "customer": customer, "status": status,
                            "metadata": {"user_id": user_id, "project": project}}},
    }


def post_event(event, secret=SECRET):
    payload = json.dumps(event).encode()
    return client.post("/billing/webhook", content=payload,
                       headers={"stripe-signature": sign(payload, secret), "content-type": "application/json"})


def state(user_id):
    with SessionLocal() as db:
        profile = db.get(Profile, user_id)
        sub = db.scalars(select(Subscription).where(Subscription.user_id == user_id)).first()
        return profile.plan, (sub.status if sub else None)


@pytest.fixture(autouse=True)
def stripe_settings(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_dummy")
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "stripe_price_id_premium", "price_test_123")


@pytest.fixture
def user(make_token):
    """Crea el perfil con un login y devuelve (user_id, token)."""
    def _make(name):
        token = make_token(sub=name, email=f"{name}@campus.test")
        assert client.get("/me", headers=auth(token)).status_code == 200
        return name, token
    return _make


@pytest.fixture
def fake_stripe(monkeypatch):
    calls = {"customers": 0, "checkout": [], "portal": []}

    def create_customer(email, user_id, project):
        calls["customers"] += 1
        return f"cus_{user_id}"

    def create_checkout_session(**kwargs):
        calls["checkout"].append(kwargs)
        return "https://checkout.stripe.test/session"

    def create_portal_session(customer_id, return_url):
        calls["portal"].append((customer_id, return_url))
        return "https://billing.stripe.test/portal"

    monkeypatch.setattr(stripe_client, "create_customer", create_customer)
    monkeypatch.setattr(stripe_client, "create_checkout_session", create_checkout_session)
    monkeypatch.setattr(stripe_client, "create_portal_session", create_portal_session)
    return calls


# ---------- checkout ----------
def test_checkout_requiere_login():
    assert client.post("/billing/checkout").status_code == 401


def test_checkout_devuelve_url_y_marca_proyecto_y_usuario(user, fake_stripe):
    uid, token = user("pay-1")
    r = client.post("/billing/checkout", headers=auth(token))
    assert r.status_code == 200 and r.json() == {"url": "https://checkout.stripe.test/session"}
    sent = fake_stripe["checkout"][0]
    assert sent["user_id"] == uid and sent["project"] == PROJECT and sent["price_id"] == "price_test_123"
    assert sent["success_url"].endswith("/?checkout=success") and sent["cancel_url"].endswith("/?checkout=cancel")
    assert state(uid) == ("free", "inactive")  # volver de pagar NO concede premium


def test_checkout_reutiliza_el_cliente_de_stripe(user, fake_stripe):
    _, token = user("pay-2")
    client.post("/billing/checkout", headers=auth(token))
    client.post("/billing/checkout", headers=auth(token))
    assert fake_stripe["customers"] == 1 and len(fake_stripe["checkout"]) == 2


def test_checkout_sin_configurar_es_503(user, fake_stripe, monkeypatch):
    _, token = user("pay-3")
    monkeypatch.setattr(settings, "stripe_price_id_premium", "")
    assert client.post("/billing/checkout", headers=auth(token)).status_code == 503


def test_checkout_si_ya_es_premium_es_409(user, fake_stripe):
    uid, token = user("pay-4")
    assert post_event(sub_event("created", uid)).status_code == 200
    assert client.post("/billing/checkout", headers=auth(token)).status_code == 409


def test_checkout_error_de_stripe_es_502_sin_detalles(user, monkeypatch):
    _, token = user("pay-5")
    def boom(*a, **k):
        raise stripe.StripeError("detalle interno secreto")
    monkeypatch.setattr(stripe_client, "create_customer", boom)
    r = client.post("/billing/checkout", headers=auth(token))
    assert r.status_code == 502 and "secreto" not in r.text


# ---------- portal ----------
def test_portal_sin_suscripcion_es_404(user, fake_stripe):
    _, token = user("portal-1")
    assert client.post("/billing/portal", headers=auth(token)).status_code == 404


def test_portal_con_cliente_devuelve_url(user, fake_stripe):
    uid, token = user("portal-2")
    client.post("/billing/checkout", headers=auth(token))
    r = client.post("/billing/portal", headers=auth(token))
    assert r.status_code == 200 and r.json()["url"].startswith("https://billing.stripe.test")
    assert fake_stripe["portal"][0][0] == f"cus_{uid}"


# ---------- webhook ----------
def test_webhook_firma_invalida_es_400(user):
    uid, _ = user("wh-1")
    payload = json.dumps(sub_event("created", uid)).encode()
    r = client.post("/billing/webhook", content=payload, headers={"stripe-signature": sign(payload, "otro_secreto")})
    assert r.status_code == 400
    assert client.post("/billing/webhook", content=payload).status_code == 400  # sin firma
    assert state(uid) == ("free", None)


def test_webhook_sin_secreto_configurado_es_503(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    assert client.post("/billing/webhook", content=b"{}").status_code == 503


def test_suscripcion_activa_da_premium(user):
    uid, _ = user("wh-2")
    r = post_event(sub_event("created", uid))
    assert r.status_code == 200 and r.json()["result"] == "updated:active"
    assert state(uid) == ("premium", "active")


def test_pago_fallido_quita_premium_y_cancelar_deja_cancelado(user):
    uid, _ = user("wh-3")
    now = int(time.time())
    post_event(sub_event("created", uid, created=now))
    post_event(sub_event("updated", uid, status="past_due", created=now + 10))
    assert state(uid) == ("free", "past_due")
    post_event(sub_event("updated", uid, status="active", created=now + 20))
    assert state(uid) == ("premium", "active")
    post_event(sub_event("deleted", uid, status="canceled", created=now + 30))
    assert state(uid) == ("free", "canceled")


def test_evento_de_otro_proyecto_se_ignora(user):
    uid, _ = user("wh-4")
    otro = "admin" if PROJECT == "estudiantes" else "estudiantes"
    r = post_event(sub_event("created", uid, project=otro))
    assert r.status_code == 200 and r.json()["result"] == "ignored"
    assert state(uid) == ("free", None)


def test_evento_sin_metadata_o_de_usuario_inexistente_se_ignora():
    ev = sub_event("created", "no-existe")
    assert post_event(ev).json()["result"] == "ignored"
    ev["data"]["object"]["metadata"] = {}
    assert post_event(ev).json()["result"] == "ignored"


def test_evento_viejo_no_pisa_a_uno_nuevo_y_duplicados_son_inofensivos(user):
    uid, _ = user("wh-5")
    now = int(time.time())
    nuevo = sub_event("updated", uid, status="active", created=now + 50)
    viejo = sub_event("updated", uid, status="past_due", created=now + 10)
    assert post_event(nuevo).json()["result"] == "updated:active"
    assert post_event(viejo).json()["result"] == "stale"
    assert post_event(nuevo).json()["result"] == "updated:active"  # reentrega del mismo evento
    assert state(uid) == ("premium", "active")


def test_checkout_completed_solo_vincula_no_concede_plan(user):
    uid, _ = user("wh-6")
    ev = {"id": "evt_cs", "type": "checkout.session.completed", "created": int(time.time()),
          "data": {"object": {"mode": "subscription", "customer": "cus_cs", "subscription": "sub_cs",
                              "metadata": {"user_id": uid, "project": PROJECT}}}}
    assert post_event(ev).json()["result"] == "linked"
    assert state(uid) == ("free", "inactive")
    with SessionLocal() as db:
        row = db.scalars(select(Subscription).where(Subscription.user_id == uid)).first()
        assert (row.stripe_customer_id, row.stripe_subscription_id) == ("cus_cs", "sub_cs")


def test_el_estado_se_ve_en_la_herramienta_mcp(user):
    """get_subscription_status lee la misma tabla que actualiza el webhook."""
    from app.tools import account  # noqa: F401  (la herramienta ya esta registrada en /mcp)
    uid, _ = user("wh-7")
    post_event(sub_event("created", uid))
    with SessionLocal() as db:
        sub = db.scalars(select(Subscription).where(Subscription.user_id == uid).order_by(Subscription.id.desc())).first()
        assert sub.status == "active"
