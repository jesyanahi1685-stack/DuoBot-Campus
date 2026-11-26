
import csv
import json
import random
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parents[2]

RUTA_CARRERAS = BASE / "seed" / "shared" / "carreras.json"
RUTA_ESTUDIANTES = BASE / "raw" / "estudiantes.csv"
RUTA_SALIDA = BASE / "raw" / "administrativo.csv"


def cargar_carreras():
    with open(RUTA_CARRERAS, encoding="utf-8") as archivo:
        return json.load(archivo)


def cargar_estudiantes():
    estudiantes = []

    with open(RUTA_ESTUDIANTES, encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)

        for fila in lector:
            estudiantes.append({
                "career_id": fila["career_id"],
                "ingreso": date.fromisoformat(
                    fila["enrollment_date"]
                ),
                "salida": date.fromisoformat(
                    fila["exit_date"]
                ) if fila["exit_date"] else None,
                "estado": fila["academic_status"],
                "beca": fila["scholarship"].lower() == "true"
            })

    return estudiantes


def siguiente_mes(fecha):
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 1)

    return date(fecha.year, fecha.month + 1, 1)


def generar_dataset():
    random.seed(43)

    carreras = cargar_carreras()
    estudiantes = cargar_estudiantes()

    registros = []
    record_id = 1

    for anio in range(2014, 2026):
        for mes in range(1, 13):

            inicio = date(anio, mes, 1)
            fin = siguiente_mes(inicio)

            for carrera in carreras:

                alumnos = [
                    e for e in estudiantes
                    if e["career_id"] == carrera["career_id"]
                ]

                # Nuevos ingresos durante el mes
                nuevos = sum(
                    inicio <= e["ingreso"] < fin
                    for e in alumnos
                )

                # Estudiantes activos al cierre del mes
                activos = [
                    e for e in alumnos
                    if e["ingreso"] < fin
                    and (
                        e["salida"] is None
                        or e["salida"] >= fin
                    )
                ]

                matricula = len(activos)

                # Bajas durante el mes
                bajas = sum(
                    e["estado"] == "Desertor"
                    and e["salida"] is not None
                    and inicio <= e["salida"] < fin
                    for e in alumnos
                )

                # Graduados durante el mes
                graduados = sum(
                    e["estado"] == "Graduado"
                    and e["salida"] is not None
                    and inicio <= e["salida"] < fin
                    for e in alumnos
                )

                # Estudiantes activos con beca
                becas = sum(
                    e["beca"] for e in activos
                )

                # Solicitudes y admisiones simuladas
                if nuevos > 0:
                    admitidos = nuevos + random.randint(1, 15)
                    solicitudes = admitidos + random.randint(5, 35)
                else:
                    admitidos = 0
                    solicitudes = 0

                # Recursos institucionales simulados
                capacidad = 350
                docentes = max(3, (matricula + 24) // 25)

                presupuesto = (
                    25000
                    + docentes * 18000
                    + matricula * 350
                )

                gastos = presupuesto * random.uniform(
                    0.80, 0.98
                )

                # Anomalías controladas para futuras pruebas
                if (anio, mes, carrera["career_id"]) in [
                    (2019, 10, "03"),
                    (2024, 3, "02")
                ]:
                    gastos = presupuesto * 1.45

                periodo = f"{anio}-{1 if mes <= 6 else 2}"

                registros.append({
                    "record_id": record_id,
                    "career_id": carrera["career_id"],
                    "career": carrera["career"],
                    "year": anio,
                    "month": mes,
                    "period": periodo,
                    "applications": solicitudes,
                    "admitted": admitidos,
                    "new_enrollments": nuevos,
                    "total_enrollment": matricula,
                    "dropouts": bajas,
                    "graduates": graduados,
                    "capacity": capacidad,
                    "scholarships": becas,
                    "teachers": docentes,
                    "budget_mxn": round(presupuesto, 2),
                    "expenses_mxn": round(gastos, 2)
                })

                record_id += 1

    validar_registros(registros, estudiantes)

    RUTA_SALIDA.parent.mkdir(
        parents=True, exist_ok=True
    )

    with open(
        RUTA_SALIDA,
        "w",
        newline="",
        encoding="utf-8"
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=registros[0].keys()
        )

        escritor.writeheader()
        escritor.writerows(registros)

    print("Dataset administrativo generado correctamente")
    print("Total de registros:", len(registros))
    print("Archivo:", RUTA_SALIDA)


def validar_registros(registros, estudiantes):
    assert len(registros) == 1440

    matriculas = {}

    for r in registros:
        carrera = r["career_id"]
        anterior = matriculas.get(carrera, 0)

        esperado = (
            anterior
            + r["new_enrollments"]
            - r["dropouts"]
            - r["graduates"]
        )

        assert r["total_enrollment"] == esperado
        assert r["total_enrollment"] <= r["capacity"]
        assert r["scholarships"] <= r["total_enrollment"]
        assert r["new_enrollments"] <= r["admitted"]
        assert r["admitted"] <= r["applications"]

        matriculas[carrera] = r["total_enrollment"]

    total_ingresos = sum(
        r["new_enrollments"] for r in registros
    )

    total_activos = sum(matriculas.values())

    total_bajas = sum(
        r["dropouts"] for r in registros
    )

    total_graduados = sum(
        r["graduates"] for r in registros
    )

    assert total_ingresos == len(estudiantes)

    assert total_activos == sum(
        e["estado"] == "Activo"
        for e in estudiantes
    )

    assert total_bajas == sum(
        e["estado"] == "Desertor"
        for e in estudiantes
    )

    assert total_graduados == sum(
        e["estado"] == "Graduado"
        for e in estudiantes
    )

    print("Validaciones correctas")
    print("Ingresos historicos:", total_ingresos)
    print("Matricula final:", total_activos)
    print("Total de bajas:", total_bajas)
    print("Total de graduados:", total_graduados)


if __name__ == "__main__":
    generar_dataset()
