import pytest


@pytest.fixture(scope="session")
def stage_user():
    return {"id": 1, "name": "Alice", "age": 22}