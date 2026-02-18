"""Outbound webhooks: create app -> endpoint -> event type -> subscription -> send."""

from hookbase import Hookbase

client = Hookbase(api_key="whr_your_api_key")

# Create an application (represents a customer/tenant)
app = client.outbound.applications.create({
    "name": "Acme Corp",
    "uid": "cust_123",
    "metadata": {"plan": "pro"},
})
print(f"Application: {app.id}")

# Create an endpoint for the application
endpoint = client.outbound.endpoints.create(app.id, {
    "url": "https://acme.com/webhooks",
    "description": "Production webhook endpoint",
})
print(f"Endpoint: {endpoint.id}")
print(f"Endpoint secret: {endpoint.secret}")

# Create event types
order_type = client.outbound.event_types.create({
    "name": "order.created",
    "description": "Fired when a new order is created",
    "category": "orders",
})

# Subscribe the endpoint to the event type
sub = client.outbound.subscriptions.create({
    "endpointId": endpoint.id,
    "eventTypeId": order_type.id,
})
print(f"Subscription: {sub.id}")

# Send a webhook event
result = client.outbound.messages.send(
    app.id,
    event_type="order.created",
    payload={
        "orderId": "ord_456",
        "amount": 99.99,
        "currency": "USD",
        "customer": {"id": "cust_123", "email": "alice@acme.com"},
    },
)
print(f"Event sent: {result.event_id}, {result.messages_queued} messages queued")

# Check delivery status
messages = client.outbound.message_log.list(application_id=app.id, limit=5)
for msg in messages.data:
    print(f"  Message {msg.id}: {msg.status} ({msg.attempts}/{msg.max_attempts} attempts)")

client.close()
