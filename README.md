# Hookbase Python SDK

The official Python SDK for the [Hookbase](https://hookbase.app) webhook management platform.

## Installation

```bash
pip install hookbase
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
    timeout=30.0,                # Seconds (default: 30)
    max_retries=3,               # Default: 3
    debug=False,                 # Log requests
)
```

### Inbound Webhooks

```python
# Sources
client.sources.list(search="github", provider="github")
client.sources.create({"name": "GitHub", "slug": "github", "provider": "github"})
client.sources.get("src_id")
client.sources.update("src_id", {"name": "Updated"})
client.sources.delete("src_id")
client.sources.rotate_secret("src_id")

# Destinations
client.destinations.list()
client.destinations.create({"name": "Backend", "url": "https://..."})
client.destinations.test("dst_id")

# Routes
client.routes.create({"name": "Route", "sourceId": "src_id", "destinationId": "dst_id"})
client.routes.get_circuit_status("route_id")
client.routes.reset_circuit("route_id")

# Events & Deliveries
client.events.list(source_id="src_id", from_date="2024-01-01")
client.events.get("evt_id")  # Includes payload and deliveries
client.deliveries.replay("del_id")
client.deliveries.bulk_replay(["del_1", "del_2"])

# Transforms & Filters
client.transforms.create({"name": "Extract", "transformType": "jsonata", "code": "$.data"})
client.transforms.test("txf_id", payload={"data": {"key": "value"}})
client.filters.test([{"field": "$.type", "operator": "eq", "value": "order"}], payload={...})

# Schemas
client.schemas.create({"name": "OrderSchema", "jsonSchema": {"type": "object", ...}})
```

### Outbound Webhooks

```python
# Applications
client.outbound.applications.create({"name": "Acme", "uid": "cust_123"})
client.outbound.applications.get_by_external_id("cust_123")

# Endpoints
client.outbound.endpoints.create("app_id", {"url": "https://..."})
client.outbound.endpoints.rotate_secret("ep_id", grace_period=3600)

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

# Cursor-based (applications, endpoints, subscriptions, etc.)
page = client.outbound.applications.list(limit=50)
for app in page.auto_paging_iter():
    print(app.name)
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

### Pydantic Models

All responses are typed Pydantic models with camelCase alias support:

```python
from hookbase.models import Source, CreateSourceParams

# Use Pydantic models for type safety
params = CreateSourceParams(name="GitHub", provider="github")
source = client.sources.create(params)

# Or use plain dicts
source = client.sources.create({"name": "GitHub", "provider": "github"})
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
mypy src/hookbase
ruff check src/ tests/
```

## License

MIT
