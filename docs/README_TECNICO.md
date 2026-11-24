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

Verificación rápida:

- `http://localhost:8001/health` y `http://localhost:8002/health` → `{"status":"ok",...}`
- El endpoint MCP está en `http://localhost:800X/mcp` (herramienta de prueba: `ping`).
- Si ya existía el volumen de Postgres antes de crear `init.sql`, ejecutar
  `docker compose down -v` para recrearlo (borra los datos locales).

Pruebas del servicio: `cd services/mcp-estudiantes && pip install -r requirements.txt pytest httpx && pytest`

Migraciones: `alembic revision --autogenerate -m "mensaje"` y `alembic upgrade head`
dentro de cada servicio.

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

Responsables (llenar):

| Subequipo | Integrantes | Carpetas |
|---|---|---|
| Estudiantes | _Nombre 1, Nombre 2_ | `apps/estudiantes`, `services/mcp-estudiantes` |
| Administrativo | _Nombre 3, Nombre 4_ | `apps/admin`, `services/mcp-admin` |

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
