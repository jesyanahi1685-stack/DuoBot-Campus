# mcp-estudiantes

Servicio FastAPI + servidor MCP de DuoBot Campus (Estudiantes).

```
app/
  main.py      # FastAPI + FastMCP (/health, /mcp)
  config.py    # variables de entorno
  auth.py      # validacion del JWT de Supabase
  db.py        # Postgres (SQLAlchemy) + MongoDB
  models/      # modelos SQLAlchemy (BD 1)
  tools/       # herramientas MCP (una por archivo)
alembic/       # migraciones
models_ml/     # modelos entrenados (joblib)
tests/
```

Migraciones: `alembic revision --autogenerate -m "mensaje"` y `alembic upgrade head`.
