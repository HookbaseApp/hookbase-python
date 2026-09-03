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
        401, json={"error": "Invalid API key", "code": "authentication_error"}
    )
    with pytest.raises(AuthenticationError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.status_code == 401
    assert str(exc_info.value) == "Invalid API key"


def test_403_raises_forbidden_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        403, json={"error": "Forbidden", "code": "forbidden"}
    )
    with pytest.raises(ForbiddenError):
        client.sources.get("src_1")


def test_404_raises_not_found_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        404, json={"error": "Not found", "code": "not_found"}
    )
    with pytest.raises(NotFoundError):
        client.sources.get("src_1")


def test_400_raises_validation_error(mock_api, client):
    mock_api.post("/api/sources").respond(
        400,
        json={
            "error": "Name is required",
            "code": "validation_error",
            "details": {
                "fieldErrors": {"name": ["required"]},
                "formErrors": [],
            },
        },
    )
    with pytest.raises(ValidationError) as exc_info:
        client.sources.create({"name": ""})
    assert exc_info.value.validation_errors == {"name": ["required"]}
    assert str(exc_info.value) == "Name is required"


def test_409_raises_conflict_error(mock_api, client):
    mock_api.post("/api/sources").respond(
        409, json={"error": "Slug already exists", "code": "conflict"}
    )
    with pytest.raises(ConflictError):
        client.sources.create({"name": "test", "slug": "existing"})


def test_429_raises_rate_limit_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        429,
        json={"error": "Too many requests", "code": "rate_limit_exceeded"},
        headers={"retry-after": "30"},
    )
    with pytest.raises(RateLimitError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.retry_after == 30.0


def test_500_raises_api_error(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(
        500, json={"error": "Internal error", "code": "internal_error"}
    )
    with pytest.raises(APIError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.status_code == 500
    # The real API's `code` is a body-level sibling of `error`, not nested inside it —
    # make sure it's actually read rather than falling back to the generic default.
    assert exc_info.value.code == "internal_error"


def test_error_code_falls_back_to_default_when_absent(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(500, json={"error": "Internal error"})
    with pytest.raises(APIError) as exc_info:
        client.sources.get("src_1")
    assert exc_info.value.code == "unknown_error"


def test_error_from_response_string_error():
    err = APIError.from_response(500, {"error": "Server error", "code": "server_error"})
    assert str(err) == "Server error"
    assert err.code == "server_error"


def test_error_from_response_string_error_default_code():
    err = APIError.from_response(500, {"error": "Server error"})
    assert err.code == "unknown_error"


def test_error_from_response_validation_details():
    err = APIError.from_response(
        400,
        {
            "error": "Name is required",
            "code": "validation_error",
            "details": {"fieldErrors": {"name": ["required"]}},
        },
    )
    assert isinstance(err, ValidationError)
    assert err.validation_errors == {"name": ["required"]}


def test_error_from_response_dict_error():
    err = APIError.from_response(
        500, {"error": {"message": "Detailed error", "code": "server_error"}},
    )
    assert str(err) == "Detailed error"
    assert err.code == "server_error"
