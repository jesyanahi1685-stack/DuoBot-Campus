# Despliegue: GitHub → Render (backends) + Vercel (frontends)

Guía para publicar DuoBot Campus con servicios gratuitos. Cada `git push` a `main` actualiza
Vercel y Render solos; no hay que subir nada a mano después de la configuración inicial.

```
GitHub (main) ──► Vercel   apps/estudiantes  → https://estudiantes-theta.vercel.app
              │            apps/admin        → https://admin-beta-tan-43.vercel.app
              └─► Render   duobot-estudiantes (Docker, services/mcp-estudiantes)
                           duobot-admin       (Docker, services/mcp-admin)
Los backends usan: Neon (Postgres), MongoDB Atlas, Supabase (solo login), Stripe (pruebas), Claude (API).
```

## 0. Cuentas y orden de trabajo

| Servicio | Para qué | Plan |
|---|---|---|
| Neon | PostgreSQL (una base por proyecto) | gratuito |
| MongoDB Atlas | datos analíticos | M0 gratuito |
| Render | los dos backends | Free |
| Vercel | los dos frontends | Hobby (ya creados) |
| Supabase | inicio de sesión | gratuito (ya creado) |
| Stripe | pagos de prueba | entorno de prueba |

Orden: **1** bases de datos → **2** Render → **3** Vercel → **4** Supabase → **5** Stripe → **6** datos y verificación.
Haz todas las pruebas con el entorno de prueba de Stripe y claves de prueba.

> **No uses el Postgres gratuito de Render:** solo permite uno por espacio de trabajo y caduca a los
> 30 días. Las dos apps tampoco pueden compartir una misma base: ambas usan las tablas `profiles` y
> `subscriptions` y se mezclarían los roles y planes.

## 1. Bases de datos

### 1.1 Neon (PostgreSQL)
1. Crea un proyecto (región de AWS en EE. UU. este, la misma zona que Render `virginia`).
2. Crea **dos bases**: `duobot_estudiantes_app` y `duobot_admin_app`.
3. Copia la cadena de conexión **directa** (sin `-pooler` en el host) de cada una y conviértela:

```
Neon entrega:     postgresql://USUARIO:CLAVE@ep-xxxx.us-east-1.aws.neon.tech/duobot_estudiantes_app?sslmode=require
El backend usa:   postgresql+psycopg://USUARIO:CLAVE@ep-xxxx.us-east-1.aws.neon.tech/duobot_estudiantes_app?sslmode=require
```
Solo cambia el inicio (`postgresql+psycopg://`). No hay que crear tablas: el backend las crea al
arrancar con `RUN_MIGRATIONS=1`.

### 1.2 MongoDB Atlas
1. Crea un clúster **M0** (misma zona, AWS us-east-1).
2. Database Access: crea un usuario con contraseña (evita caracteres especiales o codifícalos en la URL).
3. Network Access: permite `0.0.0.0/0`. Las IP de salida de Render gratuito cambian, así que no se
   puede fijar una sola. Es una limitación de seguridad que se documenta (ver sección 9).
4. Connect → Drivers: copia la URI `mongodb+srv://...` y **agrega el nombre de la base** antes de `?`:

```
mongodb+srv://USUARIO:CLAVE@cluster0.xxxxx.mongodb.net/duobot_estudiantes_analytics?retryWrites=true&w=majority
mongodb+srv://USUARIO:CLAVE@cluster0.xxxxx.mongodb.net/duobot_admin_analytics?retryWrites=true&w=majority
```
(Si no pones la base en la URI, el backend no sabe cuál usar.)

## 2. Render (backends)

`render.yaml` en la raíz define los dos servicios. Úsalo después de unir a `main` el PR que lo trae.

