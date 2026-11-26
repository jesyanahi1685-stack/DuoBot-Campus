"""Importa el dataset sintético de Administrativo a MongoDB."""

import argparse
import csv
import os
from pathlib import Path

from pymongo import MongoClient, ReplaceOne
from pymongo.errors import PyMongoError
from pymongo.uri_parser import parse_uri, split_options

BASE = Path(__file__).resolve().parents[2]
RUTA_CSV = BASE / "raw" / "administrativo.csv"

VARIABLE_MONGO = "ADMIN_MONGO_URL"
MONGO_URL_LOCAL = "mongodb://localhost:27017"
BASE_DATOS = "duobot_admin_analytics"
COLECCION = "admin_indicators"


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
        "_id": int(fila["record_id"]),
        "record_id": int(fila["record_id"]),
        "career_id": fila["career_id"],
        "career": fila["career"],
        "year": int(fila["year"]),
        "month": int(fila["month"]),
        "period": fila["period"],
        "applications": int(fila["applications"]),
        "admitted": int(fila["admitted"]),
        "new_enrollments": int(fila["new_enrollments"]),
        "total_enrollment": int(fila["total_enrollment"]),
        "dropouts": int(fila["dropouts"]),
        "graduates": int(fila["graduates"]),
        "capacity": int(fila["capacity"]),
        "scholarships": int(fila["scholarships"]),
        "teachers": int(fila["teachers"]),
        "budget_mxn": float(fila["budget_mxn"]),
        "expenses_mxn": float(fila["expenses_mxn"])
    }


def cargar_datos():
    with open(RUTA_CSV, encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)

        return [
            convertir_registro(fila)
            for fila in lector
        ]


def importar_administrativo(*, permitir_remoto=False):
    uri, base_datos, opciones = resolver_destino(permitir_remoto)
    registros = cargar_datos()

    ids = sorted(r["record_id"] for r in registros)

    if ids != list(range(1, 1441)):
        raise ValueError("Los identificadores no son correctos")

    operaciones = [
        ReplaceOne({"_id": registro["_id"]}, registro, upsert=True)
        for registro in registros
    ]

    try:
        with MongoClient(uri, serverSelectionTimeoutMS=5000, **opciones) as cliente:
            cliente.admin.command("ping")
            coleccion = cliente[base_datos][COLECCION]
            coleccion.create_index("record_id", unique=True)
            coleccion.create_index([("year", 1), ("month", 1), ("career_id", 1)], unique=True)
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
        importar_administrativo(permitir_remoto=args.permitir_remoto)
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
