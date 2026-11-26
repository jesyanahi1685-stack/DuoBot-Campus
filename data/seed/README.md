# Datasets sintéticos de DuoBot Campus

Los generadores de este directorio crean datos simulados para practicar consultas y probar las herramientas MCP. El catálogo común [carreras.json](shared/carreras.json) define las diez carreras y sus códigos de texto de `01` a `10`. El CSV administrativo usa el CSV estudiantil para calcular ingresos, bajas, egresos, matrícula y becas. Genera Estudiantes primero y vuelve a generar Administrativo si el CSV estudiantil cambia.

| Dataset | Filas | Archivo local | MongoDB | Detalles |
| --- | ---: | --- | --- | --- |
| Estudiantes | 5,000 | `data/raw/estudiantes.csv` | `duobot_estudiantes_analytics.students` | [Diccionario y herramienta MCP](estudiantes/README.md) |
| Administrativo | 1,440 | `data/raw/administrativo.csv` | `duobot_admin_analytics.admin_indicators` | [Diccionario y herramienta MCP](admin/README.md) |

Las [muestras de Estudiantes](estudiantes/estudiantes.sample.csv) y [Administrativo](admin/administrativo.sample.csv) conservan el encabezado original y contienen 20 filas extraídas de cada CSV, dos por carrera y con años de 2014 a 2025. Estudiantes incluye los tres estados académicos y Administrativo incluye las dos anomalías financieras. Git excluye `data/raw/` y admite los archivos `*.sample.csv` en `data/seed/`. Los scripts de carga requieren los CSV completos.

## Reproducir desde una copia nueva

Abre la raíz del repositorio en PowerShell. Los Dockerfiles de los servicios usan Python 3.12. Para generar los CSV basta la biblioteca estándar. Para cargarlos necesitas PyMongo y MongoDB 7 local escuchando en el puerto `27017`. Si ya tienes MongoDB local, usa esa instancia. Si el puerto está libre y necesitas una instancia de desarrollo, puedes iniciarla así.

```powershell
docker run --detach --name duobot-campus-mongo-dev `
    --publish 127.0.0.1:27017:27017 `
    --mount type=volume,source=duobot-campus-mongo-dev,target=/data/db mongo:7
```

Crea el entorno virtual una vez. Si ya tienes `.venv` con el intérprete y PyMongo, reutilízalo. Puedes ejecutar su `python.exe` desde PowerShell sin activarlo.

```powershell
py -3.12 -m venv .venv
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
& $python -m pip install 'pymongo>=4.8'

& $python data/seed/estudiantes/generate_students.py
& $python data/seed/admin/generate_admin.py

# Quita las variables de esta sesión para usar el MongoDB local predeterminado.
Remove-Item Env:ESTUDIANTES_MONGO_URL, Env:ADMIN_MONGO_URL -ErrorAction SilentlyContinue
& $python data/seed/estudiantes/seed_students.py
& $python data/seed/admin/seed_admin.py
```

Ejecuta los generadores para preparar o actualizar los CSV completos. Si ya están generados y solo necesitas importarlos, ejecuta los dos seeds. Los seeds reemplazan por `_id` con `upsert=True` y conservan los índices. Al repetir la importación de los mismos CSV, los conteos deben seguir en 5,000 y 1,440. Despliega estos datos únicamente en las bases analíticas asignadas al proyecto. Cada importación reemplaza los documentos con los mismos `_id` y deja intactos los demás.

## Configuración de MongoDB para los seeds

| Variable de entorno | Base esperada |
| --- | --- |
| `ESTUDIANTES_MONGO_URL` | `duobot_estudiantes_analytics` |
| `ADMIN_MONGO_URL` | `duobot_admin_analytics` |

Sin la variable, cada seed usa `mongodb://localhost:27017` y su propia base. Con una URI configurada, toma el nombre del segmento de base de datos o usa el nombre esperado si se omite. Una base distinta devuelve un error antes de conectar. `authSource` identifica la base de autenticación de MongoDB. Para una conexión local personalizada, puedes usar las siguientes variables en tu sesión.

```powershell
$env:ESTUDIANTES_MONGO_URL = 'mongodb://127.0.0.1:27017/duobot_estudiantes_analytics'
$env:ADMIN_MONGO_URL = 'mongodb://127.0.0.1:27017/duobot_admin_analytics'
```

El seed considera local una URI estándar con un único host `localhost`, `127.0.0.1` o `[::1]` y fuerza conexión directa para evitar descubrir otros nodos. Una URI SRV, varios hosts o cualquier otro host requieren `--permitir-remoto` en la ejecución específica. Configura una URI remota solo después de verificar el destino y contar con autorización para cargarlo. Estos son formatos de referencia con un dominio ficticio.

```text
mongodb+srv://USUARIO:CLAVE@cluster.example.invalid/duobot_estudiantes_analytics
mongodb+srv://USUARIO:CLAVE@cluster.example.invalid/duobot_admin_analytics
```

Para una carga remota autorizada, captura la URI en la sesión sin escribirla en el comando. Ejecuta el bloque que corresponda al proyecto. Los scripts muestran el nombre de la base y el resultado de la carga. Las URI se suministran fuera del repositorio.

```powershell
$uri = Read-Host 'URI autorizada de Estudiantes' -AsSecureString
try {
    $env:ESTUDIANTES_MONGO_URL = [System.Net.NetworkCredential]::new('', $uri).Password
    & $python data/seed/estudiantes/seed_students.py --permitir-remoto
} finally {
    Remove-Item Env:ESTUDIANTES_MONGO_URL -ErrorAction SilentlyContinue
}

$uri = Read-Host 'URI autorizada de Administrativo' -AsSecureString
try {
    $env:ADMIN_MONGO_URL = [System.Net.NetworkCredential]::new('', $uri).Password
    & $python data/seed/admin/seed_admin.py --permitir-remoto
} finally {
    Remove-Item Env:ADMIN_MONGO_URL -ErrorAction SilentlyContinue
}
```

