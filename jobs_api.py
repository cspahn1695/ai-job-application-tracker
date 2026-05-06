# api resource info: https://developer.adzuna.com/docs/search
import logging
from typing import Any, Dict, Optional

import requests

ADZUNA_APP_ID = "730816bd"
ADZUNA_API_KEY = "566684235abd1589aee57a226915ca20"

logger = logging.getLogger(__name__)

# Browser-like UA: some boards only redirect properly for real clients.
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _display_location(item):
    """Best-effort location string from an Adzuna job result (shape varies by region/API)."""
    loc = item.get("location")
    if isinstance(loc, dict):
        name = loc.get("display_name")
        if name:
            return name
        areas = loc.get("area")
        if isinstance(areas, list) and areas:
            return ", ".join(str(a) for a in areas if a)
    if isinstance(loc, list) and loc:
        return ", ".join(str(x) for x in loc if x)
    if isinstance(loc, str) and loc.strip():
        return loc.strip()
    return None


def _resolve_adzuna_redirect(redirect_url: str, timeout: float = 5.0) -> str:
    """
    Follow Adzuna's tracking URL on the server and return the final URL.

    Used when the user opens a single listing (not during bulk search), so job
    lists stay fast while "View job" can still land on ZipRecruiter / etc.
    """
    u = (redirect_url or "").strip()
    if not u:
        return u
    try:
        with requests.get(
            u,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": _DEFAULT_UA,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
            stream=True,
        ) as resp:
            if resp.status_code >= 400:
                return u
            final = (resp.url or u).strip()
        if final and final != u:
            return final
    except requests.RequestException as exc:
        logger.info("Adzuna redirect resolve failed for %s: %s", u, exc)
    return u


def _listing_url_from_adzuna_item(item: Dict[str, Any]) -> str:
    """Return listing URL for API payloads without resolving redirects (keeps search fast)."""
    direct = (item.get("url") or "").strip()
    if direct:
        return direct
    return (item.get("redirect_url") or "").strip()


def _company_display(item: Dict[str, Any]) -> Optional[str]:
    c = item.get("company")
    if isinstance(c, dict):
        return c.get("display_name")
    if isinstance(c, str) and c.strip():
        return c.strip()
    return None


def fetch_jobs(city, keywords="software engineer", results_per_page=20):
    results_per_page = max(1, min(50, int(results_per_page)))
    url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "what": keywords,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }
    where = (city or "").strip()
    if where:
        params["where"] = where

    res = requests.get(url, params=params)
    data = res.json()

    jobs = []
    search_city = (city or "").strip()

    for item in data.get("results", []) or []:
        loc = _display_location(item)
        if not loc and search_city:
            loc = search_city
        jobs.append(
            {
                "title": item.get("title"),
                "company": _company_display(item),
                "location": loc,
                "search_city": search_city or None,
                "description": item.get("description"),
                "url": _listing_url_from_adzuna_item(item),
            }
        )

    return jobs
