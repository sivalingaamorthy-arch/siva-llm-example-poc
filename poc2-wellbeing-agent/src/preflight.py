import shutil
import subprocess
import sys

from openai import OpenAIError

from src.config import POC_ROOT, get_settings
from src.db import connect
from src.errors import PocError
from src.openai_service import create_client


def run_preflight() -> bool:
    settings = get_settings()
    checks: list[tuple[str, bool, str]] = [
        (
            "Python",
            sys.version_info >= (3, 12),
            f"Python {sys.version.split()[0]} (requires 3.12+).",
        )
    ]
    docker = shutil.which("docker")
    compose_ok = False
    if docker:
        try:
            proc = subprocess.run(
                [docker, "compose", "version"],
                cwd=POC_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            compose_ok = proc.returncode == 0
        except subprocess.TimeoutExpired:
            compose_ok = False
    checks.append(
        (
            "Docker Compose",
            compose_ok,
            "Available." if compose_ok else "Install/enable Docker Compose in this Codespace.",
        )
    )
    try:
        with connect(register_vector_type=False) as connection:
            extension = connection.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            ).fetchone()
        db_ok = extension is not None
        db_message = (
            f"POC2 database reachable; pgvector {extension[0]} enabled."
            if extension
            else "pgvector is not installed; run --setup-db."
        )
    except PocError as exc:
        db_ok, db_message = False, str(exc)
    checks.append(("PostgreSQL / pgvector", db_ok, db_message))
    if not settings.api_key:
        api_ok, api_message = False, "OPENAI_API_KEY is missing; add a Codespaces secret and restart."
    else:
        try:
            create_client(settings).models.list()
            api_ok = True
            api_message = "OpenAI authentication succeeded; configured model access is checked on use."
        except OpenAIError as exc:
            api_ok = False
            api_message = f"OpenAI API failed ({type(exc).__name__}); check key, access, internet, and billing."
    checks.append(("OpenAI API", api_ok, api_message))

    framework_checks = [
        ("LangChain", "langchain"),
        ("LangGraph", "langgraph"),
        ("Agno", "agno"),
    ]
    for label, module in framework_checks:
        try:
            __import__(module)
            available = True
            message = "Installed."
        except ImportError:
            available = False
            message = "Missing; install requirements.txt in the POC virtual environment."
        checks.append((label, available, message))
    for name, passed, message in checks:
        print(f"[{'OK' if passed else 'FAIL'}] {name}: {message}")
    return all(passed for _, passed, _ in checks)
