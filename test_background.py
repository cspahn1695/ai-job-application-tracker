from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import background_routes


class FakeEmailField:
    def __eq__(self, other):
        return {"email": other}


@pytest.fixture
def client():
    store = {}

    class FakeBackground:
        email = FakeEmailField()

        def __init__(self, email):
            self.email = (email or "").strip().lower()
            self.skills = []
            self.education = []
            self.experience = []
            self.saved_jobs = []

        async def insert(self):
            store[self.email] = self
            return self

        async def save(self):
            store[self.email] = self
            return self

        @classmethod
        async def find_one(cls, query):
            email = query.get("email") if isinstance(query, dict) else None
            return store.get((email or "").strip().lower())

    app = FastAPI()
    with patch("background_routes.Background", FakeBackground):
        app.include_router(background_routes.router)
        yield TestClient(app)


def test_background_routes_use_real_route_logic(client):
    email = "test@example.com"

    get_res = client.get(f"/background/{email}")
    assert get_res.status_code == 200
    assert get_res.json()["email"] == email

    add_edu = client.post(f"/background/{email}/education", params={"item": "Bachelor's"})
    assert add_edu.status_code == 200
    assert "Bachelor's" in add_edu.json()["education"]

    # same item should not duplicate
    add_edu_dup = client.post(f"/background/{email}/education", params={"item": "Bachelor's"})
    assert add_edu_dup.status_code == 200
    assert add_edu_dup.json()["education"].count("Bachelor's") == 1

    add_skill = client.post(f"/background/{email}/skills", params={"item": "Python"})
    assert add_skill.status_code == 200
    assert "Python" in add_skill.json()["skills"]

    add_exp = client.post(f"/background/{email}/experience", params={"item": "Programmer"})
    assert add_exp.status_code == 200
    assert "Programmer" in add_exp.json()["experience"]

    save_job = {
        "title": "Software Engineer",
        "url": "https://example.com/job/1",
        "company": "Example Co",
        "location": "Iowa City",
    }
    add_saved = client.post(f"/background/{email}/saved-jobs/item", json=save_job)
    assert add_saved.status_code == 200
    assert len(add_saved.json()["saved_jobs"]) == 1

    # saved-jobs is idempotent by URL
    add_saved_dup = client.post(f"/background/{email}/saved-jobs/item", json=save_job)
    assert add_saved_dup.status_code == 200
    assert len(add_saved_dup.json()["saved_jobs"]) == 1

    delete_saved = client.delete(
        f"/background/{email}/saved-jobs/item",
        params={"url": "https://example.com/job/1"},
    )
    assert delete_saved.status_code == 200
    assert len(delete_saved.json()["saved_jobs"]) == 0

    delete_edu = client.delete(f"/background/{email}/education", params={"item": "Bachelor's"})
    assert delete_edu.status_code == 200
    assert "Bachelor's" not in delete_edu.json()["education"]


def test_background_rejects_invalid_section_and_missing_saved_job_url(client):
    email = "test@example.com"

    bad_section = client.post(f"/background/{email}/not-a-section", params={"item": "x"})
    assert bad_section.status_code == 400
    assert bad_section.json()["detail"] == "Invalid section"

    missing_url = client.post(
        f"/background/{email}/saved-jobs/item",
        json={"title": "No URL", "url": "   ", "company": None, "location": None},
    )
    assert missing_url.status_code == 400
    assert missing_url.json()["detail"] == "Job URL is required"

