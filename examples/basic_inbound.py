"""Basic inbound webhook setup: create source -> destination -> route."""

from hookbase import Hookbase

client = Hookbase(api_key="whr_your_api_key")

# Create a source to receive GitHub webhooks
source = client.sources.create({
    "name": "GitHub",
    "slug": "github",
    "provider": "github",
    "verifySignature": True,
})
print(f"Source created: {source.id}")
print(f"Ingest URL: {source.ingest_url}")
print(f"Signing secret: {source.signing_secret}")

# Create a destination to forward webhooks to
dest = client.destinations.create({
    "name": "My Backend",
    "slug": "backend",
    "url": "https://api.example.com/webhooks",
    "method": "POST",
    "retryCount": 3,
})
print(f"Destination created: {dest.id}")

# Create a route connecting source to destination
route = client.routes.create({
    "name": "GitHub to Backend",
    "sourceId": source.id,
    "destinationId": dest.id,
})
print(f"Route created: {route.id}")

# List recent events
events = client.events.list(source_id=source.id, limit=10)
for event in events.data:
    print(f"  Event {event.id}: {event.event_type} ({event.status})")

client.close()
