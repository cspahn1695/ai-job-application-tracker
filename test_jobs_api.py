"""Unit tests for jobs_api (no live Adzuna calls)."""

from unittest.mock import patch

from jobs_api import (
    _listing_url_from_adzuna_item,
    _resolve_adzuna_redirect,
    fetch_jobs,
)


class _FakeResp:
    def __init__(self, status_code=200, url="", payload=None):
        self.status_code = status_code
        self.url = url
        self._payload = payload or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def json(self):
        return self._payload


def test_listing_url_prefers_direct_url():
    assert (
        _listing_url_from_adzuna_item(
            {
                "url": "https://boards.example.com/123",
                "redirect_url": "https://www.adzuna.com/clk/tracked",
            }
        )
        == "https://boards.example.com/123"
    )


def test_listing_url_falls_back_to_redirect_url():
    assert (
        _listing_url_from_adzuna_item({"redirect_url": "https://www.adzuna.com/clk/v0?id=1"})
        == "https://www.adzuna.com/clk/v0?id=1"
    )


def test_resolve_adzuna_redirect_returns_final_url():
    final = "https://indeed.com/viewjob?jk=abc"
    with patch(
        "jobs_api.requests.get",
        return_value=_FakeResp(200, final),
    ):
        out = _resolve_adzuna_redirect("https://www.adzuna.com/clk/v0?id=1")
    assert out == final


def test_resolve_adzuna_redirect_on_http_error_returns_original():
    original = "https://www.adzuna.com/clk/v0?id=1"
    with patch(
        "jobs_api.requests.get",
        return_value=_FakeResp(503, "https://broken.example/err"),
    ):
        out = _resolve_adzuna_redirect(original)
    assert out == original


def test_resolve_adzuna_redirect_request_exception_returns_original():
    original = "https://www.adzuna.com/clk/v0?id=1"
    with patch("jobs_api.requests.get", side_effect=OSError("timeout")):
        out = _resolve_adzuna_redirect(original)
    assert out == original


def test_fetch_jobs_builds_request_and_maps_results():
    captured = {}
    payload = {
        "results": [
            {
                "title": "Backend Engineer",
                "company": {"display_name": "Acme"},
                "location": {"display_name": "Iowa City"},
                "description": "Python and FastAPI",
                "url": "https://example.com/job/123",
            }
        ]
    }

    def fake_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return _FakeResp(payload=payload)

    with patch("jobs_api.requests.get", side_effect=fake_get):
        jobs = fetch_jobs("Iowa City", keywords="backend engineer", results_per_page=200)

    assert captured["url"].endswith("/api/jobs/us/search/1")
    assert captured["params"]["what"] == "backend engineer"
    assert captured["params"]["where"] == "Iowa City"
    assert captured["params"]["results_per_page"] == 50
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["location"] == "Iowa City"
    assert jobs[0]["search_city"] == "Iowa City"
    assert jobs[0]["url"] == "https://example.com/job/123"


def test_fetch_jobs_uses_redirect_and_city_fallback():
    payload = {
        "results": [
            {
                "title": "Analyst",
                "company": "Data Co",
                "description": "SQL",
                "redirect_url": "https://www.adzuna.com/clk/v0?id=99",
            }
        ]
    }

    with patch("jobs_api.requests.get", return_value=_FakeResp(payload=payload)):
        jobs = fetch_jobs("Chicago", keywords="analyst", results_per_page=1)

    assert len(jobs) == 1
    assert jobs[0]["location"] == "Chicago"
    assert jobs[0]["url"] == "https://www.adzuna.com/clk/v0?id=99"
