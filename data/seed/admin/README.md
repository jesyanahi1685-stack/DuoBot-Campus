# Dataset Administrativo

`generate_admin.py` genera **1,440 registros sintéticos** a partir del [catálogo de carreras](../shared/carreras.json) y `data/raw/estudiantes.csv`. Hay una fila por carrera y mes entre enero de 2014 y diciembre de 2025. La semilla aleatoria es `43`. El generador de Estudiantes se ejecuta primero. La [muestra](administrativo.sample.csv) contiene 20 filas originales y las dos anomalías financieras. El [procedimiento común](../README.md#reproducir-desde-una-copia-nueva) incluye la generación, la carga y las pruebas.

## Columnas

Los tipos corresponden a los documentos de MongoDB. El CSV se escribe con encabezados y valores en texto.

| Columna | Tipo | Significado |
| --- | --- | --- |
| `record_id` | Entero | Identificador estable entre `1` y `1440`. El seed lo reutiliza como `_id`. |
| `career_id` | Texto | Código de carrera de `01` a `10`. |
| `career` | Texto | Nombre de la carrera en el catálogo compartido. |
| `year` | Entero | Año calendario del indicador. |
| `month` | Entero | Mes del `1` al `12`. |
| `period` | Texto | Semestre calendario con formato `AAAA-1` o `AAAA-2`. |
| `applications` | Entero | Solicitudes de admisión simuladas en el mes. |
| `admitted` | Entero | Personas admitidas simuladas en el mes. |
| `new_enrollments` | Entero | Estudiantes cuyo ingreso ocurrió ese mes. |
| `total_enrollment` | Entero | Estudiantes activos al cierre del mes. |
| `dropouts` | Entero | Salidas del mes con estado `Desertor`. |
| `graduates` | Entero | Salidas del mes con estado `Graduado`. |
| `capacity` | Entero | Capacidad simulada de la carrera, 350 lugares. |
| `scholarships` | Entero | Estudiantes activos con beca al cierre del mes. |
| `teachers` | Entero | Docentes simulados para la carrera, con un mínimo de tres. |
| `budget_mxn` | `double` | Presupuesto mensual simulado en pesos mexicanos. |
| `expenses_mxn` | `double` | Gasto mensual simulado en pesos mexicanos. |

## Reglas de generación

- Los ingresos se cuentan por fecha de inscripción. Las bajas y los egresos se cuentan por fecha y estado de salida. El generador verifica que la matrícula de cada carrera sea igual a la matrícula del mes anterior más ingresos, menos bajas y egresos. La beca se cuenta únicamente entre los estudiantes activos al cierre.
- En meses con ingresos, las admisiones suman entre 1 y 15 casos a los ingresos. Las solicitudes suman entre 5 y 35 a las admisiones. En meses sin ingresos ambas valen cero. Los docentes corresponden al redondeo hacia arriba de un docente por 25 estudiantes, con mínimo de tres.
- El presupuesto mensual suma 25,000 MXN de base, 18,000 por docente y 350 por estudiante activo. El gasto ordinario equivale al 80–98 % del presupuesto. Las dos filas de abajo simulan un gasto del 145 %.

| Mes | Carrera | Presupuesto (MXN) | Gasto (MXN) |
| --- | --- | ---: | ---: |
| Octubre de 2019 | `03` · Ingeniería Industrial | 207,700 | 301,165 |
| Marzo de 2024 | `02` · Ingeniería Electrónica | 231,300 | 335,385 |

Los flujos históricos coinciden con Estudiantes y la matrícula de diciembre de 2025 es **1,713**. Los recursos, los presupuestos y las admisiones son simulaciones. Las anomalías se añadieron deliberadamente para probar consultas y análisis.

## Carga y consulta MCP

Desde la raíz, ejecuta `& $python data/seed/admin/seed_admin.py`. El destino predeterminado es `duobot_admin_analytics.admin_indicators` en localhost. `ADMIN_MONGO_URL` permite configurar la conexión. Una carga remota requiere `--permitir-remoto`. El seed valida la base, conserva el índice único de `record_id`, el índice compuesto único de `year`, `month` y `career_id`, y actualiza por `_id`. Consulta la [configuración local y remota](../README.md#configuración-de-mongodb-para-los-seeds).

`query_admin_indicators(year, month=None, career_id=None)` requiere un JWT válido y un perfil existente con rol `admin` en PostgreSQL. El mismo control se aplica en `/mcp` y en el chat. El año requerido va de 2014 a 2025. El mes opcional va de 1 a 12 y la carrera es un código de dos caracteres. Omitir la carrera agrega las diez carreras.

```text
query_admin_indicators(year=2024, month=3, career_id="02")
query_admin_indicators(year=2025)
```

La consulta mensual devuelve `monthly`. La anual devuelve `accumulated` con los flujos y montos del año más `year_end` con los valores de diciembre para matrícula, becas activas, capacidad y docentes. **La matrícula anual es la matrícula del cierre de diciembre.** Con filas faltantes, el estado `partial` indica que los indicadores se calcularon con los datos disponibles y `missing` enumera los pares mes y carrera faltantes. Si diciembre está incompleto, `year_end` es `null`. Cuando el filtro carece de coincidencias, la herramienta devuelve `no_data`. El flujo de `/chat` se verificó con Claude simulado.
