"""Autenticacion y roles. El servidor NUNCA confia en lo que diga el chat.

- verify_token: valida el JWT de Supabase (HS256 con secreto, o ES256/RS256 con JWKS).
- get_or_create_profile: crea el perfil local en el primer login (rol 'user', plan 'free').
- current_profile / require_role: dependencias de FastAPI.
El rol y el plan se leen SIEMPRE de nuestra base (no del token). Para volver admin
a alguien: UPDATE profiles SET role = 'admin' WHERE email = '...'.
"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Profile


class AuthError(Exception):
    """Mensaje seguro para mostrar al cliente."""


@dataclass
class CurrentUser:
    user_id: str
    email: str | None


_jwks_client: PyJWKClient | None = None


def _signing_key(token: str):
    global _jwks_client
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError as exc:
        raise AuthError("Token invalido") from exc
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise AuthError("El servidor no tiene configurado el secreto JWT")
        return settings.supabase_jwt_secret, ["HS256"]
    if alg in ("ES256", "RS256") and settings.supabase_url:
        if _jwks_client is None:
            _jwks_client = PyJWKClient(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            )
        try:
            return _jwks_client.get_signing_key_from_jwt(token).key, [alg]
        except jwt.PyJWTError as exc:
            raise AuthError("No se pudo validar la firma del token") from exc
    raise AuthError("Algoritmo de token no soportado")


def verify_token(authorization: str | None) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Falta el token de autorizacion")
    token = authorization.split(" ", 1)[1].strip()
    key, algorithms = _signing_key(token)
    try:
        claims = jwt.decode(token, key, algorithms=algorithms, audience="authenticated")
    except jwt.PyJWTError as exc:
        raise AuthError("Token invalido o expirado") from exc
    if not claims.get("sub"):
        raise AuthError("Token sin usuario")
    return CurrentUser(user_id=claims["sub"], email=claims.get("email"))


def get_or_create_profile(db: Session, user: CurrentUser) -> Profile:
    profile = db.get(Profile, user.user_id)
    if profile is None:
        profile = Profile(
            user_id=user.user_id,
            email=user.email or f"{user.user_id}@sin-correo.local",
            role="user",
            plan="free",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def current_profile(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Profile:
    try:
        user = verify_token(authorization)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return get_or_create_profile(db, user)


def require_role(*roles: str):
    def dependency(profile: Profile = Depends(current_profile)) -> Profile:
        if profile.role not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return profile

    return dependency
