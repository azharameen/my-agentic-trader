from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from apscheduler.events import EVENT_JOB_EXECUTED

from app import scheduler_manager


class FakeScheduler:
    def __init__(self):
        self.jobs = {}
        self.removed = []
        self.rescheduled = []

    def get_jobs(self):
        return list(self.jobs.values())

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def remove_job(self, job_id):
        self.removed.append(job_id)
        self.jobs.pop(job_id, None)

    def add_job(self, func, trigger, id, name, replace_existing):
        self.jobs[id] = SimpleNamespace(id=id, name=name, func=func, trigger=trigger)

    def reschedule_job(self, job_id, trigger):
        self.rescheduled.append((job_id, trigger))


def test_reconcile_scheduler_adds_only_enabled_managed_jobs(monkeypatch):
    monkeypatch.setattr(
        scheduler_manager,
        "list_schedules",
        lambda: [
            {
                "id": "one",
                "name": "Run scan",
                "action": "daily_scan",
                "enabled": True,
                "trigger_type": "cron",
                "schedule": {"hour": 15, "minute": 45, "day_of_week": "mon-fri"},
                "timezone": "Asia/Kolkata",
            },
            {
                "id": "two",
                "name": "Paused",
                "action": "groww_demat_sync",
                "enabled": False,
                "trigger_type": "interval",
                "schedule": {"minutes": 15},
                "timezone": "Asia/Kolkata",
            },
        ],
    )
    monkeypatch.setattr(scheduler_manager, "seed_defaults", lambda: None)
    scheduler = FakeScheduler()

    def action():
        return None

    scheduler_manager.reconcile_scheduler(
        scheduler,
        {"daily_scan": action, "groww_demat_sync": action, "monthly_universe_refresh": action},
    )

    assert list(scheduler.jobs) == ["managed:one"]
    assert scheduler.jobs["managed:one"].func.__name__ == action.__name__


def test_record_run_persists_job_outcome(monkeypatch):
    calls = []
    monkeypatch.setattr(
        scheduler_manager.db, "execute", lambda query, params: calls.append((query, params))
    )
    run_time = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    event = type(
        "Event",
        (),
        {
            "job_id": "managed:schedule-1",
            "scheduled_run_time": run_time,
            "code": EVENT_JOB_EXECUTED,
        },
    )()

    scheduler_manager.record_run(event)

    assert calls[0][1][0:2] == ("2026-09-24T12:00:00+00:00", "SUCCESS")
    assert calls[0][1][3] == "schedule-1"


def test_pending_run_request_executes_supported_action_and_records_success(monkeypatch):
    calls = []
    action_calls = []
    monkeypatch.setattr(
        scheduler_manager.db,
        "fetchall",
        lambda query: [{"request_id": "request-1", "schedule_id": "schedule-1"}],
    )
    monkeypatch.setattr(
        scheduler_manager.db,
        "execute",
        lambda query, params: calls.append((query, params)) or SimpleNamespace(rowcount=1),
    )
    monkeypatch.setattr(
        scheduler_manager,
        "get_schedule",
        lambda schedule_id: {"id": schedule_id, "action": "daily_scan"},
    )

    def run_scan():
        action_calls.append("ran")
        return {"status": "OK"}

    scheduler_manager.run_pending_requests({"daily_scan": run_scan})

    assert action_calls == ["ran"]
    completion = next(params for query, params in calls if "SET status = %s, completed_at" in query)
    assert completion[0] == "SUCCESS"
    assert completion[-1] == "request-1"


def test_pending_run_request_propagates_partial_action_status(monkeypatch):
    calls = []
    monkeypatch.setattr(
        scheduler_manager.db,
        "fetchall",
        lambda query: [{"request_id": "request-2", "schedule_id": "schedule-1"}],
    )
    monkeypatch.setattr(
        scheduler_manager.db,
        "execute",
        lambda query, params: calls.append((query, params)) or SimpleNamespace(rowcount=1),
    )
    monkeypatch.setattr(
        scheduler_manager,
        "get_schedule",
        lambda schedule_id: {"id": schedule_id, "action": "groww_demat_sync"},
    )

    scheduler_manager.run_pending_requests(
        {"groww_demat_sync": lambda: {"status": "PARTIAL", "error": "403 scope"}}
    )

    completion = next(params for query, params in calls if "SET status = %s, completed_at" in query)
    assert completion[0] == "PARTIAL"
    assert completion[2] == "403 scope"


def test_reconcile_reschedules_interval_when_frequency_changes(monkeypatch):
    monkeypatch.setattr(
        scheduler_manager,
        "list_schedules",
        lambda: [
            {
                "id": "two",
                "name": "Sync",
                "action": "groww_demat_sync",
                "enabled": True,
                "trigger_type": "interval",
                "schedule": {"minutes": 30},
                "timezone": "Asia/Kolkata",
            },
        ],
    )
    monkeypatch.setattr(scheduler_manager, "seed_defaults", lambda: None)
    scheduler = FakeScheduler()

    def action():
        return None

    scheduler.jobs["managed:two"] = SimpleNamespace(
        id="managed:two",
        name="Sync",
        func=action,
        trigger=scheduler_manager.IntervalTrigger(minutes=15, timezone="Asia/Kolkata"),
    )

    scheduler_manager.reconcile_scheduler(
        scheduler,
        {"daily_scan": action, "groww_demat_sync": action, "monthly_universe_refresh": action},
    )

    assert scheduler.rescheduled[0][0] == "managed:two"
    assert scheduler.rescheduled[0][1].interval.total_seconds() == 1800
