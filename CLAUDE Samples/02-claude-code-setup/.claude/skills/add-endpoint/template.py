"""Template for a new resource router. Copy to src/health_api/routes/<resource>.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..errors import problem
from ..repository import Repository, get_repository

router = APIRouter(prefix="/RESOURCE", tags=["RESOURCE"])


@router.get("/{item_id}")  # add response_model=...
def get_item(item_id: str, repo: Repository = Depends(get_repository)):
    item = None  # repo.get_<resource>(item_id)
    if item is None:
        raise problem(404, "RESOURCE-not-found", f"No RESOURCE with id '{item_id}'.")
    return item
