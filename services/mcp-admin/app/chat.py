"""Flujo del chatbot: Claude + herramientas MCP.

El endpoint /chat actua como CLIENTE MCP: se conecta al /mcp de este mismo
servicio reenviando el JWT del usuario, descubre las herramientas (list_tools),
se las ofrece a Claude y ejecuta las que Claude pida (call_tool).
"""
import os

from anthropic import AsyncAnthropic
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import settings

SYSTEM_PROMPT = (
    "Eres DuoBot Administrativo, un asistente del campus. Responde siempre en espanol, de forma breve y clara. "
    "Para datos de la cuenta, planes o analisis usa las herramientas disponibles; no inventes datos. "
    "Si una herramienta falla o el usuario no tiene permiso, explicalo con sencillez."
)
MAX_TURNS = 5


def default_mcp_url() -> str:
    return settings.mcp_internal_url or f"http://127.0.0.1:{os.getenv('PORT', '8000')}/mcp"


def _assistant_blocks(content) -> list[dict]:
    blocks = []
    for b in content:
        if b.type == "text":
            blocks.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return blocks


async def run_chat(messages: list[dict], authorization: str, llm=None, url: str | None = None) -> str:
    llm = llm or AsyncAnthropic(api_key=settings.anthropic_api_key)
    async with streamablehttp_client(url or default_mcp_url(), headers={"Authorization": authorization}) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [
                {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                for t in (await session.list_tools()).tools
            ]
            convo = list(messages)
            for _ in range(MAX_TURNS):
                resp = await llm.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=convo,
                )
                if resp.stop_reason != "tool_use":
                    return "".join(b.text for b in resp.content if b.type == "text")
                convo.append({"role": "assistant", "content": _assistant_blocks(resp.content)})
                results = []
                for b in resp.content:
                    if b.type != "tool_use":
                        continue
                    r = await session.call_tool(b.name, b.input)
                    text = "".join(c.text for c in r.content if getattr(c, "type", "") == "text")
                    results.append(
                        {"type": "tool_result", "tool_use_id": b.id, "content": text, "is_error": bool(r.isError)}
                    )
                convo.append({"role": "user", "content": results})
    return "No pude completar la consulta. Intenta reformular tu pregunta."
