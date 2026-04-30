import pytest


def connect():
    print("connect to database")
    return [{"id": 1}]


@pytest.fixture(
    scope="module"
)  # if you change the scope to default("function"), then the fixture will start/teardown for each function test
def db_connection():
    print("starting up")
    db = connect()
    yield db
    print("cleaning up")
    db.clear()


def test_get_users(db_connection):
    print("first test")
    assert len(db_connection) == 1


def test_get_user_with_id(db_connection):
    print("second test")
    db_connection.append({"id": 2})
    assert db_connection[0]["id"] == 1


@pytest.mark.xfail
def test_get_users_another_time(db_connection):
    print("third test")
    assert len(db_connection) == 3