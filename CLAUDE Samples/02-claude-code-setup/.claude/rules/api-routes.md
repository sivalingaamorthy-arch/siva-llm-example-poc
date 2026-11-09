---
paths:
  - "src/health_api/routes/**/*.py"
  - "src/health_api/main.py"
---

# API route conventions

- One `APIRouter` per resource, with `prefix` and `tags` set. Register it in `main.py`.
- Every route declares `response_model` and, for creates, `status_code=201`.
- Get data only through `repo: Repository = Depends(get_repository)`. Never open files here.
- Raise errors only via `problem(status, slug, detail)`. Slugs are kebab-case and stable;
  clients branch on them, so never rename an existing slug.
- Path ids are validated in the request model or with a guard clause before use.
- Keep handlers under ~20 lines. If logic grows, move it into the repository or a service.
