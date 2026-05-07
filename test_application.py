import re
from secrets import token_hex
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routes


class _APIResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


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
            # 24-hex string keeps route ObjectId validation realistic but JSON-safe.
            self.id = token_hex(12)
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


def test_profile_job_search_title_location_mode(client):
    settings = SimpleNamespace(max_recommend_jobs=10)
    fake_jobs = [
        {
            "title": "Backend Engineer",
            "company": "Acme",
            "location": "Iowa City",
            "description": "Python API work",
            "url": "https://example.com/job/1",
        }
    ]

    async def fake_get_app_settings():
        return settings

    with patch("routes.get_app_settings", side_effect=fake_get_app_settings):
        with patch("routes.fetch_jobs", return_value=fake_jobs) as fetch_mock:
            res = client.get(
                "/applications/profile-job-search",
                params={
                    "mode": "title_location",
                    "city": "Iowa City",
                    "title": "backend engineer",
                },
            )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["score"] is None
    assert data[0]["job"]["title"] == "Backend Engineer"
    fetch_mock.assert_called_once_with("Iowa City", keywords="backend engineer", results_per_page=20)


def test_profile_job_search_profile_mode(client):
    class FakeEmailField:
        def __eq__(self, other):
            return {"email": other}

    class FakeBackground:
        email = FakeEmailField()

        @classmethod
        async def find_one(cls, query):
            if isinstance(query, dict) and query.get("email") == "test@example.com":
                return SimpleNamespace(
                    skills=["Python", "FastAPI"],
                    education=["BS Computer Science"],
                    experience=["Backend Developer"],
                )
            return None

    async def fake_get_app_settings():
        return SimpleNamespace(max_recommend_jobs=2)

    payload = {
        "results": [
            {
                "title": "Backend Engineer",
                "company": {"display_name": "A"},
                "location": {"display_name": "Chicago"},
                "description": "Python FastAPI backend APIs, SQL, and Docker services.",
                "url": "https://example.com/jobs/backend",
            },
            {
                "title": "Graphic Designer",
                "company": {"display_name": "B"},
                "location": {"display_name": "Chicago"},
                "description": "Brand assets, typography, and Adobe Illustrator work.",
                "url": "https://example.com/jobs/design",
            },
        ]
    }

    with patch("routes.Background", FakeBackground):
        with patch("routes.get_app_settings", side_effect=fake_get_app_settings):
            with patch("jobs_api.requests.get", return_value=_APIResp(payload)):
                res = client.get(
                    "/applications/profile-job-search",
                    params={
                        "mode": "profile",
                        "city": "Chicago",
                        "email": "test@example.com",
                    },
                )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    # Real rank_jobs should prefer backend role for this backend-heavy profile.
    assert data[0]["job"]["title"] == "Backend Engineer"
    assert data[0]["score"] >= data[1]["score"]
    assert all(isinstance(row["score"], float) for row in data)


def test_profile_job_search_both_mode_merges_and_dedupes(client):
    class FakeEmailField:
        def __eq__(self, other):
            return {"email": other}

    class FakeBackground:
        email = FakeEmailField()

        @classmethod
        async def find_one(cls, query):
            if isinstance(query, dict) and query.get("email") == "test@example.com":
                return SimpleNamespace(
                    skills=["Python"],
                    education=["BS CS"],
                    experience=["API Developer"],
                )
            return None

    async def fake_get_app_settings():
        return SimpleNamespace(max_recommend_jobs=10)

    payload_keywords = {
        "results": [
            {
                "title": "Python Dev",
                "company": {"display_name": "A"},
                "location": {"display_name": "Remote"},
                "description": "Python API development and backend services.",
                "url": "https://example.com/jobs/u1",
            },
            {
                "title": "API Dev",
                "company": {"display_name": "B"},
                "location": {"display_name": "Remote"},
                "description": "REST API implementation and integration work.",
                "url": "https://example.com/jobs/u2",
            },
        ]
    }
    payload_broad = {
        "results": [
            {
                "title": "Python Dev",
                "company": {"display_name": "A"},
                "location": {"display_name": "Remote"},
                "description": "Python API development and backend services.",
                "url": "https://example.com/jobs/u1",
            },
            {
                "title": "Data Engineer",
                "company": {"display_name": "C"},
                "location": {"display_name": "Remote"},
                "description": "ETL, SQL, and data pipeline engineering.",
                "url": "https://example.com/jobs/u3",
            },
        ]
    }

    with patch("routes.Background", FakeBackground):
        with patch("routes.get_app_settings", side_effect=fake_get_app_settings):
            with patch(
                "jobs_api.requests.get",
                side_effect=[_APIResp(payload_keywords), _APIResp(payload_broad)],
            ):
                res = client.get(
                    "/applications/profile-job-search",
                    params={
                        "mode": "both",
                        "city": "Remote",
                        "email": "test@example.com",
                        "title": "python developer",
                    },
                )

    assert res.status_code == 200
    data = res.json()
    # Combined jobs should be de-duplicated by URL: u1, u2, u3
    assert len(data) == 3
    assert sorted(row["job"]["url"] for row in data) == sorted(
        [
            "https://example.com/jobs/u1",
            "https://example.com/jobs/u2",
            "https://example.com/jobs/u3",
        ]
    )
    assert all(isinstance(row["score"], float) for row in data)

