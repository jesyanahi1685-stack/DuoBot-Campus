# Dataset Estudiantes

`generate_students.py` crea **5,000 registros históricos sintéticos** con semilla aleatoria `42`. Usa el [catálogo compartido de carreras](../shared/carreras.json), genera ingresos entre 2014 y 2025 y fija el corte en el **31 de diciembre de 2025**. El CSV resultante alimenta al generador [Administrativo](../admin/README.md). La [muestra](estudiantes.sample.csv) incluye 20 filas originales de las diez carreras, con estudiantes activos, graduados y desertores. Los identificadores son simulados.

## Columnas

Los tipos corresponden a los documentos de MongoDB. El CSV se escribe con encabezados y valores en texto.

| Columna | Tipo | Significado |
| --- | --- | --- |
| `student_id` | Entero | Identificador sintético entre `100001` y `105000`. El seed lo reutiliza como `_id`. |
| `career_id` | Texto | Código de carrera de `01` a `10`. |
| `career` | Texto | Nombre de la carrera en el catálogo compartido. |
| `age` | Entero | Edad simulada entre 18 y 25 años. |
| `semester` | Entero | Semestre estimado entre 1 y 9 a la salida o al corte. |
| `enrollment_year` | Entero | Año de ingreso entre 2014 y 2025. |
| `enrollment_date` | Texto ISO `AAAA-MM-DD` | Fecha de ingreso, el 1 de febrero o el 1 de agosto. |
| `exit_date` | Texto ISO o `null` | Fecha de salida. Para estudiantes activos queda vacía en el CSV y se carga como `null`. |
| `previous_average` | `double` | Promedio previo simulado en escala de 40 a 100. |
| `current_average` | `double` | Promedio actual simulado en escala de 40 a 100. |
| `attendance_rate` | `double` | Asistencia simulada entre 30 y 100 en escala porcentual. |
| `subjects_enrolled` | Entero | Materias inscritas, entre 4 y 7. |
| `subjects_passed` | Entero | Materias aprobadas. |
| `subjects_failed` | Entero | Materias reprobadas. Corresponde a la diferencia entre inscritas y aprobadas. |
| `study_hours` | Entero | Horas de estudio simuladas, entre 2 y 25. |
| `scholarship` | Booleano | Indica si el registro simula una beca. |
| `employment_status` | Booleano | Indica si el registro simula que la persona trabaja. |
| `academic_status` | Texto | `Activo`, `Graduado` o `Desertor` al corte. |

## Reglas de generación

- La carrera y el ingreso se asignan al azar. El promedio actual depende del promedio previo, la asistencia, las horas de estudio y ruido aleatorio. El promedio actual influye en la probabilidad de aprobar materias.
- El promedio, la asistencia y las materias reprobadas influyen en el riesgo simulado de deserción. La deserción ocurre entre 6 y 24 meses después de ingresar. La graduación se programa a los 54 meses. Si la salida calculada queda después del corte, el estudiante se registra como activo y la fecha de salida queda vacía.
- El resultado al corte es de **1,713 activos, 2,817 graduados y 470 desertores**. Durante 2025 ingresaron **416 estudiantes**. Las reglas simplifican cohortes y trayectorias para ejercicios reproducibles. Sus distribuciones, correlaciones y resultados provienen del generador.

## Carga y consulta MCP

Desde la raíz, ejecuta `& $python data/seed/estudiantes/seed_students.py`. El destino predeterminado es `duobot_estudiantes_analytics.students` en localhost. `ESTUDIANTES_MONGO_URL` permite configurar la conexión. Una carga remota requiere `--permitir-remoto`. El seed actualiza por `_id` y conserva el índice único de `student_id` y los índices de `career_id` y `academic_status`. Consulta el [procedimiento común de generación y carga](../README.md).

`query_dataset_summary(career_id=None, enrollment_year=None)` requiere autenticación mediante un JWT válido. Admite como filtros el código de carrera y el año de ingreso de 2014 a 2025. Puedes usar cualquiera de los dos filtros, combinarlos u omitirlos para resumir el dataset completo.

```text
query_dataset_summary()
query_dataset_summary(career_id="10", enrollment_year=2025)
```

La herramienta devuelve `student_count`, `average_grade`, `average_attendance` y `as_of`. Una cohorte de uno a nueve estudiantes devuelve `suppressed`, con el umbral de 10 y sin conteo exacto ni promedios. Una cohorte vacía devuelve `no_data`. Cada promedio también necesita al menos diez valores numéricos para publicarse. La respuesta se limita a estadísticas agregadas y metadatos de la consulta.

La herramienta se verificó directamente en `/mcp` con JWT HS256 de prueba. El backend de Estudiantes aún necesita integrar las rutas de perfil y chat que espera el frontend. Su verificador actual admite HS256. Si el proyecto Supabase firma con claves asimétricas, la integración de autenticación requiere soporte JWKS en una tarea posterior.
