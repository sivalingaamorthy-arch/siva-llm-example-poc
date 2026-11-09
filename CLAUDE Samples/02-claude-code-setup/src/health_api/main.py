"""Health-content API. Run: uvicorn health_api.main:app --reload"""

from fastapi import FastAPI, HTTPException

from .errors import problem_handler
from .routes import articles, recommendations

app = FastAPI(title="Health Content API", version="0.1.0")
app.add_exception_handler(HTTPException, problem_handler)
app.include_router(articles.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}
