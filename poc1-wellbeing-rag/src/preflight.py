import shutil
import subprocess
import sys

from openai import OpenAIError

from src.config import POC_ROOT, get_settings
from src.db import connect
from src.errors import PocError
from src.openai_client import create_client


def run_preflight() -> bool:
    settings = get_settings()
    python_ok = sys.version_info >= (3, 12)
    results: list[tuple[str, bool, str]] = [
        (
            "Python",
            python_ok,
            f"Python {sys.version.split()[0]} detected."
            if python_ok
            else f"Python {sys.version.split()[0]} found; Python 3.12 or newer is required.",
        ),
    ]
    docker = shutil.which("docker")
    compose_ok = False
    if docker:
        try:
            completed = subprocess.run(
                [docker, "compose", "version"],
                cwd=POC_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            compose_ok = completed.returncode == 0
        except subprocess.TimeoutExpired:
            compose_ok = False
    results.append(
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
        database_ok = extension is not None
        database_message = (
            f"PostgreSQL reachable; pgvector {extension[0]} enabled."
            if extension
            else "PostgreSQL is reachable, but pgvector is not enabled. Run --setup-db."
        )
    except PocError as exc:
        database_ok = False
        database_message = str(exc)
    results.append(("PostgreSQL / pgvector", database_ok, database_message))

    if not settings.openai_api_key:
        api_ok = False
        api_message = (
            "OPENAI_API_KEY is missing. Add it as a Codespaces secret and restart."
        )
    else:
        try:
            create_client(settings).models.list()
            api_ok = True
            api_message = (
                "API authentication succeeded. Configured model access is checked "
                "when the first request is made."
            )
        except OpenAIError as exc:
            api_ok = False
            api_message = (
                f"OpenAI authentication/connectivity failed ({type(exc).__name__}); "
                "check the secret, internet access, and account status."
            )
    results.append(("OpenAI API", api_ok, api_message))

    print(f"Python {sys.version.split()[0]}")
    for label, passed, message in results:
        print(f"[{'OK' if passed else 'FAIL'}] {label}: {message}")
    return all(passed for _, passed, _ in results)
