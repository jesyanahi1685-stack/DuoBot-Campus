import asyncio
import csv
import json
import os
import runpy
import socket
import threading
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import get_args
from unittest.mock import Mock

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app import chat, db
from app.config import settings
from app.models import Profile
from app.tools import admin_indicators


SERVICE = Path(__file__).resolve().parents[1]
DATA = SERVICE.parents[1] / "data"
TOOL = "query_admin_indicators"


@pytest.fixture(scope="module")
def mcp_url():
    # FastMCP necesita un gestor de sesiones nuevo por cada servidor de pruebas.
    app = runpy.run_path(str(SERVICE / "app" / "main.py"))["app"]
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.02)
            assert server.started, "El servidor MCP de pruebas no inició"
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            server.should_exit = True
            thread.join(timeout=5)


async def _mcp(url, token, tool=None, args=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if tool is None:
                return {t.name: t.inputSchema for t in (await session.list_tools()).tools}
            return await session.call_tool(tool, args or {})


def _call(url, token, **args):
    return asyncio.run(_mcp(url, token, TOOL, args))


def _data(result):
    assert not result.isError, result.content
    return json.loads(result.content[0].text)


@pytest.fixture(scope="module")
def profiles():
    with db.SessionLocal() as session:
        session.add_all([
            Profile(user_id="indicators-admin", email="indicators-admin@test.local", role="admin", plan="free"),
            Profile(user_id="indicators-user", email="indicators-user@test.local", role="user", plan="premium"),
        ])
        session.commit()


@pytest.fixture
def admin_token(profiles, make_token):
    return make_token(sub="indicators-admin")


@pytest.fixture
def mongo(monkeypatch):
    rows = [
        dict(year=2025, month=month, career_id=career, applications=3, admitted=2, new_enrollments=1,
             dropouts=0, graduates=0, budget_mxn=100.01, expenses_mxn=80.02, total_enrollment=month,
             scholarships=2, capacity=350, teachers=3)
        for month in range(1, 13)
        for career in ("01", "02")
    ]

    def find(query, projection, *, max_time_ms):
        assert max_time_ms == 2000 and projection["_id"] == 0
        return iter([
            {field: row[field] for field, included in projection.items() if included}
            for row in rows
            if row["year"] == query["year"]
            and row["month"] in query["month"]["$in"]
            and row["career_id"] in query["career_id"]["$in"]
        ])

    collection = Mock()
    collection.find.side_effect = find
    connect = Mock(return_value={"admin_indicators": collection})
    monkeypatch.setattr(admin_indicators, "get_mongo_db", connect)
    return SimpleNamespace(rows=rows, collection=collection, connect=connect)


def test_discovery_and_catalog(mcp_url):
    tools = asyncio.run(_mcp(mcp_url, None))
    assert {"ping", "get_user_profile", "get_subscription_status", TOOL} <= tools.keys()
    assert tools[TOOL]["additionalProperties"] is False
    assert set(tools[TOOL]["properties"]) == {"year", "month", "career_id"}
    catalog = json.loads((DATA / "seed" / "shared" / "carreras.json").read_text(encoding="utf-8"))
    assert {career["career_id"] for career in catalog} == set(get_args(admin_indicators.CareerId))


@pytest.mark.parametrize("kind", ["missing", "invalid", "expired"])
def test_requires_authentication(mcp_url, make_token, mongo, kind):
    token = {"missing": None, "invalid": "invalid-token", "expired": make_token(expires_in=-60)}[kind]
    result = _call(mcp_url, token, year=2025)
    assert result.isError and "authentication_required" in result.content[0].text
    mongo.connect.assert_not_called()


@pytest.mark.parametrize("user", ["indicators-user", "indicators-no-profile"])
def test_requires_admin_and_never_creates_a_profile(mcp_url, make_token, profiles, mongo, user):
    result = _call(mcp_url, make_token(sub=user), year=2025)
    assert result.isError and "permission_denied" in result.content[0].text
    mongo.connect.assert_not_called()
    with db.SessionLocal() as session:
        assert session.get(Profile, "indicators-no-profile") is None
        assert session.get(Profile, "indicators-user").role == "user"


@pytest.mark.parametrize("args", [
    {}, {"year": 2026}, {"year": "2025"}, {"year": {"$eq": 2025}}, {"year": 2025, "month": 13},
    {"year": 2025, "career_id": "1"}, {"year": 2025, "pipeline": []}, {"year": 2025, "ctx": {}},
])
def test_rejects_invalid_arguments(mcp_url, admin_token, mongo, args):
    result = _call(mcp_url, admin_token, **args)
    assert result.isError and "validation error" in result.content[0].text.lower()
    mongo.connect.assert_not_called()


def test_month_and_year(mcp_url, admin_token, mongo):
    month = _data(_call(mcp_url, admin_token, year=2025, month=3, career_id="01"))
    assert month["status"] == "ok" and month["career_id"] == "01" and month["missing"] == []
    assert month["monthly"]["total_enrollment"] == 3
    assert month["monthly"]["expenses_mxn"] == 80.02

    year = _data(_call(mcp_url, admin_token, year=2025, career_id="01"))
    assert year["status"] == "ok" and year["missing"] == []
    assert year["accumulated"]["new_enrollments"] == 12
    assert year["accumulated"]["budget_mxn"] == 1200.12
    assert "total_enrollment" not in year["accumulated"]
    assert year["year_end"] == {"total_enrollment": 12, "scholarships": 2, "capacity": 350, "teachers": 3}


@pytest.mark.parametrize("month", [4, 12])
def test_annual_missing_rows(mcp_url, admin_token, mongo, month):
    mongo.rows[:] = [row for row in mongo.rows if (row["month"], row["career_id"]) != (month, "02")]
    result = _data(_call(mcp_url, admin_token, year=2025, career_id="02"))
    assert result["status"] == "partial"
    assert result["missing"] == [{"month": month, "career_id": "02"}]
    assert result["accumulated"]["new_enrollments"] == 11
    assert (result["year_end"] is None) == (month == 12)


def test_monthly_partial_and_no_data(mcp_url, admin_token, mongo):
    partial = _data(_call(mcp_url, admin_token, year=2025, month=7))
    assert partial["status"] == "partial" and len(partial["missing"]) == 8
    assert partial["monthly"]["total_enrollment"] == 14
    empty = _data(_call(mcp_url, admin_token, year=2024, month=7, career_id="10"))
    assert empty["status"] == "no_data" and "monthly" not in empty


@pytest.mark.parametrize("error, code", [
    (ServerSelectionTimeoutError, "mongo_unavailable"), (OperationFailure, "mongo_query_failed"),
])
def test_mongo_errors(mcp_url, admin_token, mongo, error, code):
    mongo.collection.find.side_effect = error("internal detail")
    result = _call(mcp_url, admin_token, year=2025)
    assert result.isError and code in result.content[0].text
    assert "internal detail" not in result.content[0].text


def test_chat_calls_new_tool(mcp_url, admin_token, mongo, monkeypatch):
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            assert TOOL in {tool["name"] for tool in kwargs["tools"]}
            query = SimpleNamespace(type="tool_use", id="tu_1", name=TOOL, input={"year": 2025, "career_id": "01"})
            return SimpleNamespace(stop_reason="tool_use", content=[query])
        tool_result = kwargs["messages"][-1]["content"][0]
        assert not tool_result["is_error"]
        entries = json.loads(tool_result["content"])["accumulated"]["new_enrollments"]
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=f"{entries} ingresos")])

    monkeypatch.setattr(chat, "AsyncAnthropic", lambda **_: SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setattr(settings, "anthropic_api_key", "local-test")
    monkeypatch.setattr(settings, "mcp_internal_url", mcp_url)
    response = httpx.post(
        mcp_url.removesuffix("/mcp") + "/chat",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"messages": [{"role": "user", "content": "¿Cuántos ingresos hubo en 2025?"}]},
        trust_env=False,
    )
    assert response.status_code == 200 and response.json() == {"reply": "12 ingresos"}
    assert len(calls) == 2


