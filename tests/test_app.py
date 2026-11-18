
import pytest
import app as application


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        application,
        "search",
        lambda query, limit, offset: []
    )

    monkeypatch.setattr(
        application,
        "count_results",
        lambda query: 0
    )

    application.app.config["TESTING"] = True

    return application.app.test_client()


def test_home(client):
    response = client.get("/")

    assert response.status_code == 200


def test_search_api(client):
    response = client.get("/api/search?q=Belgio")

    assert response.status_code == 200

    data = response.get_json()

    assert data["query"] == "Belgio"
    assert data["total"] == 0


def test_empty_search(client):
    response = client.get("/api/search?q=")

    assert response.status_code == 200


def test_invalid_limit(client):
    response = client.get("/api/search?q=Belgio&limit=1000")

    assert response.status_code == 400


def test_long_query(client):
    response = client.get("/api/search?q=" + "a" * 301)

    assert response.status_code == 400
