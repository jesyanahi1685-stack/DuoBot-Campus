"""Resumen de cohortes del dataset sintético de Estudiantes."""

from typing import Annotated, Literal

import pymongo
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field
from pymongo.errors import ConfigurationError, ConnectionFailure, PyMongoError
from starlette.concurrency import run_in_threadpool

from app.auth import AuthError, verify_token
from app.db import get_mongo_db


# data/seed/shared/carreras.json queda fuera de la imagen de este servicio.
CareerId = Literal["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
EnrollmentYear = Annotated[int, Field(strict=True, ge=2014, le=2025)]
DATASET_CUTOFF = "2025-12-31"
MIN_STUDENTS = 10


def _require_user(ctx: Context) -> None:
    request = ctx.request_context.request
    authorization = request.headers.get("authorization") if request is not None else None
    try:
        user = verify_token(authorization)
    except AuthError as exc:
        raise ToolError(f"authentication_required: {exc}") from None
    except KeyError:
        raise ToolError("authentication_required: Token sin usuario.") from None
    if not user.user_id:
        raise ToolError("authentication_required: Token sin usuario.")


def _query_summary(career_id: CareerId | None, enrollment_year: int | None) -> dict:
    filters = {"career_id": career_id, "enrollment_year": enrollment_year}
    match = {field: value for field, value in filters.items() if value is not None}
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": None,
            "student_count": {"$sum": 1},
            "average_grade": {"$avg": "$current_average"},
            "average_attendance": {"$avg": "$attendance_rate"},
            "grade_count": {"$sum": {"$cond": [{"$isNumber": "$current_average"}, 1, 0]}},
            "attendance_count": {"$sum": {"$cond": [{"$isNumber": "$attendance_rate"}, 1, 0]}},
        }},
    ]
    try:
        with pymongo.timeout(2):
            collection = get_mongo_db()["students"]
            with collection.aggregate(pipeline, maxTimeMS=2000) as cursor:
                summary = next(cursor, None)
    except (ConfigurationError, ConnectionFailure):
        raise ToolError("mongo_unavailable: MongoDB no esta disponible.") from None
    except PyMongoError:
        raise ToolError("mongo_query_failed: No se pudo consultar el resumen.") from None

    result = {"as_of": DATASET_CUTOFF, **filters}
    if summary is None:
        return {**result, "status": "no_data"}
    if summary["student_count"] < MIN_STUDENTS:
        return {**result, "status": "suppressed", "minimum_students": MIN_STUDENTS}

    # Un promedio también necesita al menos diez valores numéricos propios.
    grade = summary["average_grade"] if summary["grade_count"] >= MIN_STUDENTS else None
    attendance = summary["average_attendance"] if summary["attendance_count"] >= MIN_STUDENTS else None
    return {
        **result,
        "status": "ok",
        "student_count": summary["student_count"],
        "average_grade": round(grade, 2) if grade is not None else None,
        "average_attendance": round(attendance, 2) if attendance is not None else None,
    }


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def query_dataset_summary(
        ctx: Context, career_id: CareerId | None = None, enrollment_year: EnrollmentYear | None = None
    ) -> dict:
        """Resume una cohorte sintética por carrera y año de ingreso. Requiere un JWT válido.

        El promedio académico y el porcentaje de asistencia se expresan en escala de 0 a 100.
        Un grupo de menos de diez estudiantes devuelve suppressed sin estadísticas.
        """
        _require_user(ctx)
        return await run_in_threadpool(_query_summary, career_id, enrollment_year)

    # Aplicar el rechazo de campos extra tanto en el esquema MCP como en Pydantic.
    tool = mcp._tool_manager.get_tool(query_dataset_summary.__name__)
    arguments = tool.fn_metadata.arg_model
    arguments.model_config["extra"] = "forbid"
    arguments.model_rebuild(force=True)
    tool.parameters = arguments.model_json_schema(by_alias=True)
