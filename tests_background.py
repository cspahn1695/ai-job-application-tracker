import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import background_routes


class FakeEmailField:
    def __eq__(self, other):
        return {"email": other}


@pytest.fixture
def client(monkeypatch):
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

    monkeypatch.setattr(background_routes, "Background", FakeBackground)

    app = FastAPI()
    app.include_router(background_routes.router)
    return TestClient(app)


def test_background_routes(client):
    email = "test@example.com"

    response = client.get(f"/background/{email}")
    assert response.status_code == 200

    response = client.post(f"/background/{email}/education?item=Bachelor's")
    assert response.status_code == 200

    response = client.post(f"/background/{email}/skills?item=Python")
    assert response.status_code == 200

    response = client.post(f"/background/{email}/experience?item=Programmer")
    assert response.status_code == 200

    response = client.post(
        f"/background/{email}/saved-jobs/item",
        json={
            "title": "Software Engineer",
            "url": "https://example.com/job/1",
            "company": "Example Co",
            "location": "Iowa City",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["saved_jobs"]) == 1

    response = client.delete(f"/background/{email}/education?item=Bachelor's")
    assert response.status_code == 200

    response = client.delete(f"/background/{email}/skills?item=Python")
    assert response.status_code == 200

