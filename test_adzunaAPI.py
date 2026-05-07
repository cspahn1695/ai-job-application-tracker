"""Tests for Adzuna-backed routes (mocked; no live API or Mongo)."""

from types import SimpleNamespace
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes

# In Python, monkey patching is the practice of dynamically replacing or modifying attributes of a module or class at runtime. 
# It allows you to change the behavior of code without altering its original source file
class FakeEmailField:
    """Stands in for Beanie `Background.email` so `Background.email == x` does not crash."""

    def __eq__(self, other):
        return {"email": other}


FAKE_JOBS = [
    {
        "title": "Software Engineer",
        "company": "Acme Corp",
        "location": "Iowa City",
        "search_city": "Iowa City",
        "description": "Python backend work.",
        "url": "https://example.com/job/1",
    }
]


@pytest.fixture
def client(monkeypatch):
    bg_store = {}

    class FakeBackground:
        email = FakeEmailField()

        def __init__(self, email):
            self.email = (email or "").strip().lower()
            self.skills = ["Python"]
            self.education = ["BS Computer Science"]
            self.experience = ["Developer"]

        @classmethod
        async def find_one(cls, query):
            # Satisfy recommend_jobs lookup for the seeded test user.
            return bg_store.get("test@example.com")

    async def fake_get_app_settings():
        return SimpleNamespace(max_recommend_jobs=10)

    def fake_fetch_jobs(city, keywords="software engineer", results_per_page=20):
        return list(FAKE_JOBS)

    def fake_rank_jobs(user_background_text, jobs):
        return [{"job": j, "score": 77.5} for j in jobs]

    monkeypatch.setattr(routes, "Background", FakeBackground)
    monkeypatch.setattr(routes, "get_app_settings", fake_get_app_settings)
    monkeypatch.setattr(routes, "fetch_jobs", fake_fetch_jobs)
    monkeypatch.setattr(routes, "rank_jobs", fake_rank_jobs)

    bg_store["test@example.com"] = FakeBackground("test@example.com")

    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_search_jobs_route(client):
    """GET /applications/search-jobs?city=&title= — keyword + location (no profile)."""
    response = client.get(
        "/applications/search-jobs",
        params={"city": "Iowa City", "title": "engineer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "Software Engineer"
    assert data[0]["url"] == "https://example.com/job/1"


def test_recommend_jobs_route(client):
    """GET /applications/recommend-jobs/{email}?city= — profile-ranked jobs."""
    email_path = quote("test@example.com", safe="")
    response = client.get(
        f"/applications/recommend-jobs/{email_path}",
        params={"city": "Iowa City"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["score"] == 77.5
    assert data[0]["job"]["title"] == "Software Engineer"
    assert data[0]["job"]["url"] == "https://example.com/job/1"

# Here's what it does:

# Mocks the redirect resolver: It patches routes._resolve_adzuna_redirect to always return a fake final URL ("https://ziprecruiter.com/candidate/job/1"), simulating what happens when an Adzuna tracking link is resolved to the actual job posting site.

# Makes a test request: It sends a GET request to the endpoint with an Adzuna URL as a query parameter ("https://www.adzuna.com/clk/v0?id=123"), and sets follow_redirects=False to capture the redirect response directly.

# Asserts the expected behavior: It checks that the response has a 302 status code (redirect) and that the Location header points to the mocked resolved URL.

# In essence, this test ensures that the route properly handles Adzuna redirect URLs by resolving them to the final destination and issuing a redirect response, without actually making external HTTP calls.


def test_resolve_listing_url_redirects(client, monkeypatch):
    """GET /applications/resolve-listing-url?url= — 302 to resolved employer URL."""
    monkeypatch.setattr(
        routes,
        "_resolve_adzuna_redirect",
        lambda url, timeout=5.0: "https://ziprecruiter.com/candidate/job/1",
    )
    response = client.get(
        "/applications/resolve-listing-url",
        params={"url": "https://www.adzuna.com/clk/v0?id=123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["location"] == "https://ziprecruiter.com/candidate/job/1"


def test_resolve_listing_url_rejects_non_adzuna(client):
    response = client.get(
        "/applications/resolve-listing-url",
        params={"url": "https://evil.example/phish"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_recommend_jobs_missing_background_returns_404(client, monkeypatch):
    """No background document -> 404 (real route behavior; empty store)."""
    class EmptyBackground:
        email = FakeEmailField()

        @classmethod
        async def find_one(cls, query):
            return None

    monkeypatch.setattr(routes, "Background", EmptyBackground)

    app = FastAPI()
    app.include_router(routes.router)
    bare = TestClient(app)

    email_path = quote("nobody@example.com", safe="")
    response = bare.get(
        f"/applications/recommend-jobs/{email_path}",
        params={"city": "Chicago"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No background found" # no background has the email nobody@example.com
