"""Comprueba que las copias del código común de ambos servicios coincidan."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES = ("mcp-estudiantes", "mcp-admin")
COMMON_FILES = (
    "app/auth.py",
    "app/chat.py",
    "app/billing.py",
    "app/stripe_client.py",
    "app/db.py",
    "app/tools/account.py",
    "app/models/base.py",
    "requirements.txt",
    "requirements-dev.txt",
    "Dockerfile",
    "pytest.ini",
    "alembic.ini",
    "alembic/env.py",
)
COMMON_GLOBS = ("alembic/versions/*", "requirements*.txt", "tests/*.py")
# Cada herramienta de datos tiene un contrato y pruebas propios de su servicio.
PROJECT_TESTS = {
    "mcp-estudiantes": Path("tests/test_dataset_summary.py"),
    "mcp-admin": Path("tests/test_admin_indicators.py"),
}
PROJECT_ASSIGNMENT = re.compile(r"^PROJECT\s*=.*$")
PROJECT_NAME = re.compile(r"\bDuoBot (?:Estudiantes|Administrativo)\b")


def normalized_content(path: Path) -> list[str]:
    return [
        PROJECT_NAME.sub("DuoBot <proyecto>", line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if not PROJECT_ASSIGNMENT.fullmatch(line)
    ]


def main() -> int:
    estudiantes, admin = (ROOT / "services" / service for service in SERVICES)
    common_paths = {Path(name) for name in COMMON_FILES}
    for service in (estudiantes, admin):
        for pattern in COMMON_GLOBS:
            common_paths.update(
                path.relative_to(service)
                for path in service.glob(pattern)
                if path.is_file() and path.relative_to(service) != PROJECT_TESTS[service.name]
            )

    has_drift = False
    for relative_path in sorted(common_paths):
        left = estudiantes / relative_path
        right = admin / relative_path
        if not left.is_file() or not right.is_file():
            missing_services = ", ".join(
                path.relative_to(ROOT).as_posix()
                for path in (left, right)
                if not path.is_file()
            )
            print(f"{relative_path.as_posix()}: falta {missing_services}")
            has_drift = True
        elif normalized_content(left) != normalized_content(right):
            print(f"{relative_path.as_posix()}: difiere entre Estudiantes y Administrativo")
            has_drift = True

    if has_drift:
        return 1
    print("El código común coincide entre Estudiantes y Administrativo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
