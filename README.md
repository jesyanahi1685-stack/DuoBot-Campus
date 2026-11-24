<div align="center">

# DuoBot Campus

### Dos asistentes de IA que convierten los datos del campus en decisiones

Un chatbot para analizar a los **estudiantes** y otro para la **gestión administrativa**.  
Preguntas en lenguaje natural, respuestas con gráficas y modelos de machine learning.

<p>
  <img src="https://img.shields.io/badge/Estado-En%20desarrollo-0ea5e9?style=for-the-badge" alt="Estado: En desarrollo" />
  <img src="https://img.shields.io/badge/Materia-Prog.%20L%C3%B3gica%20y%20Funcional%20%C2%B7%20U4-1e293b?style=for-the-badge" alt="Programación Lógica y Funcional - Unidad 4" />
  <img src="https://img.shields.io/badge/Arquitectura-MCP%20%2B%20API-6366f1?style=for-the-badge" alt="Arquitectura MCP + API IA" />
</p>

<p>
  <a href="#qué-es">¿Qué es?</a> ·
  <a href="#cómo-funciona">Cómo funciona</a> ·
  <a href="#tecnologías">Tecnologías</a> ·
  <a href="#estado-del-proyecto">Estado</a> ·
  <a href="#equipo">Equipo</a> ·
  <a href="#enlaces">Enlaces</a>
</p>

</div>

---

## ¿Qué es?

**DuoBot Campus** es un proyecto integrador de *Programación Lógica y Funcional* (Unidad 4).  
Está conformado por **dos aplicaciones web independientes**, cada una con un chatbot como interfaz principal:

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>DuoBot Estudiantes</h3>
      <p><strong>Para quién:</strong> Personal académico y tutores</p>
      <p><strong>Qué responde:</strong> Desempeño académico, riesgo de deserción y perfiles de estudiantes</p>
      <p><strong>Cómo responde:</strong> Consultas, gráficas y modelos de ML sobre datasets</p>
    </td>
    <td width="50%" valign="top">
      <h3>DuoBot Administrativo</h3>
      <p><strong>Para quién:</strong> Personal administrativo</p>
      <p><strong>Qué responde:</strong> Operación, recursos, matrícula e indicadores administrativos</p>
      <p><strong>Cómo responde:</strong> Consultas, gráficas y modelos de ML sobre datasets</p>
    </td>
  </tr>
</table>

> [!NOTE]
> El usuario escribe una pregunta en lenguaje natural; el chatbot decide qué herramienta usar y responde con datos reales y autorizados: una **tabla**, una **gráfica** o la **predicción de un modelo**.

---

## Cómo funciona

```mermaid
flowchart TD
    U(["Usuario"]) -->|"Pregunta en lenguaje natural"| FE["Chat Web<br/>Next.js · Vercel"]
    FE -->|"JWT de Supabase"| API["Servicio FastAPI + Servidor MCP<br/>Railway / Render"]
    API <-->|"Descubre e invoca herramientas MCP"| CLAUDE["Claude API"]

    subgraph DATA["Datos, modelos y visualizaciones"]
        direction LR
        PG[("PostgreSQL<br/>Cuentas y plan")]
        MG[("MongoDB<br/>Datos analíticos")]
        ML["Modelos ML y Gráficas<br/>scikit-learn · Plotly · Matplotlib"]
    end

    API --> PG
    API --> MG
    API --> ML
```

### Principios de arquitectura

- **MCP como punto central:** El modelo de IA descubre y llama herramientas que consultan el contexto de la aplicación, la cuenta del usuario autenticado y las dos bases de datos.
- **Permisos validados en el servidor:** Cada herramienta valida al usuario del lado del servidor; el chat nunca decide los permisos.
- **Plan gratuito y premium:** Gestión de planes con pagos en modo de prueba mediante Stripe.

---

## Tecnologías

| Capa | Herramientas |
| :--- | :--- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white) ![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) |
| **Backend e IA** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![MCP Python SDK](https://img.shields.io/badge/MCP%20%28SDK%20Python%29-1e293b?style=flat-square&logo=python&logoColor=white) <!-- ![Claude API](https://img.shields.io/badge/Claude%20API-191919?style=flat-square&logo=anthropic&logoColor=white) -->|
| **Bases de datos y ORM** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white) ![SQLAlchemy + Alembic](https://img.shields.io/badge/SQLAlchemy%20%2B%20Alembic-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white) |
| **Datos, ML y gráficas** | ![pandas](https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white) ![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white) ![Matplotlib](https://img.shields.io/badge/Matplotlib-11557C?style=flat-square) |
| **Auth y pagos** | ![Supabase Auth](https://img.shields.io/badge/Supabase%20Auth-3ECF8E?style=flat-square&logo=supabase&logoColor=white) ![Stripe](https://img.shields.io/badge/Stripe-635BFF?style=flat-square&logo=stripe&logoColor=white) |
| **Infraestructura** | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) ![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white) ![Render](https://img.shields.io/badge/Render-46E3B7?style=flat-square&logo=render&logoColor=black) |

---

## Estado del proyecto

![Progreso](https://img.shields.io/badge/Progreso-1%20%2F%206%20hitos-0ea5e9?style=flat-square)

- [x] Estructura base del monorepo
- [ ] Autenticación y roles
- [ ] Herramientas MCP (mínimo 6 por proyecto)
- [ ] Datasets y modelos de ML
- [ ] Pagos con Stripe (modo prueba)
- [ ] Despliegue en producción

---

## Equipo

| Integrante | Proyecto |
| :--- | :--- |
| _Jessika Diaz 23480898_ | DuoBot Estudiantes |
| _Yudel Gonzales 23481438_ | DuoBot Estudiantes |
| _Miranda Alvarez 23480831_ | DuoBot Administrativo |
| _Diego Mireles 23481455_ | DuoBot Administrativo |

---

## Enlaces

| Recurso | Acceso |
| :--- | :--- |
| **Demo Estudiantes** | estudiantes-theta.vercel.app |
| **Demo Administrativo** | admin-beta-tan-43.vercel.app |
| **Documentación técnica** | [`docs/README_TECNICO.md`](docs/README_TECNICO.md) |

> [!TIP]
> Para levantar el proyecto en local, consulta la [documentación técnica](docs/README_TECNICO.md).

---

<div align="center">
  <sub><a href="#duobot-campus">↑ Volver arriba</a></sub>
</div>
