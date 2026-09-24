from __future__ import annotations

from fastapi.testclient import TestClient

from app.dashboard_api import app


def test_schedule_api_lists_live_schedule_definitions(monkeypatch):
    from app import scheduler_manager

    schedules = [
        {"id": "daily_scan", "name": "Daily scan", "action": "daily_scan", "enabled": True}
    ]
    monkeypatch.setattr(scheduler_manager, "list_schedules", lambda: schedules)
    monkeypatch.setattr(scheduler_manager, "schedule_view", lambda row: row)

    response = TestClient(app).get("/api/schedules")

    assert response.status_code == 200
    assert response.json() == schedules


def test_schedule_api_rejects_unknown_action():
    response = TestClient(app).post(
        "/api/schedules",
        json={
            "name": "Arbitrary task",
            "action": "run_python",
            "trigger": "interval",
            "interval_minutes": 15,
        },
    )

    assert response.status_code == 422


def test_schedule_api_rejects_invalid_interval():
    response = TestClient(app).post(
        "/api/schedules",
        json={
            "name": "Fast sync",
            "action": "groww_demat_sync",
            "trigger": "interval",
            "interval_minutes": 0,
        },
    )

    assert response.status_code == 422


def test_schedule_api_rejects_daily_scan_interval():
    response = TestClient(app).post(
        "/api/schedules",
        json={
            "name": "Frequent scans",
            "action": "daily_scan",
            "trigger": "interval",
            "interval_minutes": 15,
        },
    )

    assert response.status_code == 422


def test_schedule_api_unknown_update_is_not_found(monkeypatch):
    from app import scheduler_manager

    monkeypatch.setattr(scheduler_manager, "update_schedule", lambda schedule_id, schedule: None)
    response = TestClient(app).put(
        "/api/schedules/missing",
        json={
            "name": "Daily scan",
            "action": "daily_scan",
            "trigger": "cron",
            "hour": 15,
            "minute": 45,
        },
    )

    assert response.status_code == 404


def test_schedule_api_rejects_unknown_timezone():
    response = TestClient(app).post(
        "/api/schedules",
        json={
            "name": "Invalid timezone",
            "action": "daily_scan",
            "trigger": "cron",
            "timezone": "not/a-zone",
            "hour": 15,
            "minute": 45,
        },
    )

    assert response.status_code == 422


def test_schedule_run_now_endpoint_requests_engine_execution(monkeypatch):
    from app import scheduler_manager

    monkeypatch.setattr(scheduler_manager, "request_run", lambda schedule_id: True)
    response = TestClient(app).post("/api/schedules/existing/run")

    assert response.status_code == 202
    assert response.json()["status"] == "QUEUED"