1. En [dashboard.render.com](https://dashboard.render.com): **New → Blueprint**.
2. Conecta tu cuenta de GitHub y autoriza el repositorio `DuoBot-Campus`. Elige la rama `main`.
3. Render lee `render.yaml`, muestra los dos servicios y **te pide los valores** de las variables
   marcadas como secretas. Llénalas en cada servicio:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | cadena de Neon de ese proyecto (sección 1.1) |
| `MONGO_URL` | URI de Atlas de ese proyecto (sección 1.2) |
| `SUPABASE_URL` | `https://TU-REF.supabase.co` (la misma en los dos) |
| `ANTHROPIC_API_KEY` | tu clave de Claude |
| `STRIPE_SECRET_KEY` | clave secreta de **prueba** de Stripe (la misma en los dos) |
| `STRIPE_PRICE_ID_PREMIUM` | `price_...` del producto de **ese** proyecto |
| `STRIPE_WEBHOOK_SECRET` | déjalo con un valor temporal (`pendiente`); se actualiza en el paso 5 |
| `MCP_ALLOWED_HOSTS` | `duobot-estudiantes.onrender.com,127.0.0.1:*,localhost:*` (o el del admin) |

   - **`MCP_ALLOWED_HOSTS` debe incluir `127.0.0.1:*`.** El chat se conecta a su propio servidor MCP por
     esa dirección; sin ella el chat falla aunque `/health` funcione.
   - El dominio real aparece en la página del servicio. Si el nombre ya estaba tomado, Render agrega un
     sufijo (por ejemplo `duobot-admin-x1y2.onrender.com`): en ese caso corrige `MCP_ALLOWED_HOSTS`.
4. Pulsa **Apply**. El primer despliegue construye la imagen (varios minutos).
5. Cuando termine, abre `https://<tu-servicio>.onrender.com/health`. Debe responder
   `{"status":"ok","service":"mcp-estudiantes"}` (o `mcp-admin`).
6. En **Logs** verás que Alembic aplicó las migraciones. Si aparece un error de base de datos,
   revisa el prefijo `postgresql+psycopg://` y `?sslmode=require`.

**Cómo se actualiza solo:** cada servicio tiene `autoDeployTrigger: checksPass`: Render redespliega
cuando entra un commit a `main` **y el CI de GitHub pasó**. Solo se reconstruye el servicio cuyo código cambió.

**Si el Blueprint da problemas**, crea cada servicio a mano (New → Web Service → mismo repositorio) con:
Language `Docker` · Region `Virginia` · Instance Type `Free` · Dockerfile Path
`./services/mcp-estudiantes/Dockerfile` · Docker Build Context Directory `./services/mcp-estudiantes`
(y `mcp-admin` para el otro) · Health Check Path `/health` · Auto-Deploy `After CI Checks Pass` ·
y las mismas variables de la tabla más `RUN_MIGRATIONS=1` y `FRONTEND_URL`.

### Límites del plan gratuito (afectan la demostración)
- El servicio **se duerme tras 15 minutos sin tráfico** y tarda cerca de un minuto en despertar. Antes de
  mostrarlo, abre `/health` de cada backend y espera la respuesta.
- Render da 750 horas gratuitas al mes para todos tus servicios. Un servicio dormido no gasta horas;
  si los mantienes despiertos las 24 horas con un pinger, dos servicios sumarían ~1,440 h y Render los
  suspendería. Usa un pinger solo durante la ventana de evaluación.
- El sistema de archivos es efímero (no guardamos archivos en disco, así que no afecta).

## 3. Vercel (frontends)

Los proyectos ya existen. Verifica en cada uno (**Settings**):

| Ajuste | Estudiantes | Administrativo |
|---|---|---|
| Root Directory | `apps/estudiantes` | `apps/admin` |
| Framework | Next.js | Next.js |
| Production Branch | `main` | `main` |

En **Settings → Environment Variables** (ámbito *Production*) de cada proyecto:

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://TU-REF.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clave **publishable** de Supabase (`sb_publishable_...`) |
| `NEXT_PUBLIC_API_URL` | `https://duobot-estudiantes.onrender.com` (o `https://duobot-admin.onrender.com`) |

Las variables `NEXT_PUBLIC_*` se **incorporan al compilar**: después de cambiarlas, ve a
Deployments → ⋯ → **Redeploy**. Sin la `/` final en las URLs.

**Con GitHub:** cada push a `main` crea un despliegue de producción; cada Pull Request, una vista previa.
Las vistas previas **no podrán usar el backend** (CORS solo permite el dominio de producción): para
revisar el flujo completo usa siempre el dominio de producción. En el plan Hobby, los despliegues de
commits de otras personas requieren que la dueña de la cuenta los apruebe.

## 4. Supabase

En **Authentication → URL Configuration**: Site URL = `https://estudiantes-theta.vercel.app`; en
Redirect URLs agrega `https://admin-beta-tan-43.vercel.app`, `http://localhost:3000` y `http://localhost:3001`.
Recuerda que "Confirm email" está desactivado para el demo (ver README).

## 5. Stripe (webhooks de prueba)

Con el **entorno de prueba** activo, en Desarrolladores → Webhooks crea **un endpoint por backend**:

| Proyecto | URL del endpoint |
|---|---|
| Estudiantes | `https://duobot-estudiantes.onrender.com/billing/webhook` |
| Administrativo | `https://duobot-admin.onrender.com/billing/webhook` |

Eventos: `checkout.session.completed`, `customer.subscription.created`,
`customer.subscription.updated`, `customer.subscription.deleted`. Cada endpoint genera su propio
secreto `whsec_...`: cópialo a `STRIPE_WEBHOOK_SECRET` del servicio **correspondiente** en Render
(Environment → guardar; el servicio se reinicia).

## 6. Datos y administrador

**MongoDB (una vez, desde tu computadora).** Sigue [`data/seed/README.md`](../data/seed/README.md):
genera los CSV y carga cada base con `--permitir-remoto`, pegando la URI de Atlas cuando el script
la pida (no queda en el historial). Debe terminar con 5,000 estudiantes y 1,440 filas administrativas.

**Cuenta de administrador.** Regístrate en cada app y, en el editor SQL de Neon de la base de ese
proyecto, ejecuta:

```sql
UPDATE profiles SET role = 'admin' WHERE email = 'tu-correo@ejemplo.com';
```
(Primero haz un inicio de sesión para que se cree el perfil.)

## 7. Verificación

1. `https://<backend>.onrender.com/health` responde `ok` en los dos.
2. Abre cada app, regístrate, inicia sesión: arriba debe verse tu correo, `rol: user` y `plan: free`.
3. En el chat pregunta algo del dataset y confirma que responde con datos.
4. **Mejorar a Premium** → paga con `4242 4242 4242 4242` → en Stripe el webhook debe mostrar `200` y la app pasar a **Premium**.
5. **Prueba de humo contra el despliegue.** Los backends validan tokens reales de Supabase, así que usa
   uno: inicia sesión en la app, abre las herramientas del navegador → Application → Local Storage y copia
   `access_token` de la entrada `sb-...-auth-token` (dura ~1 hora; no lo compartas ni lo subas).

```powershell
$token = Read-Host 'Pega el access_token' -AsSecureString
$plain = [System.Net.NetworkCredential]::new('', $token).Password
python scripts/smoke_test.py --base-url https://duobot-estudiantes.onrender.com --token $plain `
  --out docs/evidencia/smoke_$(Get-Date -Format yyyyMMdd)_estudiantes_render.txt
Remove-Variable plain, token
```
El reporte no incluye el token. La prueba del portal espera un perfil `free` sin suscripción previa.

## 8. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| El chat da error pero `/health` funciona | `MCP_ALLOWED_HOSTS` sin `127.0.0.1:*` | Agrégalo y guarda (reinicia) |
| El navegador muestra error de CORS | `FRONTEND_URL` no coincide con el dominio abierto (o vista previa de Vercel) | Usa el dominio de producción; sin `/` final |
| Login funciona, `/me` da 401 | `SUPABASE_URL` mal o falta en Render | Corrígela; debe ser la misma del frontend |
| La app dice "Falta configurar NEXT_PUBLIC_SUPABASE..." | Variables sin definir o sin redesplegar | Definirlas y **Redeploy** |
| El servicio no arranca, error de base | URL de Neon sin `+psycopg` o sin `sslmode=require` | Corrige `DATABASE_URL` |
| `query_*` falla o devuelve vacío | MongoDB sin datos, sin base en la URI o IP no permitida | Revisa `MONGO_URL`, Network Access y la carga de datos |
| El pago se completa pero el plan no cambia | Webhook mal configurado | Ver "Entregas" del endpoint en Stripe; revisa `STRIPE_WEBHOOK_SECRET` del servicio correcto |
| Todo tarda ~1 minuto la primera vez | Render despertando | Espera y reintenta; abre `/health` antes de la demo |

## 9. Limitaciones y operación real (para el README final)

- Render gratuito se duerme y puede reiniciarse en cualquier momento; Neon y Atlas gratuitos tienen límites de almacenamiento.
- Atlas permite acceso desde cualquier IP (`0.0.0.0/0`) porque Render gratuito no tiene IP fija. En producción: instancia de pago con IP estática o red privada.
- "Confirm email" de Supabase está desactivado para el demo; en producción se activa con SMTP propio.
- Stripe solo en modo de prueba. Para cobrar de verdad: activar la cuenta (verificación de identidad y negocio), usar claves, productos y webhooks de **modo real**, configurar el portal de clientes real y publicar términos y política de privacidad.
- Producción real: instancias de pago (sin dormir), copias de seguridad, monitoreo y rotación de claves.
