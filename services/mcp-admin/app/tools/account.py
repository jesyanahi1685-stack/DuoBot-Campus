"""Herramientas MCP de cuenta (comunes a ambos proyectos).

Cada herramienta lee el JWT del encabezado Authorization de la peticion MCP y
valida al usuario en el servidor. Ninguna recibe un user_id como parametro:
solo pueden ver los datos del usuario autenticado (permisos minimos).
"""
from mcp.server.fastmcp import Context, FastMCP
from sqlalchemy import select

from app.auth import get_or_create_profile, verify_token
from app.db import SessionLocal
from app.models import Profile, Subscription


def _authenticated_profile(ctx: Context, db) -> Profile:
    request = ctx.request_context.request
    authorization = request.headers.get("authorization") if request is not None else None
    user = verify_token(authorization)  # lanza AuthError si el token no es valido
    return get_or_create_profile(db, user)


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_user_profile(ctx: Context) -> dict:
        """Devuelve el perfil del usuario autenticado: correo, rol (user/admin) y plan (free/premium)."""
        with SessionLocal() as db:
            p = _authenticated_profile(ctx, db)
            return {"user_id": p.user_id, "email": p.email, "role": p.role, "plan": p.plan}

    @mcp.tool()
    def get_subscription_status(ctx: Context) -> dict:
        """Devuelve el plan del usuario autenticado y el estado de su suscripcion de pago
        (inactive si nunca ha contratado el plan premium)."""
        with SessionLocal() as db:
            p = _authenticated_profile(ctx, db)
            sub = db.scalars(
                select(Subscription)
                .where(Subscription.user_id == p.user_id)
                .order_by(Subscription.id.desc())
            ).first()
            return {"plan": p.plan, "subscription_status": sub.status if sub else "inactive"}
