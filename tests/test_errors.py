from __future__ import annotations

import pytest
import respx

from hookbase import (
    APIError,
    AuthenticationError,
    ForbiddenError,
    Hookbase,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from hookbase.errors import ConflictError


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test", max_retries=0)
    yield c
    c.close()


def test_401_raises_authentication_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        401, json={"error": {"message": "Invalid API key"}}
    )
    with pytest.raises(AuthenticationError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.status_code == 401


def test_403_raises_forbidden_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        403, json={"error": {"message": "Forbidden"}}
    )
    with pytest.raises(ForbiddenError):
        client.sources.get("src_1")


def test_404_raises_not_found_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        404, json={"error": {"message": "Not found"}}
    )
    with pytest.raises(NotFoundError):
        client.sources.get("src_1")


def test_400_raises_validation_error(mock_api, client):
    mock_api.post("/api/sources").respond(
        400,
        json={"error": {"message": "Name is required",
                         "validationErrors": {"name": ["required"]}}},
    )
    with pytest.raises(ValidationError) as exc_info:
        client.sources.create({"name": ""})
    assert exc_info.value.validation_errors == {"name": ["required"]}


def test_409_raises_conflict_error(mock_api, client):
    mock_api.post("/api/sources").respond(
        409, json={"error": {"message": "Slug already exists"}}
    )
    with pytest.raises(ConflictError):
        client.sources.create({"name": "test", "slug": "existing"})


def test_429_raises_rate_limit_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        429,
        json={"error": {"message": "Too many requests"}},
        headers={"retry-after": "30"},
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.retry_after == 30.0


def test_500_raises_api_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        500, json={"error": {"message": "Internal error"}}
    )
    with pytest.raises(APIError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.status_code == 500


def test_error_from_response_string_error():
    err = APIError.from_response(500, {"error": "Server error"})
    assert str(err) == "Server error"


def test_error_from_response_dict_error():
    err = APIError.from_response(
        500, {"error": {"message": "Detailed error", "code": "server_error"}},
    )
    assert str(err) == "Detailed error"
