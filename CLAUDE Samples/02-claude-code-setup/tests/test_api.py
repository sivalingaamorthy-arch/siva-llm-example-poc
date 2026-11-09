import pytest
from fastapi.testclient import TestClient

from health_api.main import app
from health_api.repository import Repository, get_repository


@pytest.fixture
def client():
    repo = Repository()  # fresh state per test
    app.dependency_overrides[get_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


def recommend(client, report_id, article_id, reason="fits the report markers"):
    return client.post(
        "/recommendations",
        json={"report_id": report_id, "article_id": article_id, "reason": reason},
    )


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_excludes_defaults_and_filters(client):
    assert len(client.get("/articles").json()) == 30  # 33 minus the 3 defaults
    hyper = client.get("/articles", params={"tag": "hypertension", "category": "physical"}).json()
    assert hyper and all("hypertension" in a["condition_tags"] for a in hyper)


def test_get_article_not_found_uses_problem_json(client):
    r = client.get("/articles/physical-99")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["type"].endswith("article-not-found")


def test_create_recommendation_records_markers(client):
    r = recommend(client, "R2", "physical-01")
    assert r.status_code == 201
    assert r.json()["report_markers"] == ["hypertension", "prediabetes"]


def test_r2_safety_trap_is_blocked(client):
    r = recommend(client, "R2", "physical-08")
    assert r.status_code == 422 and r.json()["type"].endswith("unsafe-for-report")
    assert "hypertension" in r.json()["detail"]


def test_same_article_allowed_for_r1(client):
    assert recommend(client, "R1", "physical-08").status_code == 201


def test_unapproved_article_is_blocked(client):
    r = recommend(client, "R1", "physical-07")
    assert r.status_code == 422 and r.json()["type"].endswith("article-not-approved")


def test_validation_rejects_bad_ids(client):
    assert recommend(client, "R1", "x").status_code == 422
    assert recommend(client, "R9", "physical-01").status_code == 422
