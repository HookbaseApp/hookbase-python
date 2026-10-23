# Hookbase Python SDK

The official Python SDK for the [Hookbase](https://hookbase.app) webhook management platform.

## Installation

```bash
pip install hookbase
# To verify Ed25519 (v1a) signed webhooks, include the optional extra:
pip install 'hookbase[ed25519]'
```

## Quick Start

```python
from hookbase import Hookbase

client = Hookbase(api_key="whr_your_api_key")

# List webhook sources
sources = client.sources.list()
for source in sources.data:
    print(f"{source.name} ({source.provider})")

# Send an outbound webhook
result = client.outbound.messages.send(
    "app_123",
    event_type="order.created",
    payload={"orderId": "456", "amount": 99.99},
)
print(f"Sent: {result.event_id}")
```

## Async Support

```python
from hookbase import AsyncHookbase

async with AsyncHookbase(api_key="whr_...") as client:
    sources = await client.sources.list()
```

## API Reference

### Client Initialization

```python
from hookbase import Hookbase

client = Hookbase(
    api_key="whr_...",           # Required
    base_url="https://...",      # Default: https://api.hookbase.app
    timeout=30.0,                # Seconds or httpx.Timeout (default: 30); None = no timeout
    max_retries=3,               # Default: 3
    debug=False,                 # Log requests
)
```

#### Custom `httpx` client

Pass your own `httpx.Client` (or `httpx.AsyncClient` for `AsyncHookbase`) for proxies, custom
transports or TLS settings. The SDK uses it as given and never modifies it: every request is
sent to an absolute URL built from `base_url`, with the SDK's `Authorization` (an `auth=` set on
your client is not applied to Hookbase requests) and `User-Agent` headers. If you pass `timeout`
(a number, an `httpx.Timeout`, or `None` for no timeout), it is applied to each request; if you
leave it out, the client's own timeout applies. `close()` (and the context manager) leaves a client you supplied open, so close
it yourself.

```python
import httpx
from hookbase import Hookbase

http = httpx.Client(verify="/etc/ssl/corp-ca.pem", timeout=10.0)
client = Hookbase(api_key="whr_...", http_client=http)  # uses the 10s client timeout
...
client.close()
http.close()
```

### Inbound Webhooks

```python
# Sources
client.sources.list(search="github", provider="github")
client.sources.create({"name": "GitHub", "slug": "github", "provider": "github"})
client.sources.get("src_id")
client.sources.update("src_id", {"name": "Updated"})
client.sources.delete("src_id")
client.sources.rotate_secret("src_id")  # 400 for vendor-issued/public-key/built-in secrets
client.sources.reveal_secret("src_id")

# A provider that verifies with no secret: signing_secret comes back None
wise = client.sources.create({"name": "Wise", "slug": "wise", "provider": "wise"})
assert wise.verifies_without_secret and wise.signing_secret is None

# WhatsApp (Meta) sources also carry a verify token
wa = client.sources.create({"name": "WhatsApp", "slug": "whatsapp", "provider": "whatsapp"})
print(wa.verify_token)
client.sources.rotate_verify_token(wa.id)

# Notion parks its verification token until you adopt it
pending = client.sources.get_pending_verification("notion")
client.sources.adopt_pending_verification("notion")

# Provider catalog: which secret each provider needs (public, no auth needed)
for p in client.providers.list(category="payments").providers:
    print(p.hookbase_provider, p.signature_verification and p.signature_verification.secret_source)
client.providers.get("stripe").signature_verification

# Destinations
client.destinations.list()
client.destinations.create({"name": "Backend", "url": "https://..."})
client.destinations.test("dst_id")

# Routes
client.routes.create({"name": "Route", "sourceId": "src_id", "destinationId": "dst_id"})
client.routes.get_circuit_status("route_id")
client.routes.reset_circuit("route_id")

# Events & Deliveries
client.events.list(source_id="src_id", from_date="2024-01-01")  # id or slug; unknown -> 404
client.events.get("evt_id")  # Includes payload and deliveries
client.deliveries.replay("del_id")
client.deliveries.bulk_replay(["del_1", "del_2"])

# Transforms & Filters
client.transforms.create({"name": "Extract", "transformType": "jsonata", "code": "$.data"})
client.transforms.test(code="$.data", payload={"data": {"key": "value"}})  # .result
client.filters.test([{"field": "$.type", "operator": "eq", "value": "order"}], payload={...})

# Schemas
client.schemas.create({"name": "OrderSchema", "jsonSchema": {"type": "object", ...}})
```

