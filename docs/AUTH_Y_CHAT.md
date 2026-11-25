# Autenticación, roles y flujo del chat (base común)

Esta base es idéntica en `services/mcp-estudiantes` y `services/mcp-admin`. Cada subequipo
la extiende en su rama agregando sus propias herramientas MCP.

## Flujo

```
Navegador ── login (Supabase Auth) ──► JWT
Navegador ── POST /chat + "Authorization: Bearer <JWT>" ──► FastAPI
FastAPI   ── valida el JWT, carga/crea el perfil (rol, plan) en Postgres
FastAPI   ── cliente MCP ► /mcp (mismo servicio, reenvía el JWT) ► list_tools
FastAPI   ── Claude recibe las herramientas; si pide una, call_tool ► resultado ► Claude
FastAPI   ── respuesta final de texto al navegador
```

Cada herramienta MCP vuelve a validar el JWT por su cuenta (`app/tools/account.py`), así que
una herramienta nunca confía en el chat ni recibe un `user_id` como parámetro.

## Roles y plan

- Los perfiles viven en la tabla `profiles` (BD 1). El primer login crea el perfil con
  `role = user` y `plan = free`.
- El rol y el plan se leen de la base, **no** del token.
- Para volver admin a alguien: `UPDATE profiles SET role = 'admin' WHERE email = '...';`
- `require_role("admin")` protege rutas; ejemplo en `GET /admin/ping`.

## Herramientas MCP incluidas (comunes)

| Herramienta | Entradas | Salida | Permiso | Errores |
|---|---|---|---|---|
| `ping` | — | texto | público | — |
| `get_user_profile` | — | `user_id`, `email`, `role`, `plan` | usuario autenticado | token ausente/inválido |
| `get_subscription_status` | — | `plan`, `subscription_status` | usuario autenticado | token ausente/inválido |

Falta la tercera herramienta del avance 2 (consulta al dataset de cada proyecto) y las del avance 3.

## Variables de entorno nuevas

Backend: `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (opcional),
`MCP_INTERNAL_URL` (opcional). Frontend: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`NEXT_PUBLIC_API_URL`.

- Si el proyecto de Supabase firma con HS256, definir `SUPABASE_JWT_SECRET`.
- Si firma con claves asimétricas (ES256/RS256), basta `SUPABASE_URL`: se usa el JWKS público.

## Cómo probar

```bash
cd services/mcp-estudiantes        # o mcp-admin
pip install -r requirements-dev.txt
pytest                             # usa SQLite temporal; no necesita Docker ni claves reales
```

Las pruebas cubren: token ausente, inválido y expirado (401), creación del perfil en el primer login,
rutas por rol (403/200), descubrimiento de herramientas MCP, herramientas con y sin token,
validación de entradas del chat y el ciclo completo del chat con un Claude simulado.

Migraciones (con Postgres arriba):

```bash
alembic upgrade head
alembic check        # confirma que los modelos y la migración coinciden
```

## Pendiente

- Probar el flujo real con las claves de Supabase y de Claude (las pruebas usan un Claude simulado).
- Stripe: Checkout + webhook que actualice `subscriptions` y el `plan` del perfil.
- Seed del dataset de Kaggle y la herramienta de consulta (tercera herramienta MCP).
- Respuesta del chat en streaming (hoy devuelve el texto completo).
