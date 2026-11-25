import os
import tempfile
import time

import jwt
import pytest

# Configuracion de prueba ANTES de importar la app (SQLite en un archivo temporal)
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-test-secret-test-secret-12345"
os.environ["MCP_ALLOWED_HOSTS"] = "127.0.0.1:*,localhost:*,testserver"

from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402

Base.metadata.create_all(engine)


@pytest.fixture
def make_token():
    def _make(sub="user-1", email="ana@campus.test", expires_in=3600):
        claims = {"sub": sub, "email": email, "aud": "authenticated", "exp": int(time.time()) + expires_in}
        return jwt.encode(claims, os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256")

    return _make
