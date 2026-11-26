"""Pagos con Stripe: Checkout (suscripcion), portal del cliente y webhook.

El estado del plan SOLO cambia por webhook firmado por Stripe: volver de Checkout
(?checkout=success) no concede nada por si mismo.
"""
import json
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import stripe_client
from app.auth import current_profile
from app.config import settings
from app.db import get_db
from app.models import Profile, Subscription

log = logging.getLogger("duobot.billing")
router = APIRouter(prefix="/billing", tags=["billing"])

# Una sola cuenta de Stripe sirve a los dos proyectos: cada backend marca sus pagos
# con este valor e ignora los eventos de los demas.
PROJECT = "admin"
PREMIUM_STATUSES = {"active", "trialing"}
SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


def _latest(db: Session, user_id: str) -> Subscription | None:
    return db.scalars(
        select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.id.desc())
    ).first()


@router.post("/checkout")
def checkout(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    if not (settings.stripe_secret_key and settings.stripe_price_id_premium):
        raise HTTPException(status_code=503, detail="Los pagos aun no estan configurados")
    if profile.plan == "premium":
        raise HTTPException(status_code=409, detail="Ya tienes el plan premium")
    try:
        row = _latest(db, profile.user_id)
        if row is None or not row.stripe_customer_id:
            customer_id = stripe_client.create_customer(profile.email, profile.user_id, PROJECT)
            if row is None:
                row = Subscription(user_id=profile.user_id, status="inactive")
                db.add(row)
            row.stripe_customer_id = customer_id
            db.commit()
        url = stripe_client.create_checkout_session(
            customer_id=row.stripe_customer_id,
            user_id=profile.user_id,
            project=PROJECT,
            price_id=settings.stripe_price_id_premium,
            success_url=f"{settings.frontend_url}/?checkout=success",
            cancel_url=f"{settings.frontend_url}/?checkout=cancel",
        )
    except stripe.StripeError:
        log.exception("Stripe rechazo la creacion del pago")
        raise HTTPException(status_code=502, detail="No se pudo iniciar el pago")
    return {"url": url}


@router.post("/portal")
def portal(profile: Profile = Depends(current_profile), db: Session = Depends(get_db)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Los pagos aun no estan configurados")
    row = _latest(db, profile.user_id)
    if row is None or not row.stripe_customer_id:
        raise HTTPException(status_code=404, detail="Aun no tienes una suscripcion")
    try:
        url = stripe_client.create_portal_session(row.stripe_customer_id, settings.frontend_url)
    except stripe.StripeError:
        log.exception("Stripe rechazo la creacion del portal")
        raise HTTPException(status_code=502, detail="No se pudo abrir el portal de suscripcion")
    return {"url": url}


def _get_or_create_row(db: Session, user_id: str) -> Subscription:
    row = _latest(db, user_id)
    if row is None:
        row = Subscription(user_id=user_id, status="inactive")
        db.add(row)
    return row


def _apply_subscription(db: Session, user_id: str, sub: dict, created: int, deleted: bool) -> str:
    profile = db.get(Profile, user_id)
    if profile is None:
        return "ignored"
    row = _get_or_create_row(db, user_id)
    sub_id = sub.get("id")
    if row.stripe_subscription_id and sub_id and sub_id != row.stripe_subscription_id and row.status in PREMIUM_STATUSES:
        return "ignored"  # evento de una suscripcion vieja mientras hay otra activa
    if row.last_event_created and created < row.last_event_created:
        return "stale"  # Stripe no garantiza el orden de entrega
    status = "canceled" if deleted else str(sub.get("status") or "inactive")
    row.stripe_customer_id = sub.get("customer") or row.stripe_customer_id
    row.stripe_subscription_id = sub_id or row.stripe_subscription_id
    row.status = status
    row.last_event_created = created
    profile.plan = "premium" if (status in PREMIUM_STATUSES and not deleted) else "free"
    db.commit()
    return f"updated:{status}"


def handle_event(db: Session, event: dict) -> str:
    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}
    created = int(event.get("created") or 0)
    metadata = obj.get("metadata") or {}
    if metadata.get("project") != PROJECT or not metadata.get("user_id"):
        return "ignored"
    user_id = metadata["user_id"]

    if event_type in SUBSCRIPTION_EVENTS:
        return _apply_subscription(db, user_id, obj, created, deleted=event_type.endswith(".deleted"))

    if event_type == "checkout.session.completed" and obj.get("mode") == "subscription":
        if db.get(Profile, user_id) is None:
            return "ignored"
        row = _get_or_create_row(db, user_id)  # solo vincula ids; el plan lo decide la suscripcion
        row.stripe_customer_id = row.stripe_customer_id or obj.get("customer")
        row.stripe_subscription_id = row.stripe_subscription_id or obj.get("subscription")
        db.commit()
        return "linked"
    return "ignored"


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="El webhook no esta configurado")
    payload = await request.body()
    try:
        stripe_client.verify_webhook(payload, request.headers.get("stripe-signature"))
    except (stripe.SignatureVerificationError, ValueError):
        raise HTTPException(status_code=400, detail="Firma invalida")
    result = handle_event(db, json.loads(payload))
    return {"received": True, "result": result}
