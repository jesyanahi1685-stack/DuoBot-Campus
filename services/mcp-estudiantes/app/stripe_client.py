"""Llamadas a Stripe en un solo lugar. Las pruebas reemplazan estas funciones."""
import stripe

from app.config import settings


def _key() -> str:
    if not settings.stripe_secret_key:
        raise RuntimeError("Stripe no esta configurado")
    return settings.stripe_secret_key


def create_customer(email: str, user_id: str, project: str) -> str:
    customer = stripe.Customer.create(
        api_key=_key(), email=email, metadata={"user_id": user_id, "project": project}
    )
    return customer["id"]


def create_checkout_session(
    customer_id: str, user_id: str, project: str, price_id: str, success_url: str, cancel_url: str
) -> str:
    # El proyecto y el usuario viajan en la sesion Y en la suscripcion: asi los webhooks
    # de la suscripcion (que no pasan por la sesion) tambien saben de quien son.
    metadata = {"user_id": user_id, "project": project}
    session = stripe.checkout.Session.create(
        api_key=_key(),
        mode="subscription",
        customer=customer_id,
        client_reference_id=user_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        subscription_data={"metadata": metadata},
    )
    return session["url"]


def create_portal_session(customer_id: str, return_url: str) -> str:
    session = stripe.billing_portal.Session.create(api_key=_key(), customer=customer_id, return_url=return_url)
    return session["url"]


def verify_webhook(payload: bytes, signature: str | None) -> None:
    """Lanza stripe.SignatureVerificationError (o ValueError) si la firma no es valida."""
    stripe.Webhook.construct_event(payload, signature or "", settings.stripe_webhook_secret)
