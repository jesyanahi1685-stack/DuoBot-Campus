# Evidencia del avance 2

## Índice

| Evidencia | Alcance | Estado |
| --- | --- | --- |
| CI | Pruebas de servicios y compilación de ambas aplicaciones | Verificada en el [PR #5](https://github.com/jesyanahi1685-stack/DuoBot-Campus/pull/5/checks) |
| Prueba de humo | Estudiantes y Administrativo | Procedimiento en el [PR #6](https://github.com/jesyanahi1685-stack/DuoBot-Campus/pull/6). Se informó una ejecución local con Claude y MongoDB simulados. Los reportes temporales están pendientes de adjuntar. |
| Capturas de inicio de sesión, chat, Checkout y webhook | Estudiantes y Administrativo | Pendientes de adjuntar |

## Reproducción

1. Prepara las bases, aplica las migraciones, carga los datos sintéticos y abre las dos aplicaciones de desarrollo. [Configuración local](../README_TECNICO.md#3-levantar-en-local).
2. Inicia sesión y envía una consulta del dataset en cada chat. Usa una cuenta de prueba con rol `admin` para `query_admin_indicators`. Registra el nombre de la herramienta a partir de una traza cuando la interfaz solo muestre la respuesta. [Flujo de autenticación y chat](../AUTH_Y_CHAT.md#flujo).
3. Con un perfil gratuito, completa Stripe Checkout en modo de prueba. Comprueba en Stripe la entrega al endpoint del proyecto y confirma que la aplicación pasa a Premium tras procesar el webhook. [Prueba local de Stripe](../PAGOS_STRIPE.md#probar-en-local).
4. Ejecuta `scripts/smoke_test.py` por separado contra los puertos 8001 y 8002. Usa `--out` para guardar un reporte por proyecto. Si ejecutas con `--skip-chat`, indica que el chat se omitió. [Procedimiento y comandos](../README_TECNICO.md#11-prueba-de-humo-de-estudiantes-y-administrativo).

## Plantilla para adjuntar evidencia

Completa esta ficha por proyecto y ejecución. Sustituye los marcadores con observaciones reales y oculta tokens, secretos, correos y datos de pago antes de adjuntar archivos.

- **Proyecto y fecha** — `<Estudiantes o Administrativo>`, `<AAAA-MM-DD>`
- **Revisión y entorno** — `<commit o PR>`, `<local o entorno de prueba>`, `<servicios simulados, si aplica>`
- **Resultado observado** — `<resultado y cualquier comprobación omitida>`

| Evidencia | Nombre sugerido | Qué registrar |
| --- | --- | --- |
| Inicio de sesión | `login_<fecha>_<proyecto>.png` | Vista autenticada con el proyecto y el rol de la cuenta de prueba. |
| Chat con herramienta | `chat_<fecha>_<proyecto>.png` | Pregunta, respuesta y nombre de la herramienta. Incluye una referencia a la traza cuando haga falta. |
| Pago de prueba | `checkout_<fecha>_<proyecto>.png` | Checkout en modo de prueba y resultado observado. |
| Webhook | `webhook_<fecha>_<proyecto>.png` | Tipo de evento, código HTTP de entrega y referencia a la captura del plan resultante. |
| Prueba de humo | `smoke_<fecha>_<proyecto>.txt` y, opcionalmente, `smoke_<fecha>_<proyecto>.png` | Adjunta el reporte como evidencia principal y una captura de consola si está disponible. Registra `OK`, `FALLO` u `OMITIDO` por comprobación y anota cualquier simulación u omisión del chat en la ficha. |
