import asyncio
import csv
import json
import os
import runpy
import socket
import threading
import time
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import get_args
from unittest.mock import Mock

import jwt
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from app import db
from app.config import settings
from app.tools import dataset_summary


SERVICE = Path(__file__).resolve().parents[1]
DATA = SERVICE.parents[1] / "data"
TOOL = "query_dataset_summary"


@pytest.fixture(scope="module")
def mcp_url():
    # Usar otra instancia de FastMCP para conservar la prueba de /health existente.
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


@pytest.fixture
def make_token(monkeypatch):
    secret = "student-jwt-signing-secret-for-local-tests"
    monkeypatch.setattr(settings, "supabase_jwt_secret", secret)

    def encode(sub="test-student", expires_in=300):
        claims = {"aud": "authenticated", "exp": int(time.time()) + expires_in}
        if sub is not None:
            claims["sub"] = sub
        return jwt.encode(claims, secret, algorithm="HS256")

    return encode


@pytest.fixture
def mongo(monkeypatch):
    collection = Mock()
    connect = Mock(return_value={"students": collection})
    monkeypatch.setattr(dataset_summary, "get_mongo_db", connect)
    return SimpleNamespace(collection=collection, connect=connect)


def test_discovery_and_catalog(mcp_url):
    tools = asyncio.run(_mcp(mcp_url, None))
    assert {"ping", TOOL} <= tools.keys()
    assert tools[TOOL]["additionalProperties"] is False
    assert set(tools[TOOL]["properties"]) == {"career_id", "enrollment_year"}
    assert not asyncio.run(_mcp(mcp_url, None, "ping")).isError
    catalog = json.loads((DATA / "seed" / "shared" / "carreras.json").read_text(encoding="utf-8"))
    assert {career["career_id"] for career in catalog} == set(get_args(dataset_summary.CareerId))


@pytest.mark.parametrize("kind", ["missing", "invalid", "expired", "no_subject", "empty_subject"])
def test_requires_authentication(mcp_url, make_token, mongo, kind):
    tokens = {
        "missing": None,
        "invalid": "invalid-token",
        "expired": make_token(expires_in=-60),
        "no_subject": make_token(sub=None),
        "empty_subject": make_token(sub=""),
    }
    result = _call(mcp_url, tokens[kind])
    assert result.isError and "authentication_required" in result.content[0].text
    mongo.connect.assert_not_called()


@pytest.mark.parametrize("args", [
    {"career_id": "11"}, {"career_id": 1}, {"career_id": {"$ne": "01"}}, {"enrollment_year": 2013},
    {"enrollment_year": "2025"}, {"enrollment_year": True}, {"collection": "students"}, {"student_id": 100001},
])
def test_rejects_invalid_arguments(mcp_url, make_token, mongo, args):
    result = _call(mcp_url, make_token(), **args)
    assert result.isError and "validation error" in result.content[0].text.lower()
    mongo.connect.assert_not_called()


@pytest.mark.parametrize("count, grade_count, expected", [
    (0, 0, {"status": "no_data"}),
    (9, 9, {"status": "suppressed", "minimum_students": 10}),
    (10, 10, {"status": "ok", "student_count": 10, "average_grade": 87.54, "average_attendance": 91.25}),
    (10, 9, {"status": "ok", "student_count": 10, "average_grade": None, "average_attendance": 91.25}),
])
def test_summary_privacy(mcp_url, make_token, mongo, count, grade_count, expected):
    groups = [{
        "student_count": count, "grade_count": grade_count, "attendance_count": count,
        "average_grade": 87.542, "average_attendance": 91.25,
    }] if count else []
    mongo.collection.aggregate.return_value = nullcontext(iter(groups))
    result = _data(_call(mcp_url, make_token(), career_id="01", enrollment_year=2025))
    assert result == {"as_of": "2025-12-31", "career_id": "01", "enrollment_year": 2025, **expected}
    pipeline, kwargs = mongo.collection.aggregate.call_args
    assert pipeline[0][0] == {"$match": {"career_id": "01", "enrollment_year": 2025}}
    assert kwargs == {"maxTimeMS": 2000}


@pytest.mark.parametrize("error, code", [
    (ServerSelectionTimeoutError, "mongo_unavailable"), (OperationFailure, "mongo_query_failed"),
])
def test_mongo_errors(mcp_url, make_token, mongo, error, code):
    mongo.collection.aggregate.side_effect = error("internal detail")
    result = _call(mcp_url, make_token())
    assert result.isError and code in result.content[0].text
    assert "internal detail" not in result.content[0].text


@pytest.mark.skipif(os.getenv("DUOBOT_TEST_LOCAL_MONGO") != "1", reason="requiere MongoDB local y el CSV")
def test_local_mongo_matches_student_csv(mcp_url, make_token, monkeypatch):
    monkeypatch.setattr(settings, "mongo_url", "mongodb://127.0.0.1:27017/duobot_estudiantes_analytics")
    monkeypatch.setattr(db, "_mongo_client", None)
    with (DATA / "raw" / "estudiantes.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 5000
    token = make_token()
    cohorts = [
        ({}, rows),
        ({"career_id": "10", "enrollment_year": 2025}, [
            row for row in rows if row["career_id"] == "10" and row["enrollment_year"] == "2025"
        ]),
    ]
    try:
        for filters, cohort in cohorts:
            result = _data(_call(mcp_url, token, **filters))
            assert result["status"] == "ok" and result["student_count"] == len(cohort)
            for metric, field in {"average_grade": "current_average", "average_attendance": "attendance_rate"}.items():
                assert result[metric] == round(sum(float(row[field]) for row in cohort) / len(cohort), 2)
    finally:
        if db._mongo_client is not None:
            db._mongo_client.close()