Las variables de arriba configuran la **importación**. Cada servicio MCP usa su propio `MONGO_URL`, con el nombre de su base analítica en la URI.

## Cifras de referencia

| Medida | Valor |
| --- | ---: |
| Estudiantes históricos | 5,000 |
| Filas administrativas | 1,440 |
| Estudiantes activos al cierre de diciembre de 2025 | 1,713 |
| Nuevos ingresos durante 2025 | 416 |
| Graduados históricos | 2,817 |
| Desertores históricos | 470 |
| Anomalías financieras simuladas | 2 |

La matrícula anual toma **el cierre de diciembre**. Las matrículas mensuales son conteos de personas activas en distintos cortes y su suma contaría a muchas de ellas más de una vez. Los ingresos, las bajas y los egresos sí se acumulan a lo largo del año. Estos datos tienen un corte fijo en 2025 y sirven para pruebas. Los indicadores y las relaciones simuladas carecen de validez como medición de un campus real.

## Reproducir las 57 pruebas de MCP

Desde la raíz, instala las dependencias declaradas de ambos servicios y las de pruebas si todavía faltan. Carga los CSV en MongoDB local antes de ejecutar el bloque de pruebas. La opción `DUOBOT_TEST_LOCAL_MONGO=1` activa dos pruebas de lectura contra `127.0.0.1:27017`. Los perfiles de prueba de Administrativo se guardan en SQLite temporal y el flujo del chat usa un Claude simulado.

```powershell
$python = (Resolve-Path '.venv/Scripts/python.exe').Path
& $python -m pip install -r services/mcp-admin/requirements-dev.txt `
    -r services/mcp-estudiantes/requirements.txt

powershell -NoProfile -Command {
    $repo = (Get-Location).Path
    $python = Join-Path $repo '.venv/Scripts/python.exe'
    $env:DATABASE_URL = 'sqlite://'
    $env:DUOBOT_TEST_LOCAL_MONGO = '1'
    $env:MCP_ALLOWED_HOSTS = 'localhost:*,127.0.0.1:*,testserver'
    $env:NO_PROXY = 'localhost,127.0.0.1'

    Set-Location -LiteralPath ([IO.Path]::GetTempPath())
    if (Test-Path -LiteralPath '.env') {
        throw 'Usa un directorio temporal sin .env'
    }

    foreach ($name in 'mcp-admin', 'mcp-estudiantes') {
        $service = Join-Path $repo "services/$name"
        $env:PYTHONPATH = $service
        & $python -B -m pytest -q -p no:cacheprovider --rootdir $service (Join-Path $service 'tests')
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
```

En Python 3.14.3 y Python 3.12.16 pasaron **35 pruebas de Administrativo y 22 de Estudiantes**, incluidas las dos lecturas contra MongoDB 7 local. Con `mcp==1.30.0` aparecieron 41 avisos de deprecación en Administrativo y 23 en Estudiantes. El chat administrativo y las pruebas invocan `streamablehttp_client`. El SDK indica migrar a `streamable_http_client`. El comando deja visibles los avisos.

## Compatibilidad de los servicios

Los servicios declaran `pymongo>=4.8` y `mcp>=1.9,<2`. Las herramientas MCP usan `_tool_manager`, una API interna de FastMCP, para aplicar `extra="forbid"` al modelo de entrada y al esquema publicado. Un cambio interno del SDK puede romper el registro o el rechazo de argumentos extra. Después de actualizar MCP, ejecuta las pruebas de descubrimiento y las de parámetros inválidos por HTTP. El límite declarado `mcp>=1.9` incluye versiones que carecen del `transport_security` que usan ambos servidores. La versión comprobada en las suites locales fue `mcp==1.30.0`. [Código de FastMCP 1.9.4](https://github.com/modelcontextprotocol/python-sdk/blob/v1.9.4/src/mcp/server/fastmcp/server.py)

Los módulos de los servicios y los seeds pasaron la validación de sintaxis de Python 3.12. Los metadatos de los paquetes usados en las suites, incluido `pymongo==4.20.2`, admiten Python 3.12 y sus versiones están dentro de los rangos del repositorio. El parser de URI que usan los seeds también está disponible en PyMongo 4.8. [Parser de PyMongo 4.8](https://github.com/mongodb/mongo-python-driver/blob/4.8.0/pymongo/uri_parser.py)

En un contenedor temporal `python:3.12-slim` se instalaron las dependencias declaradas de ambos servicios y de pruebas. `pip check` pasó con `mcp==1.30.0` y `pymongo==4.20.2`. Las suites se ejecutaron desde una copia de solo lectura con el código, los manifiestos y los datos sintéticos necesarios. Para las dependencias que faltaban en el entorno local también se revisaron los metadatos de las versiones mínimas. [Alembic](https://pypi.org/project/alembic/1.13.0/) · [Psycopg binario](https://pypi.org/project/psycopg-binary/3.2.0/) · [pandas](https://pypi.org/project/pandas/2.2.0/) · [scikit-learn](https://pypi.org/project/scikit-learn/1.5.0/) · [Matplotlib](https://pypi.org/project/matplotlib/3.9.0/) · [Plotly](https://pypi.org/project/plotly/5.24.0/) · [joblib](https://pypi.org/project/joblib/1.4.0/) · [Stripe](https://pypi.org/project/stripe/10.0.0/)
