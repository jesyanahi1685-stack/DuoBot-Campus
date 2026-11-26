"""Importa el dataset sintético de Estudiantes a MongoDB."""

import argparse
import csv
import os
from pathlib import Path

from pymongo import MongoClient, ReplaceOne
from pymongo.errors import PyMongoError
from pymongo.uri_parser import parse_uri, split_options

BASE = Path(__file__).resolve().parents[2]
RUTA_CSV = BASE / "raw" / "estudiantes.csv"

VARIABLE_MONGO = "ESTUDIANTES_MONGO_URL"
MONGO_URL_LOCAL = "mongodb://localhost:27017"
BASE_DATOS = "duobot_estudiantes_analytics"
COLECCION = "students"


def resolver_destino(permitir_remoto):
    uri = os.environ.get(VARIABLE_MONGO, MONGO_URL_LOCAL).strip()
    es_srv = uri.startswith("mongodb+srv://")
    try:
        if es_srv:
            # Validar el destino y las opciones por separado evita resolver DNS.
            direccion, _, opciones_srv = uri.partition("?")
            destino = parse_uri(direccion.replace("mongodb+srv://", "mongodb://", 1))
            if opciones_srv:
                split_options(opciones_srv)
        else:
            destino = parse_uri(uri)
    except (PyMongoError, ValueError):
        raise ValueError(f"{VARIABLE_MONGO} debe contener una URI válida de MongoDB.") from None

    base_datos = destino["database"] or BASE_DATOS
    if base_datos != BASE_DATOS or destino["collection"] is not None:
        raise ValueError(f"La URI debe apuntar a la base {BASE_DATOS}.")

    nodos = destino["nodelist"]
    es_local = not es_srv and len(nodos) == 1 and nodos[0][0] in {"localhost", "127.0.0.1", "::1"}
    if not es_local and not permitir_remoto:
        raise ValueError("Destino no local. Usa --permitir-remoto para autorizar la importación.")

    # Una conexión local directa evita seguir nodos anunciados por un replica set.
    opciones = {"directConnection": True} if es_local else {}
    return uri, base_datos, opciones


def convertir_registro(fila):
    return {
        "_id": int(fila["student_id"]),
        "student_id": int(fila["student_id"]),
        "career_id": fila["career_id"],
        "career": fila["career"],
        "age": int(fila["age"]),
        "semester": int(fila["semester"]),
        "enrollment_year": int(fila["enrollment_year"]),
        "enrollment_date": fila["enrollment_date"],
        "exit_date": fila["exit_date"] or None,
        "previous_average": float(fila["previous_average"]),
        "current_average": float(fila["current_average"]),
        "attendance_rate": float(fila["attendance_rate"]),
        "subjects_enrolled": int(fila["subjects_enrolled"]),
        "subjects_passed": int(fila["subjects_passed"]),
        "subjects_failed": int(fila["subjects_failed"]),
        "study_hours": int(fila["study_hours"]),
        "scholarship": fila["scholarship"].lower() == "true",
        "employment_status": fila["employment_status"].lower() == "true",
        "academic_status": fila["academic_status"]
    }


def cargar_datos():
    with open(RUTA_CSV, encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)

        return [
            convertir_registro(fila)
            for fila in lector
        ]


def importar_estudiantes(*, permitir_remoto=False):
    uri, base_datos, opciones = resolver_destino(permitir_remoto)
    estudiantes = cargar_datos()

    ids = sorted(e["student_id"] for e in estudiantes)

    if ids != list(range(100001, 105001)):
        raise ValueError("Los identificadores no son correctos")

    operaciones = [
        ReplaceOne({"_id": estudiante["_id"]}, estudiante, upsert=True)
        for estudiante in estudiantes
    ]

    try:
        with MongoClient(uri, serverSelectionTimeoutMS=5000, **opciones) as cliente:
            cliente.admin.command("ping")
            coleccion = cliente[base_datos][COLECCION]
            coleccion.create_index("student_id", unique=True)
            coleccion.create_index("career_id")
            coleccion.create_index("academic_status")
            resultado = coleccion.bulk_write(operaciones)
            total = coleccion.count_documents({})
    except (PyMongoError, ValueError):
        raise RuntimeError(
            "No se pudo completar la importación. Revisa la conexión y los permisos de MongoDB."
        ) from None

    print("Conexión con MongoDB correcta")
    print("Base de datos:", base_datos)
    print("Colección:", COLECCION)
    print("Registros nuevos:", resultado.upserted_count)
    print("Registros modificados:", resultado.modified_count)
    print("Total almacenado:", total)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--permitir-remoto", action="store_true", help="Autoriza escrituras fuera de localhost.")
    args = parser.parse_args()
    try:
        importar_estudiantes(permitir_remoto=args.permitir_remoto)
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
