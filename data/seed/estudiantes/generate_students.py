
import csv
import json
import random
from pathlib import Path
from datetime import date

random.seed(42)

BASE = Path(__file__).resolve().parents[2]
RUTA_CARRERAS = BASE / "seed" / "shared" / "carreras.json"
RUTA_SALIDA = BASE / "raw" / "estudiantes.csv"

TOTAL_ESTUDIANTES = 5000
FECHA_CORTE = date(2025, 12, 31)


def cargar_carreras():
    with open(RUTA_CARRERAS, encoding="utf-8") as archivo:
        return json.load(archivo)


def limitar(valor, minimo, maximo):
    return max(minimo, min(valor, maximo))


def sumar_meses(fecha, meses):
    total = fecha.year * 12 + fecha.month - 1 + meses
    return date(total // 12, total % 12 + 1, 1)


def generar_estudiante(student_id, carreras):
    carrera = random.choice(carreras)

    anio = random.randint(2014, 2025)
    mes = random.choice([2, 8])
    ingreso = date(anio, mes, 1)

    edad = random.randint(18, 25)
    promedio_anterior = limitar(random.gauss(80, 10), 40, 100)
    asistencia = limitar(random.gauss(85, 12), 30, 100)
    horas_estudio = random.randint(2, 25)

    promedio_actual = limitar(
        promedio_anterior
        + (asistencia - 80) * 0.20
        + (horas_estudio - 10) * 0.25
        + random.gauss(0, 7),
        40, 100
    )

    materias = random.randint(4, 7)

    prob_aprobar = limitar(
        (promedio_actual - 40) / 60,
        0.10, 0.98
    )

    aprobadas = sum(
        random.random() < prob_aprobar
        for _ in range(materias)
    )

    reprobadas = materias - aprobadas

    beca = random.choice([True, False])
    trabaja = random.choice([True, False])

    riesgo = limitar(
        0.10
        + (75 - promedio_actual) * 0.008
        + (80 - asistencia) * 0.005
        + reprobadas * 0.025,
        0.03, 0.75
    )

    if random.random() < riesgo:
        salida = sumar_meses(
            ingreso, random.choice([6, 12, 18, 24])
        )
        estado = "Desertor"
    else:
        salida = sumar_meses(ingreso, 54)
        estado = "Graduado"

    if salida > FECHA_CORTE:
        estado = "Activo"
        salida = None

    meses_cursados = (
        (FECHA_CORTE.year - ingreso.year) * 12
        + FECHA_CORTE.month - ingreso.month
    )

    semestre = limitar(meses_cursados // 6 + 1, 1, 9)

    if salida is not None:
        meses_cursados = (
            (salida.year - ingreso.year) * 12
            + salida.month - ingreso.month
        )
        semestre = limitar(meses_cursados // 6, 1, 9)

    return {
        "student_id": student_id,
        "career_id": carrera["career_id"],
        "career": carrera["career"],
        "age": edad,
        "semester": semestre,
        "enrollment_year": anio,
        "enrollment_date": ingreso.isoformat(),
        "exit_date": salida.isoformat() if salida else "",
        "previous_average": round(promedio_anterior, 2),
        "current_average": round(promedio_actual, 2),
        "attendance_rate": round(asistencia, 2),
        "subjects_enrolled": materias,
        "subjects_passed": aprobadas,
        "subjects_failed": reprobadas,
        "study_hours": horas_estudio,
        "scholarship": beca,
        "employment_status": trabaja,
        "academic_status": estado
    }


def generar_dataset():
    carreras = cargar_carreras()

    estudiantes = [
        generar_estudiante(100001 + i, carreras)
        for i in range(TOTAL_ESTUDIANTES)
    ]

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
            fieldnames=estudiantes[0].keys()
        )

        escritor.writeheader()
        escritor.writerows(estudiantes)

    print("Dataset generado correctamente")
    print("Total de estudiantes:", len(estudiantes))
    print("Archivo:", RUTA_SALIDA)


if __name__ == "__main__":
    generar_dataset()
