"""Prueba de humo HTTP y MCP para los dos servicios de DuoBot Campus."""

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


ROOT = Path(__file__).resolve().parents[1]
DATA_TOOLS = {
    "mcp-estudiantes": ("query_dataset_summary", {}),
    "mcp-admin": ("query_admin_indicators", {"year": 2024, "month": 3, "career_id": "02"}),
}
QUESTION = "Saluda brevemente."


class CheckFailure(Exception):
    """Fallo cuyo mensaje se puede incluir en el reporte."""


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failed = False

    def add(self, status: str, label: str, detail: str) -> None:
        line = f"{status} {label} — {detail}"
        self.lines.append(line)
        self.failed |= status == "FALLO"
        print(line, flush=True)

    async def check(self, label, operation):
        try:
            result, detail = await operation()
        except CheckFailure as exc:
            self.add("FALLO", label, str(exc))
        except Exception as exc:
            # No volcar errores de transporte que puedan incluir credenciales o datos.
            self.add("FALLO", label, type(exc).__name__)
        else:
            self.add("OK", label, detail)
            return result
        return None


async def request_json(client, method, path, expected=200, **kwargs):
    response = await client.request(method, path, **kwargs)
    if response.status_code != expected:
        raise CheckFailure(f"HTTP {response.status_code}; esperado {expected}")
    try:
        payload = response.json()
    except ValueError:
        raise CheckFailure("la respuesta no es JSON válido") from None
    if not isinstance(payload, dict):
        raise CheckFailure("se esperaba un objeto JSON")
    return payload


async def call_tool(session, name, arguments):
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise CheckFailure("la herramienta devolvió un error MCP")
    data = getattr(result, "structuredContent", None)
    if data is None and result.content and result.content[0].type == "text":
        try:
            data = json.loads(result.content[0].text)
        except ValueError:
            raise CheckFailure("la herramienta no devolvió JSON válido") from None
    if not isinstance(data, dict):
        raise CheckFailure("la herramienta no devolvió un objeto JSON")
    return data


