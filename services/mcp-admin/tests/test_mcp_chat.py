"""Pruebas con el servidor REAL (uvicorn en un hilo): herramientas MCP y flujo del chat."""
import asyncio
import threading
import time
from types import SimpleNamespace

import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.chat import run_chat
from app.main import app

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/mcp"


@pytest.fixture(scope="module", autouse=True)
def live_server():
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield
    server.should_exit = True
    thread.join(timeout=5)


async def _call(tool, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(URL, headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return await s.call_tool(tool, {})


def test_descubre_herramientas():
    async def go():
        async with streamablehttp_client(URL) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                return {t.name for t in (await s.list_tools()).tools}

    assert {"ping", "get_user_profile", "get_subscription_status"} <= asyncio.run(go())


def test_herramienta_con_token_valido(make_token):
    res = asyncio.run(_call("get_user_profile", make_token(sub="mcp-1", email="mcp1@campus.test")))
    assert not res.isError
    assert "mcp1@campus.test" in res.content[0].text


def test_herramienta_sin_token_falla():
    res = asyncio.run(_call("get_user_profile"))
    assert res.isError


def test_estado_de_suscripcion_por_defecto(make_token):
    res = asyncio.run(_call("get_subscription_status", make_token(sub="mcp-2", email="mcp2@campus.test")))
    assert not res.isError
    assert "inactive" in res.content[0].text


class FakeLLM:
    """Simula a Claude: primero pide una herramienta, luego responde con su resultado."""

    def __init__(self):
        self.calls = 0
        self.messages = SimpleNamespace(create=self.create)

    async def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            assert any(t["name"] == "get_user_profile" for t in kwargs["tools"])
            block = SimpleNamespace(type="tool_use", id="tu_1", name="get_user_profile", input={})
            return SimpleNamespace(stop_reason="tool_use", content=[block])
        resultado = kwargs["messages"][-1]["content"][0]["content"]
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=f"Tus datos: {resultado}")])


def test_flujo_del_chat_con_mcp(make_token):
    token = make_token(sub="chat-1", email="chat1@campus.test")
    llm = FakeLLM()
    reply = asyncio.run(
        run_chat([{"role": "user", "content": "¿Quién soy?"}], f"Bearer {token}", llm=llm, url=URL)
    )
    assert "chat1@campus.test" in reply
    assert llm.calls == 2
