"""Async usage with AsyncHookbase."""

import asyncio

from hookbase import AsyncHookbase


async def main():
    async with AsyncHookbase(api_key="whr_your_api_key") as client:
        # List sources
        sources = await client.sources.list()
        print(f"Found {sources.total} sources")

        for src in sources.data:
            print(f"  {src.name} ({src.provider})")

        # Send an outbound webhook
        result = await client.outbound.messages.send(
            "app_123",
            event_type="invoice.paid",
            payload={"invoiceId": "inv_789", "amount": 49.99},
        )
        print(f"Sent event: {result.event_id}")

        # Check DLQ
        dlq_stats = await client.outbound.dlq.stats()
        print(f"DLQ: {dlq_stats.total} messages")

        # Paginate through all applications
        page = await client.outbound.applications.list(limit=10)
        async for app in page.auto_paging_iter():
            print(f"  App: {app.name} (uid={app.uid})")


if __name__ == "__main__":
    asyncio.run(main())
