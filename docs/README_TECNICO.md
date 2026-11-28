# DuoBot Campus · Documentación técnica (interna)

Guía para el equipo: cómo levantar el proyecto, qué stack usamos y cómo nos dividimos el trabajo.
Esta versión es un esqueleto: se amplía conforme avanzan los entregables.

## 1. Estructura del monorepo

```
apps/
  estudiantes/        Next.js  (Vercel, proyecto 1, puerto local 3000)
  admin/              Next.js  (Vercel, proyecto 2, puerto local 3001)
services/
  mcp-estudiantes/    FastAPI + MCP + ML  (Railway/Render, puerto local 8001)
  mcp-admin/          FastAPI + MCP + ML  (Railway/Render, puerto local 8002)
packages/shared/      código común (vacío por ahora)
data/seed/            scripts de datos (sin CSV pesados)
infra/postgres/       inicialización de Postgres local
docs/                 documentación
docker-compose.yml    entorno de desarrollo
```

## 2. Stack

| Capa | Tecnología | Notas |
|---|---|---|
| Frontend | Next.js 15 + Tailwind | Solo interfaz de chat; desplegado en Vercel (`.vercel.app`) |
| Backend | FastAPI + MCP (`mcp>=1.9,<2`) | Transporte HTTP streamable en `/mcp` |
| ML y gráficas | pandas, scikit-learn, plotly, matplotlib, joblib | Modelos entrenados offline; el servicio solo hace inferencia |
| BD 1 | PostgreSQL + SQLAlchemy 2 + Alembic | Usuarios, roles, suscripciones, historial |
| BD 2 | MongoDB (provisional) | Datos analíticos y resultados de modelos |
| Auth | Supabase Auth | Solo login; roles y plan viven en nuestra BD 1 |
| Pagos | Stripe (modo prueba) | Checkout + webhooks |
| LLM | API de Claude | Invoca las herramientas MCP |
| Contenedores | Docker | Solo desarrollo local y backend |

> **Nota sobre `mcp`:** está fijado a `<2` porque la versión 2 renombró `FastMCP`. Si se actualiza,
> hay que migrar el código.

## 3. Levantar en local

Requisitos: Docker Desktop, Node 20+ y (opcional) Python 3.12 para correr pruebas fuera de Docker.

```bash
# 1. Variables de entorno
cp .env.example .env            # llenar POSTGRES_PASSWORD como mínimo
cp apps/estudiantes/.env.example apps/estudiantes/.env.local
cp apps/admin/.env.example apps/admin/.env.local

# 2. Bases y servicios (Postgres, MongoDB, ambos servicios MCP)
docker compose up --build

# 3. Frontends (en terminales aparte)
cd apps/estudiantes && npm install && npm run dev    # http://localhost:3000
cd apps/admin       && npm install && npm run dev    # http://localhost:3001
```

Ejecuta el bloque de PowerShell desde la raíz del repositorio.

```powershell
# 1. Variables de entorno
Copy-Item .env.example .env # llenar POSTGRES_PASSWORD como mínimo
Copy-Item apps/estudiantes/.env.example apps/estudiantes/.env.local
Copy-Item apps/admin/.env.example apps/admin/.env.local

# 2. Bases y servicios
docker compose up --build

# 3. Estudiantes (en otra terminal, desde la raíz)
Set-Location apps/estudiantes
npm.cmd install
if ($LASTEXITCODE -eq 0) { npm.cmd run dev } # http://localhost:3000

# Administrativo (en otra terminal, desde la raíz)
Set-Location apps/admin
npm.cmd install
if ($LASTEXITCODE -eq 0) { npm.cmd run dev } # http://localhost:3001
```

Verificación rápida:

- `http://localhost:8001/health` y `http://localhost:8002/health` → `{"status":"ok",...}`
- El endpoint MCP está en `http://localhost:800X/mcp` (herramienta de prueba: `ping`).
- Si ya existía el volumen de Postgres antes de crear `init.sql`, ejecutar
  `docker compose down -v` para recrearlo (borra los datos locales).

Para probar cada servicio, ejecuta estos comandos desde `services/mcp-estudiantes` y desde
`services/mcp-admin`.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Los mismos comandos funcionan en PowerShell.

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Migraciones: `alembic revision --autogenerate -m "mensaje"` y `alembic upgrade head`
dentro de cada servicio.

CI ejecuta las pruebas de cada servicio con Python 3.12 y verifica sus migraciones sobre
SQLite. Para reproducir la verificación, usa una base local nueva y temporal.

```bash
export DATABASE_URL=sqlite:///./ci.db
python -m alembic upgrade head
python -m alembic check
```

En PowerShell, ejecuta el siguiente bloque desde el directorio de cada servicio.

