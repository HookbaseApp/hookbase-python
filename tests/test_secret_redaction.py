"""Secrets and credentials stay out of repr(), str() and validation errors.

Logging a create result used to print its secret, since repr() shows every field. A response that
failed to parse printed it too: pydantic quotes the input in its error, cut to the head and tail
of the dict, and a create response's secret is its last key. The same holds for the credentials
a caller passes in (signing secrets, auth configs, headers, storage keys), and for the headers
and auth configs the API returns in full to a key with the write scope.
"""

from __future__ import annotations

import json
from typing import Any

import pydantic
import pytest
from pydantic import TypeAdapter

from hookbase import AsyncHookbase
from hookbase.models import (
    ApiKeyWithSecret,
    AzureBlobConfig,
    CreateCronJobParams,
    CreateDestinationParams,
    CreateEndpointParams,
    CreateSourceParams,
    CronJob,
    CustomHeader,
    Destination,
    DestinationSecret,
    DestinationWithSecret,
    EndpointWithSecret,
    GCSConfig,
    PendingVerification,
    PortalToken,
    RotateSecretResult,
    S3Config,
    SourceWithSecret,
    Tunnel,
    TunnelToken,
    UpdateCronJobParams,
    UpdateDestinationParams,
    UpdateEndpointParams,
    UpdateSourceParams,
    WebhookEndpoint,
)

from .conftest import TEST_API_KEY

SECRET = "whsec_c2VjcmV0LXRoYXQtbXVzdC1ub3QtbGVhaw"

# (model, the other fields it requires, the secret fields)
CASES: list[tuple[type[pydantic.BaseModel], dict[str, Any], list[str]]] = [
    (DestinationWithSecret, {"id": "dst_1", "name": "D", "slug": "d"}, ["signingSecret"]),
    (DestinationSecret, {}, ["signingSecret"]),
    (SourceWithSecret, {"id": "src_1", "name": "S", "slug": "s"},
     ["signingSecret", "verifyToken"]),
    (PendingVerification, {"provider": "notion", "receivedAt": "2026-11-12T00:00:00Z"}, ["token"]),
    (EndpointWithSecret, {"id": "ep_1", "applicationId": "app_1", "url": "https://x.test"},
     ["secret"]),
    (RotateSecretResult, {}, ["secret"]),
    (ApiKeyWithSecret, {"id": "key_1", "name": "K"}, ["key"]),
    (Tunnel, {"id": "tun_1", "name": "T"}, ["authToken", "wsUrl"]),
    (TunnelToken, {}, ["authToken", "wsUrl"]),
    (PortalToken, {"id": "pt_1"}, ["token"]),
]
IDS = [model.__name__ for model, _, _ in CASES]


def _leaks(text: str) -> bool:
    """Whether any 8 characters of SECRET appear in text. pydantic quotes long inputs as their
    head and tail, so a leak can be the secret's last few characters rather than all of it."""
    return any(SECRET[i:i + 8] in text for i in range(len(SECRET) - 7))


def _parse(model: type[pydantic.BaseModel], data: Any) -> Any:
    # What the resources do with a response.
    return TypeAdapter(model).validate_python(data)


@pytest.mark.parametrize(("model", "required", "secret_fields"), CASES, ids=IDS)
def test_repr_and_str_leave_out_the_secret(model, required, secret_fields):
    parsed = _parse(model, {**required, **dict.fromkeys(secret_fields, SECRET)})
    assert not _leaks(repr(parsed))
    assert not _leaks(str(parsed))
    # Still there to read.
    dumped = parsed.model_dump(by_alias=True)
    assert all(dumped[field] == SECRET for field in secret_fields)


def test_endpoint_repr_leaves_out_the_secret():
    endpoint = WebhookEndpoint.model_validate(
        {"id": "ep_1", "applicationId": "app_1", "url": "https://x.test", "secret": SECRET},
    )
    assert not _leaks(repr(endpoint))
    assert endpoint.secret == SECRET


@pytest.mark.parametrize(("model", "required", "secret_fields"), CASES, ids=IDS)
def test_an_invalid_secret_field_is_left_out_of_the_error(model, required, secret_fields):
    with pytest.raises(pydantic.ValidationError) as exc:
        _parse(model, {**required, secret_fields[0]: [SECRET]})
    assert not _leaks(str(exc.value))
    assert not _leaks(repr(exc.value))


@pytest.mark.parametrize(
    ("model", "required", "secret_fields"), [c for c in CASES if c[1]],
    ids=[model.__name__ for model, required, _ in CASES if required],
)
def test_a_missing_field_error_leaves_out_the_secret(model, required, secret_fields):
    # A missing field quotes the whole input, secret last.
    data = {**dict(list(required.items())[1:]), **dict.fromkeys(secret_fields, SECRET)}
    with pytest.raises(pydantic.ValidationError) as exc:
        _parse(model, data)
    assert not _leaks(str(exc.value))


def test_create_response_that_fails_to_parse_leaves_out_the_secret(mock_api, client):
    # No id: the response no longer matches DestinationWithSecret.
    mock_api.post("/api/destinations").respond(201, json={"destination": {
        "name": "D", "slug": "d", "type": "http", "url": "https://x.test",
        "signingSecret": SECRET,
    }})
    with pytest.raises(pydantic.ValidationError) as exc:
        client.destinations.create({"name": "D", "slug": "d", "url": "https://x.test"})
    assert not _leaks(str(exc.value))