async def check_mcp(report, base_url, headers, service, profile):
    if service is None:
        report.add("FALLO", "MCP", "no se pudo identificar el servicio en /health")
        return None
    data_tool, arguments = DATA_TOOLS[service]
    try:
        async with streamablehttp_client(
            f"{base_url}/mcp", headers=headers, timeout=15, sse_read_timeout=15
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                async with asyncio.timeout(15):
                    await session.initialize()

                async def list_tools():
                    async with asyncio.timeout(15):
                        result = await session.list_tools()
                    names = {tool.name for tool in result.tools}
                    expected = {"get_user_profile", "get_subscription_status", data_tool}
                    if missing := expected - names:
                        raise CheckFailure(f"faltan: {', '.join(sorted(missing))}")
                    return names, f"{len(names)} herramientas anunciadas"

                async def user_profile():
                    async with asyncio.timeout(15):
                        result = await call_tool(session, "get_user_profile", {})
                    if profile is None or any(
                        result.get(key) != profile.get(key)
                        for key in ("user_id", "email", "role", "plan")
                    ):
                        raise CheckFailure("el perfil MCP no coincide con /me")
                    return result, "identidad, rol y plan coinciden con /me"

                async def subscription():
                    async with asyncio.timeout(15):
                        result = await call_tool(session, "get_subscription_status", {})
                    if profile is None or result.get("plan") != profile["plan"]:
                        raise CheckFailure("el plan MCP no coincide con /me")
                    if not isinstance(result.get("subscription_status"), str):
                        raise CheckFailure("falta el estado de suscripción")
                    return result, "la herramienta devolvió plan y estado de suscripción"

                async def project_data():
                    async with asyncio.timeout(15):
                        result = await call_tool(session, data_tool, arguments)
                    if service == "mcp-estudiantes":
                        count = result.get("student_count")
                        has_data = type(count) is int and count > 0
                    else:
                        monthly = result.get("monthly")
                        has_data = isinstance(monthly, dict) and {
                            "new_enrollments", "total_enrollment", "budget_mxn",
                        } <= monthly.keys()
                    if result.get("status") != "ok" or not has_data:
                        raise CheckFailure("faltan resultados del dataset sintético")
                    return result, "consulta al dataset sintético correcta"

                await report.check("MCP list_tools", list_tools)
                await report.check("MCP get_user_profile", user_profile)
                status = await report.check("MCP get_subscription_status", subscription)
                await report.check(f"MCP {data_tool}", project_data)
                return status
    except Exception as exc:
        report.add("FALLO", "MCP conexión", type(exc).__name__)
        return None


async def run_smoke(args, report):
    headers = {"Authorization": f"Bearer {args.token}"}
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        async def health():
            payload = await request_json(client, "GET", "health")
            service = payload.get("service")
            if payload.get("status") != "ok" or service not in DATA_TOOLS:
                raise CheckFailure("estado o identificador de servicio inesperado")
            return service, service

        async def me():
            payload = await request_json(client, "GET", "me", headers=headers)
            role, plan = payload.get("role"), payload.get("plan")
            user_id = payload.get("user_id")
            if (
                not isinstance(user_id, str) or not user_id
                or role not in ("user", "admin") or plan not in ("free", "premium")
            ):
                raise CheckFailure("el perfil no contiene una identidad, rol y plan válidos")
            return payload, f"rol={role}, plan={plan}"

        async def chat():
            payload = await request_json(
                client, "POST", "chat", headers=headers,
                json={"messages": [{"role": "user", "content": QUESTION}]},
            )
            reply = payload.get("reply")
            if not isinstance(reply, str) or not reply.strip():
                raise CheckFailure("la respuesta del asistente está vacía")
            return reply, "el asistente devolvió texto"

        service = await report.check("GET /health", health)
        profile = await report.check("GET /me", me)
        subscription = await check_mcp(report, args.base_url, headers, service, profile)

        if args.skip_chat:
            report.add("OMITIDO", "POST /chat", "se indicó --skip-chat")
        else:
            await report.check("POST /chat", chat)

        async def portal():
            if not subscription or subscription["plan"] != "free" or subscription["subscription_status"] != "inactive":
                raise CheckFailure("se requiere un perfil de prueba con plan free y estado inactive")
            payload = await request_json(client, "POST", "billing/portal", 404, headers=headers)
            if payload.get("detail") != "Aun no tienes una suscripcion":
                raise CheckFailure("HTTP 404 sin el mensaje esperado de suscripción")
            return payload, "HTTP 404 sin cliente Stripe"

        await report.check("POST /billing/portal", portal)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="URL base del servicio de prueba")
    parser.add_argument("--token", required=True, help="JWT sintético del perfil de prueba")
    parser.add_argument(
        "--out", type=Path, default=ROOT / "docs" / "evidencia" / f"smoke_{date.today():%Y%m%d}.txt",
        help="ruta del reporte de texto",
    )
    parser.add_argument("--skip-chat", action="store_true", help="omite el chat sin Claude configurado")
    args = parser.parse_args()
    args.base_url = args.base_url.rstrip("/")
    try:
        url = urlsplit(args.base_url)
        valid_url = (
            url.scheme in ("http", "https") and url.hostname
            and url.username is None and not url.query and not url.fragment
        )
    except ValueError:
        valid_url = False
    if not valid_url:
        parser.error("--base-url debe ser una URL HTTP(S) sin credenciales, consulta ni fragmento")

    report = Report()
    asyncio.run(run_smoke(args, report))
    report.add(
        "FALLO" if report.failed else "OK", "Resultado",
        "revisa las comprobaciones" if report.failed else "comprobaciones requeridas correctas",
    )
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(report.lines) + "\n", encoding="utf-8")
    except OSError as exc:
        report.add("FALLO", "Guardar reporte", type(exc).__name__)
    return int(report.failed)


if __name__ == "__main__":
    raise SystemExit(main())
