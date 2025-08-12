from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_list_posts_empty():
    r = client.get("/api/v1/scraper/posts/")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 0
    assert isinstance(data["data"], list)


def test_run_scraper_requires_auth():
    r = client.post("/api/v1/scraper/run/", params={"companies": ["laudite"]})
    # Should require superuser auth
    assert r.status_code in (401, 403)
