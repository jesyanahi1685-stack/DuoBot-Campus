"""Servidor MCP + API de Administrativo (esqueleto).

- /health        -> verificacion de despliegue
- /mcp           -> endpoint MCP (HTTP streamable) con las herramientas
Agregar herramientas en app/tools/ y registrarlas aqui.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config import settings

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


@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-admin"}


# El endpoint MCP queda en /mcp (se monta al final para no tapar /health)
app.mount("/", mcp.streamable_http_app())
