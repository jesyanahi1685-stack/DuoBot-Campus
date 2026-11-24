"""Validacion del JWT de Supabase. El servidor NUNCA confia en lo que diga el chat.

Cada llamada a una herramienta MCP debe traer 'Authorization: Bearer <jwt>'.
NOTA: este ejemplo valida HS256 con SUPABASE_JWT_SECRET. Si el proyecto de
Supabase usa claves asimetricas (JWKS), cambiar la verificacion aqui.
"""
from dataclasses import dataclass

import jwt

from app.config import settings


class AuthError(Exception):
    pass


@dataclass
class CurrentUser:
    user_id: str
    email: str | None


def verify_token(authorization: str | None) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Falta el token de autorizacion")
    token = authorization.split(" ", 1)[1]
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise AuthError("Token invalido o expirado") from exc
    return CurrentUser(user_id=claims["sub"], email=claims.get("email"))
