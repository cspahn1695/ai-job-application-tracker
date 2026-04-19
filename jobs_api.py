#api resource info: https://developer.adzuna.com/docs/search
import requests

ADZUNA_APP_ID = "730816bd"
ADZUNA_API_KEY = "566684235abd1589aee57a226915ca20"


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


def fetch_jobs(city, keywords="software engineer", results_per_page=20):
    results_per_page = max(1, min(50, int(results_per_page)))
    url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "what": keywords,
        "where": city,
        "results_per_page": results_per_page,
        "content-type": "application/json"
    }

    res = requests.get(url, params=params)
    data = res.json()

    jobs = []
    search_city = (city or "").strip()

    for item in data.get("results", []):
        loc = _display_location(item)
        if not loc and search_city:
            loc = search_city
        jobs.append({
            "title": item.get("title"),
            "company": item.get("company", {}).get("display_name"),
            "location": loc,
            "search_city": search_city or None,
            "description": item.get("description"),
            "url": item.get("redirect_url"),
        })

    return jobs