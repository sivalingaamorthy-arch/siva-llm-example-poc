# Health Content API

FastAPI service over the repo's shared synthetic health-content data
(`../../Sample-Data-Health-Content/sample-data`): serves the 33-article catalog and
stores report-based recommendations (R1, R2, R3) behind the shared safety rules.

## Commands
- Install: `pip install -e ".[dev]"`
- Test (run before saying a task is done): `pytest -q`
- Lint: `ruff check src tests`
- Run locally: `uvicorn health_api.main:app --reload`

## Architecture
- `src/health_api/routes/`: one router per resource. Routes are thin; no business logic beyond guard clauses.
- `src/health_api/repository.py`: the only module that touches data. Injected via `Depends(get_repository)`.
- `src/health_api/sample_data.py`: locates the canonical data (override: `HEALTH_CONTENT_SAMPLE_DATA`), derives report markers, owns the safety rules.
- `src/health_api/models.py`: Pydantic request/response models. Response models are explicit on every route.
- `src/health_api/errors.py`: `problem()` is the only way to raise an HTTP error (RFC 9457 problem+json).

## Non-negotiables
- Recommendations obey the shared R2 safety rules. Details in `.claude/rules/safety-content.md` (always loaded).
- Synthetic data only. Never add real health or personal data, and never edit the shared sample data from here.

## Working agreement
- Plan before editing more than one file; state the plan in 3-5 bullets.
- Smallest change that passes the tests. No new dependencies without asking.
- If unsure, say "unknown" and ask; don't guess at domain rules.

## Where things live in .claude/
- `rules/`: path-scoped conventions (load only when matching files are touched)
- `skills/add-endpoint/`: `/add-endpoint` procedure for new routes
- `agents/api-reviewer.md`: read-only reviewer subagent, used after route changes
- `../.mcp.json`: `health-content` MCP server from `../03-mcp-structured-errors` (catalog search with structured errors)

## Known gaps (good practice tasks)
- FastAPI request-validation 422s still use the default body, not problem+json.
