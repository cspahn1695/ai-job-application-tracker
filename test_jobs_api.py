"""Unit tests for jobs_api (no live Adzuna calls)."""

from unittest import mock

from jobs_api import _listing_url_from_adzuna_item, _resolve_adzuna_redirect


class _FakeResp:
    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


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
    with mock.patch(
        "jobs_api.requests.get",
        return_value=_FakeResp(200, final),
    ):
        out = _resolve_adzuna_redirect("https://www.adzuna.com/clk/v0?id=1")
    assert out == final


def test_resolve_adzuna_redirect_on_http_error_returns_original():
    original = "https://www.adzuna.com/clk/v0?id=1"
    with mock.patch(
        "jobs_api.requests.get",
        return_value=_FakeResp(503, "https://broken.example/err"),
    ):
        out = _resolve_adzuna_redirect(original)
    assert out == original


def test_resolve_adzuna_redirect_request_exception_returns_original():
    original = "https://www.adzuna.com/clk/v0?id=1"
    with mock.patch("jobs_api.requests.get", side_effect=OSError("timeout")):
        out = _resolve_adzuna_redirect(original)
    assert out == original

    # make sure to broaden the exception handler to catch OSError in addition to requests.RequestException
