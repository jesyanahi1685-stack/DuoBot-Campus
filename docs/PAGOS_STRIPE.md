# Pagos con Stripe (modo de prueba)

Suscripción premium con **Stripe Checkout**, portal del cliente y **webhooks firmados**.
Funciona igual en `mcp-estudiantes` y `mcp-admin`. Todo se prueba en modo de prueba,
sin tarjetas reales.

## Cómo funciona

```
Usuario ── "Mejorar a Premium" ──► POST /billing/checkout (con su JWT)
Backend ── crea (o reutiliza) el Customer de Stripe y una Checkout Session en modo suscripción
Usuario ── paga en la página de Stripe ──► vuelve a /?checkout=success
Stripe  ── POST /billing/webhook (firmado) ──► el backend verifica la firma y actualiza
           la tabla subscriptions y el plan del perfil (free ⇄ premium)
```

- **El plan solo cambia por webhook.** Volver de Stripe (`?checkout=success`) no concede nada:
  la app consulta `/me` unos segundos hasta que el webhook llegue.
- `POST /billing/portal` abre el portal de Stripe para cancelar o cambiar la tarjeta.
- Una sola cuenta de Stripe sirve a los dos proyectos. Cada pago se marca con
  `metadata.project` y `metadata.user_id` (en la sesión **y** en la suscripción), y cada backend
  ignora los eventos de otro proyecto.

### Estados
| Estado de Stripe | Plan en la app |
|---|---|
| `active`, `trialing` | premium |
| `past_due`, `unpaid`, `incomplete`, `canceled` (o suscripción eliminada) | free |

Decisiones de diseño: el webhook guarda el estado completo (no sumas), por lo que una reentrega
del mismo evento es inofensiva; guarda la marca de tiempo del último evento aplicado y descarta
los más viejos (Stripe no garantiza el orden); la firma se verifica con el secreto del endpoint.

## Configuración (una vez)

1. En Stripe, con el **entorno de prueba** activo: crea los productos *DuoBot Estudiantes Premium*
   y *DuoBot Administrativo Premium*, cada uno con un precio **recurrente mensual**. Copia el ID de
   cada precio (`price_...`).
2. Copia la **clave secreta de prueba** (Desarrolladores → Claves de API).
3. Activa el **portal de clientes** en el entorno de prueba (Configuración → Facturación →
   Portal de clientes) y guarda la configuración.
4. Llena el `.env` (ver `.env.example`):

| Variable | Valor |
|---|---|
| `STRIPE_SECRET_KEY` | clave secreta de prueba (compartida) |
| `ESTUDIANTES_STRIPE_PRICE_ID_PREMIUM` | `price_...` del producto de Estudiantes |
| `ADMIN_STRIPE_PRICE_ID_PREMIUM` | `price_...` del producto de Administrativo |
| `ESTUDIANTES_STRIPE_WEBHOOK_SECRET` / `ADMIN_STRIPE_WEBHOOK_SECRET` | `whsec_...` (ver abajo) |

> Nunca subas estos valores a GitHub ni los pegues en el cliente. En el panel de Render/Railway
> de cada servicio las variables se llaman `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID_PREMIUM` y
> `STRIPE_WEBHOOK_SECRET` (sin prefijo).

## Probar en local

```powershell
# 1. Servicios (lee el .env)
docker compose up --build

# 2. Stripe CLI (una terminal por proyecto)
stripe login
stripe listen --forward-to localhost:8001/billing/webhook   # Estudiantes
stripe listen --forward-to localhost:8002/billing/webhook   # Administrativo
```

`stripe listen` imprime un secreto `whsec_...`: ponlo en `ESTUDIANTES_STRIPE_WEBHOOK_SECRET`
(o `ADMIN_...`) y reinicia el servicio. Después, desde la app: inicia sesión → **Mejorar a
Premium** → paga con una tarjeta de prueba.

| Tarjeta | Resultado |
|---|---|
| `4242 4242 4242 4242` | pago exitoso |
| `4000 0000 0000 0002` | tarjeta rechazada |
| `4000 0025 0000 3155` | pide autenticación 3D Secure |

(cualquier fecha futura, cualquier CVC y código postal). `stripe trigger` genera eventos de
ejemplo **sin** nuestros metadatos, así que se ignoran: prueba con el flujo real de la app.

## Producción (también en modo de prueba)

1. En Stripe → Desarrolladores → Webhooks, agrega un endpoint por servicio:
   `https://<backend>/billing/webhook` con los eventos `checkout.session.completed`,
   `customer.subscription.created`, `customer.subscription.updated` y
   `customer.subscription.deleted`.
2. Copia el secreto de firma de cada endpoint a `STRIPE_WEBHOOK_SECRET` de ese servicio.
3. Confirma que `FRONTEND_URL` del backend sea la URL de su frontend (la usan los redireccionamientos).

## Para operar con dinero real (no se hace en este proyecto)

Activar la cuenta de Stripe (verificación de identidad y de negocio), usar las claves y productos
de **modo real** (los objetos de prueba no existen en modo real), crear un webhook real con su
propio secreto, configurar el portal de clientes en modo real, y publicar términos y política de
privacidad. Revisar impuestos y facturación según el caso.

## Pruebas automáticas

`pytest` en cada servicio (`tests/test_billing.py`): checkout, portal, firma válida e inválida,
eventos de otro proyecto, orden y duplicados de eventos, y que volver de Checkout no concede premium.
Stripe se simula en esas pruebas; la verificación de la firma del webhook es real.

## Evidencia para la entrega (requisitos 7 y 11)

- Captura de los productos y precios en Stripe (modo de prueba).
- Captura de la página de pago de Stripe y del pago con `4242…`.
- Captura de los eventos entregados al webhook (respuesta 200) en Stripe.
- Captura de la app mostrando el cambio de plan Gratuito → Premium.
- Captura del pago rechazado (`4000 0000 0000 0002`) sin cambio de plan.
- Salida de `pytest`.
