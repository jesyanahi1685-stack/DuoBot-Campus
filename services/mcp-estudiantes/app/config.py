from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion leida de variables de entorno (nunca valores en el codigo)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "DuoBot Campus - Estudiantes"
    database_url: str = "postgresql+psycopg://duobot:password@localhost:5432/duobot_estudiantes_app"
    mongo_url: str = "mongodb://localhost:27017/duobot_estudiantes_analytics"
    frontend_url: str = "http://localhost:3000"
    # Hosts permitidos por el MCP (separados por coma). En produccion agregar
    # el dominio de Railway/Render, p. ej. mi-servicio.up.railway.app
    mcp_allowed_hosts: str = "localhost:*,127.0.0.1:*"

    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    # Vacio = se calcula como http://127.0.0.1:$PORT/mcp (el chat se conecta a su propio MCP)
    mcp_internal_url: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""


settings = Settings()