```powershell
$env:DATABASE_URL = 'sqlite:///./ci.db'
python -m alembic upgrade head
python -m alembic check
```

CI también compila ambos frontends con Node 22, `npm install` y `npm run build`, con las
variables `NEXT_PUBLIC_*` de configuración vacías. Desde la raíz, ejecuta
`python scripts/check_common.py` para detectar archivos faltantes o diferencias en las
copias del código común y sus migraciones. La comparación omite las asignaciones de
`PROJECT` y normaliza los nombres visibles de DuoBot. Cada diferencia se informa por
archivo y el comando devuelve un código de salida distinto de cero.

En PowerShell, usa `npm.cmd install` y `npm.cmd run build` para cada frontend.

## 4. Variables de entorno

Todas están listadas, sin valores, en `.env.example` y en el `.env.example` de cada app.
**Nunca** se sube `.env` ni se ponen secretos en variables `NEXT_PUBLIC_*` (son visibles en el navegador).

## 5. Seguridad (reglas del equipo)

- Cada herramienta MCP valida el JWT de Supabase (`app/auth.py`) y filtra por `user_id` y rol.
- Herramientas **fijas y parametrizadas**; nunca una que ejecute código generado por el LLM.
- Validar entradas (Pydantic), manejar errores sin filtrar detalles internos, HTTPS en producción.
- Permisos mínimos: las herramientas solo leen lo necesario; las sensibles requieren rol o plan.
- En producción, configurar `MCP_ALLOWED_HOSTS` con el dominio del servicio.

## 6. Cómo nos dividimos el trabajo

Dos subequipos de dos personas, un solo repositorio.

```
main                       ← base común, protegida (solo por Pull Request)
 ├─ equipo-estudiantes     ← rama larga: app + servicio MCP + ML de Estudiantes
 └─ equipo-admin           ← rama larga: app + servicio MCP + ML de Administrativo
```

- **`main`** contiene solo lo común: estructura, Docker, documentación, auth base y modelos base.
- Cada subequipo trabaja **todo su proyecto** (interfaz, MCP y modelos) en su rama de equipo, en ramas cortas:
  `equipo-estudiantes` → `est/feature-nombre` → PR a `equipo-estudiantes`.
- Al terminar cada hito, la rama de equipo se une a `main` con Pull Request y revisión del otro subequipo.
- Cambios en carpetas comunes (`packages/`, `infra/`, `docs/`, `docker-compose.yml`): PR directo a `main`
  y avisar a todos.
- Cada subequipo toca solo su `apps/<proyecto>` y `services/mcp-<proyecto>`, así que los conflictos son mínimos.
- Commits pequeños y con mensajes claros: el historial es parte de la evaluación.

Responsables

| Subequipo | Integrantes | Carpetas |
|---|---|---|
| Estudiantes | Jessika Diaz, Yudel Gonzales | `apps/estudiantes`, `services/mcp-estudiantes` |
| Administrativo | Miranda Alvarez, Diego Mireles | `apps/admin`, `services/mcp-admin` |

## 7. Despliegue (plan)

| Pieza | Plataforma | Configuración |
|---|---|---|
| Frontends | Vercel | 2 proyectos, Root Directory `apps/estudiantes` y `apps/admin` |
| Servicios MCP | Railway (alternativa: Render) | 2 servicios, Root Directory `services/mcp-<proyecto>`, detecta el Dockerfile |
| Postgres / MongoDB | Neon o Supabase / MongoDB Atlas | Por definir |
| Auth | Supabase | Solo autenticación |

Pendiente de definir al desplegar: variables en cada plataforma, `FRONTEND_URL` y
`MCP_ALLOWED_HOSTS` de cada servicio, CORS.

## 8. Herramientas MCP (plantilla a llenar)

Mínimo 3 en el avance 2 y 6 en el avance 3, por proyecto. Documentar cada una:

| Herramienta | Entradas | Salida | Permiso (rol/plan) | Errores | Base que consulta |
|---|---|---|---|---|---|
| `ping` | — | texto | público | — | — |
| _por definir_ | | | | | |

## 9. Decisiones pendientes

- [ ] Confirmar con el profesor que el monorepo es aceptable y qué rama se revisa.
- [ ] Revisar el TXT de evaluación (fechas, evidencias, formato de correo).
- [ ] Motor definitivo de la BD 2 (MongoDB, DuckDB u otro Postgres).
- [ ] Railway o Render para los servicios.
- [ ] Datasets de Kaggle de cada proyecto.
- [ ] Herramientas MCP gratuitas vs. premium.
- [ ] Neon o Supabase para el Postgres de producción.

## 10. Lista para la documentación final (requisito 9)

