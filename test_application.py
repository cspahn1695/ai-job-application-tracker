import re
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes


@pytest.fixture
def client():
    store = {}

    class FakeQuery:
        def __init__(self, docs):
            self.docs = docs

        async def to_list(self):
            return list(self.docs)

    class FakeApplication:
        def __init__(self, **kwargs):
            self.id = ObjectId()
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
            store[str(self.id)] = self
            return self

        async def save(self):
            store[str(self.id)] = self
            return self

        async def delete(self):
            store.pop(str(self.id), None)

        @classmethod
        async def find_one(cls, query):
            if not isinstance(query, dict):
                return None
            oid = query.get("_id")
            if not oid:
                return None
            doc = store.get(str(oid))
            if not doc:
                return None
            owner_allowed = {
                f.get("owner_email")
                for f in query.get("$or", [])
                if isinstance(f, dict) and f.get("owner_email")
            }
            if owner_allowed and doc.owner_email not in owner_allowed:
                return None
            return doc

        @classmethod
        def find(cls, query):
            docs = list(store.values())
            owner_allowed = {
                f.get("owner_email")
                for f in query.get("$or", [])
                if isinstance(f, dict) and f.get("owner_email")
            }
            if owner_allowed:
                docs = [d for d in docs if d.owner_email in owner_allowed]

            if "status" in query and isinstance(query["status"], dict):
                allowed_statuses = set(query["status"].get("$in", []))
                docs = [d for d in docs if d.status in allowed_statuses]

            if "company" in query and isinstance(query["company"], dict):
                pattern = query["company"].get("$regex", "")
                flags = re.IGNORECASE if query["company"].get("$options") == "i" else 0
                docs = [d for d in docs if re.match(pattern, d.company or "", flags)]

            return FakeQuery(docs)

    class FakeUser:
        def __init__(self, email):
            self.id = "user-id-1"
            self.email = email

    async def fake_get_current_user():
        return FakeUser("user@gmail.com")

    app = FastAPI()
    with patch("routes.Application", FakeApplication):
        app.include_router(routes.router)
        app.dependency_overrides[routes._get_current_user] = fake_get_current_user
        yield TestClient(app)


def test_application_crud_and_filters(client):
    payload_1 = {
        "company": "Rockwell",
        "role": "Software Engineer",
        "status": "applied",
        "priority": "high",
        "recruitmentinfo": "Campus recruiter",
        "jobpostinglink": "https://example.com/jobs/1",
    }
    payload_2 = {
        "company": "Collins Aerospace",
        "role": "Data Engineer",
        "status": "offer",
        "priority": "medium",
        "recruitmentinfo": "Referral",
        "jobpostinglink": "https://example.com/jobs/2",
    }

    create_1 = client.post("/applications/", json=payload_1)
    create_2 = client.post("/applications/", json=payload_2)
    assert create_1.status_code == 200
    assert create_2.status_code == 200

    app_id = create_1.json()["_id"]
    get_res = client.get(f"/applications/{app_id}")
    assert get_res.status_code == 200
    assert get_res.json()["company"] == "Rockwell"

    update_payload = {
        "company": "Rockwell Automation",
        "role": "Software Engineer II",
        "status": "interview",
        "priority": "medium",
        "recruitmentinfo": "Phone screen scheduled",
        "jobpostinglink": "https://example.com/jobs/updated",
    }
    update_res = client.put(f"/applications/{app_id}", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "interview"
    assert update_res.json()["company"] == "Rockwell Automation"

    list_status = client.get("/applications/", params={"status": ["interview"]})
    assert list_status.status_code == 200
    assert len(list_status.json()) == 1
    assert list_status.json()[0]["company"] == "Rockwell Automation"

    list_company = client.get("/applications/", params={"company": "collins"})
    assert list_company.status_code == 200
    assert len(list_company.json()) == 1
    assert list_company.json()[0]["company"] == "Collins Aerospace"

    delete_res = client.delete(f"/applications/{app_id}")
    assert delete_res.status_code == 200

    missing_res = client.get(f"/applications/{app_id}")
    assert missing_res.status_code == 404

