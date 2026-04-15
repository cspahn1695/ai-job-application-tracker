import requests

ADZUNA_APP_ID = "your_id"
ADZUNA_API_KEY = "your_key"

def fetch_jobs(city, keywords="software engineer"):
    url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_API_KEY,
        "what": keywords,
        "where": city,
        "results_per_page": 20,
        "content-type": "application/json"
    }

    res = requests.get(url, params=params)
    data = res.json()

    jobs = []

    for item in data.get("results", []):
        jobs.append({
            "title": item.get("title"),
            "company": item.get("company", {}).get("display_name"),
            "location": item.get("location", {}).get("display_name"),
            "description": item.get("description"),
            "url": item.get("redirect_url")
        })

    return jobs