"""Unit tests for real Adzuna/settings/ranking logic exposed via `routes` imports."""
# some of this code was made with help of ChatGPT
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import routes


class _FakeResponse:
    """Minimal requests.Response stub for jobs_api.fetch_jobs tests."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_fetch_jobs_maps_payload_and_clamps_results_per_page():
    captured = {}
    payload = {
        "results": [
            {
                "title": "Backend Engineer",
                "company": {"display_name": "Acme Corp"},
                "location": {"display_name": "Iowa City"},
                "description": "<p>Python + FastAPI</p>",
                "url": "https://example.com/job/1",
            }
        ]
    }

    def fake_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(payload)

    # Patch only network I/O; run real fetch_jobs implementation.
    with patch("jobs_api.requests.get", side_effect=fake_get):
        jobs = routes.fetch_jobs("Iowa City", keywords="backend engineer", results_per_page=999)

    assert captured["url"].endswith("/api/jobs/us/search/1")
    assert captured["params"]["what"] == "backend engineer"
    assert captured["params"]["where"] == "Iowa City"
    assert captured["params"]["results_per_page"] == 50  # clamped from 999 -> 50
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Engineer"
    assert jobs[0]["company"] == "Acme Corp"
    assert jobs[0]["location"] == "Iowa City"
    assert jobs[0]["search_city"] == "Iowa City"
    assert jobs[0]["url"] == "https://example.com/job/1"


def test_fetch_jobs_uses_search_city_when_location_missing():
    payload = {
        "results": [
            {
                "title": "Data Analyst",
                "company": {"display_name": "Data Co"},
                "description": "SQL and dashboarding",
                "redirect_url": "https://adzuna.com/clk/abc",
            }
        ]
    }

    with patch("jobs_api.requests.get", return_value=_FakeResponse(payload)):
        jobs = routes.fetch_jobs("Chicago", keywords="data analyst", results_per_page=1)

    assert len(jobs) == 1
    assert jobs[0]["location"] == "Chicago"
    assert jobs[0]["url"] == "https://adzuna.com/clk/abc"


def test_get_app_settings_returns_existing_document():
    fake_doc = SimpleNamespace(max_recommend_jobs=17)

    with patch("app_settings_model.AppSettings.find_one", new=AsyncMock(return_value=fake_doc)):
        settings = asyncio.run(routes.get_app_settings())

    assert settings is fake_doc
    assert settings.max_recommend_jobs == 17


def test_get_app_settings_creates_default_when_missing():
    insert_mock = AsyncMock(return_value=None)

    class FakeAppSettings:
        def __init__(self, max_recommend_jobs=10):
            self.max_recommend_jobs = max_recommend_jobs

        async def insert(self):
            await insert_mock()

        @classmethod
        async def find_one(cls):
            return None

    with patch("app_settings_model.AppSettings", FakeAppSettings):
        settings = asyncio.run(routes.get_app_settings())

    insert_mock.assert_awaited_once()
    assert settings.max_recommend_jobs == 10


def test_rank_jobs_prefers_more_relevant_job_and_sorts_desc():
    user_text = "python fastapi sql docker rest api backend development"
    jobs = [
        {
            "title": "Backend Python Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Build FastAPI services with Python, SQL, and Docker.",
            "url": "https://example.com/job/backend",
        },
        {
            "title": "Graphic Designer",
            "company": "Design Co",
            "location": "Remote",
            "description": "Create brand assets in Illustrator and Photoshop.",
            "url": "https://example.com/job/designer",
        },
    ]

    ranked = routes.rank_jobs(user_text, jobs)

    assert len(ranked) == 2
    assert all("job" in item and "score" in item for item in ranked)
    assert all(isinstance(item["score"], float) for item in ranked)
    assert ranked[0]["score"] >= ranked[1]["score"]  # sorted descending
    assert ranked[0]["job"]["title"] == "Backend Python Engineer"


def test_rank_jobs_handles_empty_user_text_with_zero_scores():
    jobs = [
        {
            "title": "Software Engineer",
            "description": "Python development and APIs",
            "url": "https://example.com/job/1",
        }
    ]

    ranked = routes.rank_jobs("", jobs)
    assert len(ranked) == 1
    assert ranked[0]["score"] == 0.0
