FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Railway/Render inyectan $PORT; en local usa 8000.
# Con RUN_MIGRATIONS=1 aplica las migraciones de Alembic antes de arrancar (idempotente).
CMD ["sh", "-c", "if [ \"$RUN_MIGRATIONS\" = \"1\" ]; then python -m alembic upgrade head || exit 1; fi; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