@pytest.mark.skipif(os.getenv("DUOBOT_TEST_LOCAL_MONGO") != "1", reason="requiere MongoDB local y el CSV")
def test_local_mongo_matches_admin_csv(mcp_url, admin_token, monkeypatch):
    monkeypatch.setattr(settings, "mongo_url", "mongodb://127.0.0.1:27017/duobot_admin_analytics")
    monkeypatch.setattr(db, "_mongo_client", None)
    with (DATA / "raw" / "administrativo.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    try:
        assert db.get_mongo_db()["admin_indicators"].count_documents({}, maxTimeMS=2000) == len(rows) == 1440
        results = {year: _data(_call(mcp_url, admin_token, year=year)) for year in range(2014, 2026)}
        assert all(result["status"] == "ok" for result in results.values())
        for field, known in {"graduates": 2817, "dropouts": 470}.items():
            assert sum(result["accumulated"][field] for result in results.values()) == sum(int(row[field]) for row in rows) == known
        assert results[2025]["accumulated"]["new_enrollments"] == sum(
            int(row["new_enrollments"]) for row in rows if row["year"] == "2025"
        ) == 416
        assert results[2025]["year_end"]["total_enrollment"] == sum(
            int(row["total_enrollment"]) for row in rows if row["year"] == "2025" and row["month"] == "12"
        ) == 1713
        march = _data(_call(mcp_url, admin_token, year=2024, month=3, career_id="02"))["monthly"]
        row = next(row for row in rows if (row["year"], row["month"], row["career_id"]) == ("2024", "3", "02"))
        assert Decimal(str(march["budget_mxn"])) == Decimal(row["budget_mxn"]) == 231300
        assert Decimal(str(march["expenses_mxn"])) == Decimal(row["expenses_mxn"]) == 335385
    finally:
        if db._mongo_client is not None:
            db._mongo_client.close()
