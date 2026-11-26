"""Servidor MCP + API de Administrativo.

- GET  /health      verificacion de despliegue
- GET  /me          perfil del usuario autenticado (rol y plan)
- GET  /admin/ping  ejemplo de ruta restringida al rol admin
- POST /chat        chatbot (Claude + herramientas MCP)
- /mcp              endpoint MCP (HTTP streamable)
Agregar herramientas en app/tools/ y registrarlas aqui.
"""
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field

from app.auth import current_profile, require_role
from app.billing import router as billing_router
from app.chat import run_chat
from app.config import settings
from app.models import Profile
from app.tools import account, admin_indicators

log = logging.getLogger("duobot.admin")

mcp = FastMCP(
    "duobot-admin",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()],
        allowed_origins=[settings.frontend_url],
    ),
)


@mcp.tool()
def ping() -> str:
    """Herramienta de prueba: confirma que el servidor MCP responde."""
    return "pong desde DuoBot Campus - Administrativo"


account.register(mcp)
admin_indicators.register(mcp)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Mcp-Session-Id"],
)


app.include_router(billing_router)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-admin"}


@app.get("/me")
def me(profile: Profile = Depends(current_profile)):
    return {"user_id": profile.user_id, "email": profile.email, "role": profile.role, "plan": profile.plan}


@app.get("/admin/ping")
def admin_ping(_: Profile = Depends(require_role("admin"))):
    return {"ok": True}


@app.post("/chat")
async def chat(
    req: ChatRequest,
    authorization: str | None = Header(default=None),
    _: Profile = Depends(current_profile),
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="El asistente aun no esta configurado")
    try:
        reply = await run_chat([m.model_dump() for m in req.messages], authorization or "")
    except Exception:  # no filtrar detalles internos al cliente
        log.exception("Fallo el flujo del chat")
        raise HTTPException(status_code=502, detail="No se pudo obtener respuesta del asistente")
    return {"reply": reply}


# El endpoint MCP queda en /mcp (se monta al final para no tapar las rutas anteriores)
app.mount("/", mcp.streamable_http_app())
