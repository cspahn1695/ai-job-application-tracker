import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes


@pytest.fixture
def client(monkeypatch):
    store = {}

    class FakeQuery:
        def __init__(self, docs):
            self.docs = docs

        async def to_list(self):
            return list(self.docs)

    class FakeApplication:
        def __init__(self, **kwargs):
            self.id = str(ObjectId())
            self._id = self.id
            self.Owner = kwargs.get("Owner")
            self.owner_email = kwargs.get("owner_email")
            self.company = kwargs.get("company")
            self.role = kwargs.get("role")
            self.status = kwargs.get("status")
            self.priority = kwargs.get("priority")
            self.recruitmentinfo = kwargs.get("recruitmentinfo")
            self.jobpostinglink = kwargs.get("jobpostinglink")
            self.resume_path = kwargs.get("resume_path")

        async def insert(self):
            store[self.id] = self
            return self

        async def save(self):
            store[self.id] = self
            return self

        async def set(self, values):
            for key, value in values.items():
                setattr(self, key, value)
            store[self.id] = self
            return self

        async def delete(self):
            store.pop(self.id, None)

        @classmethod
        async def find_one(cls, query):
            oid = query.get("_id") if isinstance(query, dict) else None
            if not oid:
                return None
            return store.get(str(oid))

        @classmethod
        def find(cls, query):
            owner_email = None
            or_filters = query.get("$or", []) if isinstance(query, dict) else []
            for f in or_filters:
                if "owner_email" in f:
                    owner_email = f["owner_email"]
                    break
            docs = [
                doc
                for doc in store.values()
                if owner_email is None or doc.owner_email == owner_email
            ]
            return FakeQuery(docs)

    class FakeUser:
        def __init__(self, email):
            self.id = "user-id-1"
            self.email = email

    async def fake_get_current_user():
        return FakeUser("user@gmail.com")

    monkeypatch.setattr(routes, "Application", FakeApplication)

    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes._get_current_user] = fake_get_current_user
    return TestClient(app)


def test_application_routes(client):
    create_payload = {
        "company": "Rockwell",
        "role": "Software Engineer",
        "status": "applied",
        "priority": "high",
        "recruitmentinfo": "Campus recruiter",
        "jobpostinglink": "https://example.com/jobs/1",
    }

    create_res = client.post("/applications/", json=create_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    app_id = created["_id"]

    get_res = client.get(f"/applications/{app_id}")
    assert get_res.status_code == 200
    assert get_res.json()["company"] == "Rockwell"

    update_payload = {
        "company": "Collins Aerospace",
        "role": "Software Engineer II",
        "status": "interview",
        "priority": "medium",
        "recruitmentinfo": "Phone screen scheduled",
        "jobpostinglink": "https://example.com/jobs/2",
    }
    update_res = client.put(f"/applications/{app_id}", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "interview"

    list_res = client.get("/applications/")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    delete_res = client.delete(f"/applications/{app_id}")
    assert delete_res.status_code == 200

    missing_res = client.get(f"/applications/{app_id}")
    assert missing_res.status_code == 404

