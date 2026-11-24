<div align="center">

# DuoBot Campus

**Dos asistentes de IA que convierten los datos del campus en decisiones.**

Un chatbot para analizar a los **estudiantes** y otro para la **gestión administrativa**.
Preguntas en lenguaje natural, respuestas con gráficas y modelos de machine learning.

</div>

---

## ¿Qué es?

DuoBot Campus es un proyecto integrador de *Programación Lógica y Funcional* (Unidad 4).
Son **dos aplicaciones web** independientes, cada una con un chatbot como interfaz principal:

| | DuoBot Estudiantes | DuoBot Administrativo |
|---|---|---|
| **Para quién** | Personal académico y tutores | Personal administrativo |
| **Qué responde** | Desempeño, riesgo de deserción, perfiles de estudiantes | Operación, recursos, matrícula, indicadores administrativos |
| **Cómo** | Consultas, gráficas y modelos de ML sobre datasets | Consultas, gráficas y modelos de ML sobre datasets |

El usuario escribe una pregunta, el chatbot decide qué herramienta usar y responde con datos reales
y autorizados: una tabla, una gráfica o la predicción de un modelo.

## Cómo funciona

```
Usuario ──► Chat (Next.js, Vercel)
                │  JWT de Supabase
                ▼
        Servicio FastAPI + servidor MCP (Railway / Render)
          │            │              │
          ▼            ▼              ▼
     Postgres      MongoDB      Modelos ML (scikit-learn)
   (cuentas, plan)  (datos       + gráficas (plotly / matplotlib)
                    analíticos)
                │
                ▼
          Claude (API) descubre e invoca las herramientas MCP
```

- **MCP** es el punto central: el modelo de IA descubre y llama herramientas que consultan el contexto
  de la aplicación, la cuenta del usuario autenticado y las dos bases de datos.
- **Cada herramienta valida al usuario en el servidor**; el chat nunca decide los permisos.
- **Plan gratuito y premium** con pagos en modo de prueba mediante Stripe.

## Tecnologías

Next.js · Tailwind CSS · FastAPI · MCP (SDK oficial de Python) · PostgreSQL · MongoDB ·
SQLAlchemy + Alembic · pandas · scikit-learn · Supabase Auth · Stripe · Docker · Vercel · Railway

## Estado del proyecto

- [x] Estructura base del monorepo
- [ ] Autenticación y roles
- [ ] Herramientas MCP (mínimo 6 por proyecto)
- [ ] Datasets y modelos de ML
- [ ] Pagos con Stripe (modo prueba)
- [ ] Despliegue en producción

## Equipo

| Integrante | Proyecto |
|---|---|
| _Nombre 1_ | Estudiantes |
| _Nombre 2_ | Estudiantes |
| _Nombre 3_ | Administrativo |
| _Nombre 4_ | Administrativo |

## Enlaces

- Demo Estudiantes: _pendiente_
- Demo Administrativo: _pendiente_
- Documentación técnica: [`docs/README_TECNICO.md`](docs/README_TECNICO.md)

---

Para levantar el proyecto en local, ver la [documentación técnica](docs/README_TECNICO.md).