Objetivo · integrantes · arquitectura y diagrama · las dos bases (propósito, estructura, relaciones,
acceso) · instalación · variables de entorno · ejecución · despliegue · herramientas MCP · roles ·
pagos · pruebas · limitaciones · enlaces.

## 11. Prueba de humo de Estudiantes y Administrativo

Usa un entorno de desarrollo con las migraciones aplicadas y los
[datasets sintéticos cargados](../data/seed/README.md). En el `.env` local de ambos
servicios, usa un `SUPABASE_JWT_SECRET` exclusivamente de prueba y un valor
ficticio no vacío en `STRIPE_SECRET_KEY`. Prepara una identidad de prueba con
plan `free` y sin fila en `subscriptions`. En Administrativo, crea el perfil
con rol `admin` en su base de datos de desarrollo. Por ejemplo, para la base
local predeterminada de Docker Compose y una identidad nueva:

```bash
docker compose exec -T postgres psql -U duobot -d duobot_admin_app -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO profiles (user_id, email, role, plan)
VALUES ('smoke-local', 'smoke-local@campus.test', 'admin', 'free');
SQL
```

En PowerShell, pasa el SQL a `psql` por la entrada estándar.

```powershell
@'
INSERT INTO profiles (user_id, email, role, plan)
VALUES ('smoke-local', 'smoke-local@campus.test', 'admin', 'free');
'@ | docker compose exec -T postgres psql -U duobot -d duobot_admin_app -v ON_ERROR_STOP=1
```

En Estudiantes, `GET /me` crea esa identidad con el rol `user` la primera vez.
Desde la raíz, activa el entorno Python con las dependencias de un servicio
(`python -m pip install -r services/mcp-estudiantes/requirements-dev.txt`).
Exporta en tu terminal el mismo `SUPABASE_JWT_SECRET` sintético del servicio
y genera un JWT de corta duración sin mostrarlo.

```bash
TOKEN=$(python -c 'import os, time, jwt; print(jwt.encode({"sub": "smoke-local", "email": "smoke-local@campus.test", "aud": "authenticated", "exp": int(time.time()) + 900}, os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"))')
FECHA=$(date +%Y%m%d)
python scripts/smoke_test.py --base-url http://localhost:8001 --token "$TOKEN" \
  --out "docs/evidencia/smoke_${FECHA}_estudiantes.txt" --skip-chat
python scripts/smoke_test.py --base-url http://localhost:8002 --token "$TOKEN" \
  --out "docs/evidencia/smoke_${FECHA}_admin.txt" --skip-chat
```

En PowerShell, sustituye el ejemplo por el mismo secreto sintético configurado
en los servicios locales. El JWT se guarda en una variable de la sesión.

```powershell
$env:SUPABASE_JWT_SECRET = 'secreto-sintetico-solo-local-32-bytes'
$smokeToken = @'
import os
import time
import jwt

claims = {
    "sub": "smoke-local",
    "email": "smoke-local@campus.test",
    "aud": "authenticated",
    "exp": int(time.time()) + 900,
}
print(jwt.encode(claims, os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256"))
'@ | python -
if ($LASTEXITCODE -ne 0 -or -not $smokeToken) {
  throw 'No se pudo generar el JWT de prueba'
}

$smokeDate = Get-Date -Format 'yyyyMMdd'
$studentSmokeArgs = @(
  '--base-url', 'http://localhost:8001',
  '--token', $smokeToken,
  '--out', "docs/evidencia/smoke_${smokeDate}_estudiantes.txt",
  '--skip-chat'
)
$adminSmokeArgs = @(
  '--base-url', 'http://localhost:8002',
  '--token', $smokeToken,
  '--out', "docs/evidencia/smoke_${smokeDate}_admin.txt",
  '--skip-chat'
)
python scripts/smoke_test.py @studentSmokeArgs
python scripts/smoke_test.py @adminSmokeArgs
Remove-Variable smokeToken, studentSmokeArgs, adminSmokeArgs
```

Quita `--skip-chat` para probar `POST /chat` con Claude configurado o simulado
en el servidor de desarrollo. La prueba comprueba salud, rol y plan, las
herramientas MCP de cuenta y datos, y el HTTP 404 de `POST /billing/portal`
para el perfil sin cliente Stripe. El portal usa POST, de acuerdo con la ruta
de ambos servicios. Ejecuta la prueba solo contra un servidor de desarrollo
con una clave Stripe ficticia y una identidad nueva sin fila de suscripción.
Un perfil `free` e `inactive` puede conservar un cliente Stripe previo.
La consola y el reporte muestran `OK`, `FALLO` u `OMITIDO` por
comprobación. Un fallo devuelve código de salida 1. Sin `--out`, el reporte
se guarda en `docs/evidencia/smoke_YYYYMMDD.txt`. Usa un `--out` diferente por
servicio para conservar ambos reportes en la misma fecha.
