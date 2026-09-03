from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import CronJob, CronJobExecution

from ..conftest import make_paginated_response

CRON_JOB_DATA = {
    "id": "cron_1",
    "organizationId": "org_1",
    "groupId": None,
    "name": "Nightly sync",
    "description": None,
    "cronExpression": "0 0 * * *",
    "timezone": "UTC",
    "url": "https://example.com/sync",
    "method": "POST",
    "headers": None,
    "payload": None,
    "timeoutMs": 30000,
    "useStaticIp": False,
    "isActive": True,
    "notifyOnFailure": True,
    "notifyOnSuccess": False,
    "notifyEmails": None,
    "consecutiveFailures": 0,
    "lastRunAt": "2026-09-01T00:00:00Z",
    "nextRunAt": "2026-09-02T00:00:00Z",
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-09-01T00:00:00Z",
}


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


def test_list_cron_jobs_uses_real_field_names(mock_api, client):
    # GET /api/cron sends cronExpression, timezone, nextRunAt, lastRunAt and
    # consecutiveFailures -- not the old, fabricated "schedule"/"lastStatus" fields.
    mock_api.get("/api/cron").respond(200, json=make_paginated_response(
        [CRON_JOB_DATA], data_key="cronJobs", total=1,
    ))
    page = client.cron_jobs.list()
    assert len(page) == 1
    job = page.data[0]
    assert isinstance(job, CronJob)
    assert job.cron_expression == "0 0 * * *"
    assert job.next_run_at == "2026-09-02T00:00:00Z"
    assert job.last_run_at == "2026-09-01T00:00:00Z"
    assert job.consecutive_failures == 0
    assert job.payload is None
    assert not hasattr(job, "last_status")
    assert not hasattr(job, "schedule")


def test_get_cron_job_uses_real_field_names(mock_api, client):
    mock_api.get("/api/cron/cron_1").respond(200, json={"cronJob": CRON_JOB_DATA})
    job = client.cron_jobs.get("cron_1")
    assert job.cron_expression == "0 0 * * *"
    assert job.timeout_ms == 30000
    assert job.notify_on_failure is True
    assert job.notify_on_success is False
    assert job.consecutive_failures == 0


def test_create_cron_job(mock_api, client):
    mock_api.post("/api/cron").respond(200, json={"cronJob": CRON_JOB_DATA})
    job = client.cron_jobs.create({
        "name": "Nightly sync",
        "url": "https://example.com/sync",
        "cron_expression": "0 0 * * *",
        "payload": '{"foo": "bar"}',
    })
    assert isinstance(job, CronJob)
    assert job.cron_expression == "0 0 * * *"


def test_update_cron_job(mock_api, client):
    mock_api.patch("/api/cron/cron_1").respond(200, json={"success": True})
    client.cron_jobs.update("cron_1", {"cron_expression": "*/5 * * * *", "payload": "{}"})


def test_delete_cron_job(mock_api, client):
    mock_api.delete("/api/cron/cron_1").respond(200, json={"success": True})
    client.cron_jobs.delete("cron_1")


def test_trigger_cron_job_calls_trigger_endpoint(mock_api, client):
    route = mock_api.post("/api/cron/cron_1/trigger").respond(200, json={
        "execution": {
            "id": "exec_1",
            "status": "success",
            "responseStatus": 200,
            "latencyMs": 142,
        }
    })
    result = client.cron_jobs.trigger("cron_1")
    assert route.called
    assert isinstance(result, CronJobExecution)
    assert result.id == "exec_1"
    assert result.status == "success"
    assert result.response_status == 200
    assert result.latency_ms == 142


def test_trigger_cron_job_failed_execution(mock_api, client):
    mock_api.post("/api/cron/cron_1/trigger").respond(200, json={
        "execution": {
            "id": "exec_2",
            "status": "failed",
            "responseStatus": None,
            "latencyMs": 30000,
        }
    })
    result = client.cron_jobs.trigger("cron_1")
    assert result.status == "failed"
    assert result.response_status is None


async def test_async_list_cron_jobs(mock_api):
    from hookbase import AsyncHookbase

    mock_api.get("/api/cron").respond(200, json=make_paginated_response(
        [CRON_JOB_DATA], data_key="cronJobs", total=1,
    ))
    client = AsyncHookbase(api_key="whr_test")
    page = await client.cron_jobs.list()
    assert page.data[0].cron_expression == "0 0 * * *"
    await client.close()


async def test_async_trigger_cron_job(mock_api):
    from hookbase import AsyncHookbase

    mock_api.post("/api/cron/cron_1/trigger").respond(200, json={
        "execution": {
            "id": "exec_1",
            "status": "success",
            "responseStatus": 200,
            "latencyMs": 99,
        }
    })
    client = AsyncHookbase(api_key="whr_test")
    result = await client.cron_jobs.trigger("cron_1")
    assert isinstance(result, CronJobExecution)
    assert result.latency_ms == 99
    await client.close()
