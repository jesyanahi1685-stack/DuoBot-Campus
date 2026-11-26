"""Indicadores mensuales y anuales para perfiles administrativos."""

from decimal import Decimal
from typing import Annotated, Literal, get_args

import pymongo
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field
from pymongo.errors import ConfigurationError, ConnectionFailure, PyMongoError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.auth import AuthError, verify_token
from app.db import SessionLocal, get_mongo_db
from app.models import Profile


# data/seed/shared/carreras.json queda fuera de la imagen de este servicio.
CareerId = Literal["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
Year = Annotated[int, Field(strict=True, ge=2014, le=2025)]
Month = Annotated[int, Field(strict=True, ge=1, le=12)]
FLOW_FIELDS = ("applications", "admitted", "new_enrollments", "dropouts", "graduates")
MONEY_FIELDS = ("budget_mxn", "expenses_mxn")
SNAPSHOT_FIELDS = ("total_enrollment", "scholarships", "capacity", "teachers")


def _require_admin(ctx: Context) -> None:
    request = ctx.request_context.request
    authorization = request.headers.get("authorization") if request is not None else None
    try:
        user = verify_token(authorization)
    except AuthError as exc:
        raise ToolError(f"authentication_required: {exc}") from None

    try:
        with SessionLocal() as db:
            profile = db.get(Profile, user.user_id)
            if profile is None or profile.role != "admin":
                raise ToolError("permission_denied: Se requiere el rol admin.")
    except SQLAlchemyError:
        raise ToolError("profile_unavailable: No se pudieron comprobar los permisos.") from None


def _sum_indicators(rows: list[dict], fields: tuple[str, ...]) -> dict:
    return {field: sum(row[field] for row in rows) for field in fields}


def _sum_mxn(rows: list[dict]) -> dict:
    # MongoDB almacena estos importes como float. Sumar en Decimal conserva los centavos.
    return {
        field: float(sum(Decimal(str(row[field])) for row in rows).quantize(Decimal("0.01")))
        for field in MONEY_FIELDS
    }


def _query_indicators(year: int, month: int | None, career_id: CareerId | None) -> dict:
    careers = (career_id,) if career_id is not None else get_args(CareerId)
    months = (month,) if month is not None else range(1, 13)
    query = {"year": year, "month": {"$in": list(months)}, "career_id": {"$in": list(careers)}}
    fields = ("month", "career_id", *FLOW_FIELDS, *MONEY_FIELDS, *SNAPSHOT_FIELDS)
    projection = {"_id": 0, **dict.fromkeys(fields, 1)}
    try:
        # PyMongo aplica el mismo plazo al cliente y al comando enviado a MongoDB.
        with pymongo.timeout(2):
            collection = get_mongo_db()["admin_indicators"]
            rows = list(collection.find(query, projection, max_time_ms=2000))
    except (ConfigurationError, ConnectionFailure):
        raise ToolError("mongo_unavailable: MongoDB no esta disponible.") from None
    except PyMongoError:
        raise ToolError("mongo_query_failed: No se pudieron consultar los indicadores.") from None

    found = {(row["month"], row["career_id"]) for row in rows}
    missing = [
        {"month": expected_month, "career_id": career}
        for expected_month in months
        for career in careers
        if (expected_month, career) not in found
    ]
    result = {"year": year, "month": month, "career_id": career_id, "missing": missing}
    if not rows:
        return {**result, "status": "no_data"}

    result["status"] = "partial" if missing else "ok"
    flows = {**_sum_indicators(rows, FLOW_FIELDS), **_sum_mxn(rows)}
    if month is not None:
        return {**result, "monthly": {**flows, **_sum_indicators(rows, SNAPSHOT_FIELDS)}}

    december = [row for row in rows if row["month"] == 12]
    year_end = None
    if not any(entry["month"] == 12 for entry in missing):
        year_end = _sum_indicators(december, SNAPSHOT_FIELDS)
    return {**result, "accumulated": flows, "year_end": year_end}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def query_admin_indicators(
        ctx: Context, year: Year, month: Month | None = None, career_id: CareerId | None = None
    ) -> dict:
        """Consulta indicadores sintéticos por año, mes y carrera. Requiere el rol admin.

        Omite el mes para obtener los flujos acumulados y el cierre de diciembre.
        El estado partial indica que faltan los pares de mes y carrera en missing.
        En una consulta anual, year_end es nulo si diciembre está incompleto.
        """
        await run_in_threadpool(_require_admin, ctx)
        return await run_in_threadpool(_query_indicators, year, month, career_id)

    # FastMCP genera el modelo a partir de la firma. Endurecer solo esta herramienta.
    tool = mcp._tool_manager.get_tool(query_admin_indicators.__name__)
    arguments = tool.fn_metadata.arg_model
    arguments.model_config["extra"] = "forbid"
    arguments.model_rebuild(force=True)
    tool.parameters = arguments.model_json_schema(by_alias=True)