### Outbound Webhooks

```python
# Applications
client.outbound.applications.create({"name": "Acme", "externalId": "cust_123"})
client.outbound.applications.get_by_external_id("cust_123")

# Endpoints
client.outbound.endpoints.create("app_id", {"url": "https://..."})
client.outbound.endpoints.rotate_secret("ep_id", grace_period=3600)

# An unset field is left alone by an update, so `None` cannot also mean "reset
# this". Name the setting in `clear` to send an explicit null for it:
client.outbound.endpoints.update("ep_id", {"clear": ["retryDelays"]})

# Event Types & Subscriptions
client.outbound.event_types.create({"name": "order.created", "category": "orders"})
client.outbound.subscriptions.create({"endpointId": "ep_id", "eventTypeId": "et_id"})
client.outbound.subscriptions.bulk_create("ep_id", ["et_1", "et_2"])

# Send Events
client.outbound.messages.send("app_id", event_type="order.created", payload={...})

# Message Log
client.outbound.message_log.list(application_id="app_id")
client.outbound.message_log.list_attempts("msg_id")
client.outbound.message_log.stats()

# Dead Letter Queue
client.outbound.dlq.list()
client.outbound.dlq.stats()
client.outbound.dlq.retry("dlq_id")
client.outbound.dlq.retry_bulk(["dlq_1", "dlq_2"])
```

### Admin

```python
# Organizations
client.organizations.list()
client.organizations.list_members("org_id")
client.organizations.invite("org_id", "user@example.com", "member")

# API Keys
client.api_keys.create({"name": "CI Key", "scopes": ["read", "write"]})

# Analytics
client.analytics.dashboard(range="30d")

# Cron Jobs & Tunnels
client.cron_jobs.list()
client.tunnels.list()
```

### Pagination

```python
# Offset-based (sources, destinations, routes, etc.)
page = client.sources.list(page_size=10)
print(f"Total: {page.total}, Page: {page.page}")

# Auto-paginate through all items
for source in page.auto_paging_iter():
    print(source.name)

# Manual pagination
while page.has_more:
    page = page.next_page()

# Cursor-based (inbound events, applications, endpoints, subscriptions, etc.)
page = client.outbound.applications.list(limit=50)
for app in page.auto_paging_iter():
    print(app.name)
for event in client.events.list(limit=100).auto_paging_iter():
    print(event.id)

# Limit/offset with no total (deliveries): pages until one comes back short
for delivery in client.deliveries.list(status="failed", limit=100).auto_paging_iter():
    print(delivery.id, delivery.response_status)
```

### Webhook Verification

```python
from hookbase import Webhook, WebhookVerificationError

wh = Webhook("whsec_your_secret")

try:
    payload = wh.verify(request_body, request_headers)
    print(f"Verified: {payload}")
except WebhookVerificationError as e:
    print(f"Invalid: {e}")

# Generate test headers
headers = wh.generate_test_headers('{"test": true}')
```

#### Ed25519 (`v1a`) endpoints

Endpoints created with `signature_scheme="ed25519"` are signed with Ed25519
(Standard Webhooks `v1a,<sig>`). Hookbase keeps the private key; verify with the
endpoint's `whpk_` public key. This needs `pip install 'hookbase[ed25519]'`.