async def test_async_rotate_result_repr_leaves_out_the_secret(mock_api):
    mock_api.post("/api/destinations/dst_1/rotate-secret").respond(200, json={
        "signingSecret": SECRET, "previousSecretExpiresAt": "2026-11-12T01:00:00Z",
    })
    async with AsyncHookbase(api_key=TEST_API_KEY) as c:
        result = await c.destinations.rotate_secret("dst_1", grace_period_seconds=3600)
    assert not _leaks(repr(result))
    assert result.signing_secret == SECRET


HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {SECRET}"}
AUTH = {"username": "ops", "password": SECRET}
CRON = {"name": "C", "url": "https://x.test", "cronExpression": "* * * * *"}

# (model, data holding SECRET, data that fails validation and would quote SECRET). Credentials go
# last, where pydantic's truncated quote of the input keeps them.
CREDENTIAL_CASES: list[tuple[type[pydantic.BaseModel], dict[str, Any], dict[str, Any]]] = [
    (CreateSourceParams, {"name": "S", "slug": "s", "signingSecret": SECRET, "verifyToken": SECRET},
     {"name": "S", "signingSecret": SECRET}),
    (UpdateSourceParams, {"signingSecret": SECRET, "verifyToken": SECRET},
     {"signingSecret": [SECRET]}),
    (CreateDestinationParams,
     {"name": "D", "headers": HEADERS, "authType": "basic", "authConfig": AUTH,
      "config": {"accessKeyId": "AKIA", "secretAccessKey": SECRET}},
     {"slug": "d", "authConfig": AUTH}),
    (UpdateDestinationParams,
     {"headers": HEADERS, "authConfig": AUTH, "config": {"secretAccessKey": SECRET}},
     {"headers": [SECRET]}),
    (S3Config, {"bucket": "b", "region": "r", "accessKeyId": "AKIA", "secretAccessKey": SECRET},
     {"bucket": "b", "region": "r", "secretAccessKey": SECRET}),
    (GCSConfig, {"bucket": "b", "projectId": "p", "serviceAccountKey": SECRET},
     {"bucket": "b", "serviceAccountKey": SECRET}),
    (AzureBlobConfig, {"accountName": "a", "containerName": "c", "accountKey": SECRET},
     {"accountName": "a", "accountKey": SECRET}),
    (CustomHeader, {"name": "Authorization", "value": SECRET}, {"value": SECRET}),
    (CreateEndpointParams, {"url": "https://x.test", "headers": HEADERS},
     {"description": "E", "headers": HEADERS}),
    (UpdateEndpointParams,
     {"headers": [{"name": "Authorization", "value": SECRET}]}, {"headers": [SECRET]}),
    (CreateCronJobParams, {**CRON, "headers": HEADERS}, {"name": "C", "headers": HEADERS}),
    (UpdateCronJobParams, {"headers": HEADERS}, {"headers": [SECRET]}),
    (Destination, {"id": "dst_1", "name": "D", "slug": "d", "headers": HEADERS, "authConfig": AUTH},
     {"name": "D", "slug": "d", "headers": HEADERS, "authConfig": AUTH}),
    (WebhookEndpoint,
     {"id": "ep_1", "applicationId": "app_1", "url": "https://x.test",
      "headers": [{"name": "Authorization", "value": SECRET}]},
     {"id": "ep_1", "url": "https://x.test",
      "headers": [{"name": "Authorization", "value": SECRET}]}),
    (CronJob, {"id": "cj_1", "name": "C", "headers": HEADERS},
     {"name": "C", "headers": HEADERS}),
]
CREDENTIAL_IDS = [f"{model.__name__}-{i}" for i, (model, _, _) in enumerate(CREDENTIAL_CASES)]


@pytest.mark.parametrize(("model", "data", "broken"), CREDENTIAL_CASES, ids=CREDENTIAL_IDS)
def test_credentials_stay_out_of_repr_and_str(model, data, broken):
    parsed = model.model_validate(data)
    assert not _leaks(repr(parsed))
    assert not _leaks(str(parsed))
    # Still sent, and still there to read.
    assert _leaks(json.dumps(parsed.model_dump(mode="json", by_alias=True)))


@pytest.mark.parametrize(("model", "data", "broken"), CREDENTIAL_CASES, ids=CREDENTIAL_IDS)
def test_credentials_stay_out_of_validation_errors(model, data, broken):
    with pytest.raises(pydantic.ValidationError) as exc:
        model.model_validate(broken)
    assert not _leaks(str(exc.value))


def test_a_page_that_fails_to_parse_leaves_out_the_credentials(mock_api, client):
    # Each item is quoted in full when it has no id; the page's own config decides, not the
    # item's, so the list adapter asks for hidden input too.
    mock_api.get("/api/destinations").respond(200, json={
        "destinations": [{"name": "D", "slug": "d", "headers": HEADERS, "authConfig": AUTH}],
        "pagination": {"total": 1, "page": 1, "pageSize": 20},
    })
    with pytest.raises(pydantic.ValidationError) as exc:
        client.destinations.list()
    assert not _leaks(str(exc.value))


async def test_async_tunnel_list_that_fails_to_parse_leaves_out_the_token(mock_api, async_client):
    mock_api.get("/api/tunnels").respond(200, json={"tunnels": [
        {"id": "tun_1", "subdomain": "s", "authToken": SECRET},
    ]})
    with pytest.raises(pydantic.ValidationError) as exc:
        await async_client.tunnels.list()
    assert not _leaks(str(exc.value))
