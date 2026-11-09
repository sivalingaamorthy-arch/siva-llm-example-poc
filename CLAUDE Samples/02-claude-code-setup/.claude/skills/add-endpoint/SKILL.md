---
name: add-endpoint
description: Add a new REST endpoint to the health-content API following project conventions (router, response model, problem+json errors, tests). Use when the user asks to add, create or expose a new route or resource.
argument-hint: "<METHOD> <path> <one-line purpose>"
---

# Add an endpoint

Request: $ARGUMENTS

Follow these steps in order. Do not skip the test step.

1. **Clarify** the method, path, request/response shape and error cases. If any is
   unclear, ask one question before writing code.
2. **Model**: add request/response models to `src/health_api/models.py`.
   Use `Field(...)` constraints for validation rather than manual checks.
3. **Data**: if new data access is needed, add a method to `Repository`
   (`src/health_api/repository.py`). Routes never read files; canonical data comes via `sample_data.py`.
4. **Route**: add the handler to an existing router in `src/health_api/routes/`, or
   create a new router from [template.py](template.py) and register it in `main.py`.
   Errors only through `problem(status, slug, detail)`.
5. **Tests**: add tests in `tests/` for the happy path and **each** error slug,
   using the `client` fixture. See the conventions in `.claude/rules/tests.md`.
6. **Verify**: run `pytest -q` and `ruff check src tests`. Fix until green.
7. **Review**: delegate to the `api-reviewer` subagent and address its findings.
8. **Report** in 3 bullets: what changed, which files, how it was verified.