```python
from hookbase.models import CreateEndpointParams

ep = client.outbound.endpoints.create(
    "app_id", CreateEndpointParams(url="https://example.com/hook", signature_scheme="ed25519")
)
wh = Webhook(ep.public_key)  # "whpk_..."; same verify() API, tolerance and errors as v1
payload = wh.verify(request_body, request_headers)

# Rotation returns the new public key (no secret). During the grace period
# deliveries carry `v1a,<old> v1a,<new>`, so either key verifies them.
rotated = client.outbound.endpoints.rotate_secret(ep.id, grace_period=3600)
rotated.public_key, rotated.previous_public_key
```

The key decides the scheme (`wh.signature_scheme`): a `whsec_` secret checks
`v1` entries only and a `whpk_` key checks `v1a` entries only, so a header that
mixes both verifies with either.

### Error Handling

```python
from hookbase import (
    HookbaseError,          # Base error
    APIError,               # API returned an error
    AuthenticationError,    # 401
    ForbiddenError,         # 403
    NotFoundError,          # 404
    ValidationError,        # 400/422
    ConflictError,          # 409
    RateLimitError,         # 429 (has retry_after)
    TimeoutError,           # Request timed out
    NetworkError,           # Connection failed
    WebhookVerificationError,
)

try:
    client.sources.get("src_id")
except NotFoundError:
    print("Not found")
except RateLimitError as e:
    print(f"Retry after {e.retry_after}s")
except APIError as e:
    print(f"{e.status_code}: {e} (request_id={e.request_id})")
```

Every `APIError` carries:

- `status_code`: the HTTP status actually returned (a `ValidationError` is 400 or 422).
- `code`: the `code` from the response body, e.g. `LIMIT_EXCEEDED` or `FEATURE_DISABLED` on a
  `ForbiddenError`. When the body has no `code`, it is the class default (`forbidden`,
  `not_found`, `validation_error`, ...).
- `details`: the body's `details` object (for validation failures, `{"fieldErrors": ...,
  "formErrors": ...}`), or any extra fields the error sent (such as `current` and `max` on
  `LIMIT_EXCEEDED`); `None` when there are none. `ValidationError.validation_errors` is the
  `fieldErrors` map.
- `request_id`: the `x-request-id` response header.

`TimeoutError` and `NetworkError` (connection failures, and a `base_url` that is not an
absolute http(s) URL) are raised for requests that got no response.

### Pydantic Models

All responses are typed Pydantic models with camelCase alias support:

```python
from hookbase.models import Source, CreateSourceParams

# Use Pydantic models for type safety
params = CreateSourceParams(name="GitHub", slug="github", provider="github")
source = client.sources.create(params)

# Or use plain dicts
source = client.sources.create({"name": "GitHub", "slug": "github", "provider": "github"})

# `provider` is any string (hookbase.models.KNOWN_SOURCE_PROVIDERS lists today's values), so a
# source with a provider newer than this package still parses.
```

## Upgrading to 4.1

- `APIError.code` now carries the API's `code` from the response body (for example
  `FEATURE_DISABLED` or `LIMIT_EXCEEDED` on a `ForbiddenError`, `DUPLICATE_NAME` on a
  `ConflictError`) instead of a fixed string such as `"forbidden"` or `"conflict"`. The fixed
  string is still used when the body has no `code`. Check code that compares `.code` to those
  strings; `isinstance` checks on the error classes are unaffected.
- `ValidationError.status_code` is the status actually returned (400 or 422); it used to be
  always 400.
- `APIError.details` is now populated (see [Error Handling](#error-handling)).
- A custom `http_client` no longer needs `base_url`, auth headers or a timeout configured on it,
  and `close()` no longer closes it.
- `timeout=None` now means no timeout; leave `timeout` out to get the default.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
mypy src/hookbase
ruff check src/ tests/
```

## License

MIT
