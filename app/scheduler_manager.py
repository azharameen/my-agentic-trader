"""Shared persistent definitions for the supported background jobs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfoNotFoundError

from apscheduler.events import EVENT_JOB_ERROR
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pydantic import BaseModel, Field, field_validator, model_validator

from app import db
from config.settings import get_settings

Action = Literal["daily_scan", "groww_demat_sync", "monthly_universe_refresh"]
TriggerType = Literal["cron", "interval"]


class ScheduleInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    action: Action
    trigger: TriggerType
    timezone: str = "Asia/Kolkata"
    enabled: bool = True
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    day_of_week: str | None = None
    day: int | None = Field(default=None, ge=1, le=31)
    interval_minutes: int | None = Field(default=None, ge=1, le=10080)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be blank")
        return value.strip()

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            CronTrigger(timezone=value)
        except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Unknown timezone") from exc
        return value

    @model_validator(mode="after")
    def valid_trigger_config(self) -> ScheduleInput:
        if self.trigger == "interval" and self.interval_minutes is None:
            raise ValueError("interval_minutes is required for interval schedules")
        if self.trigger == "cron" and self.interval_minutes is not None:
            raise ValueError("interval_minutes only applies to interval schedules")
        if (self.action == "groww_demat_sync") != (self.trigger == "interval"):
            raise ValueError(
                "Groww holdings sync uses intervals; other automations use cron schedules"
            )
        if self.trigger == "cron":
            if self.action == "monthly_universe_refresh" and self.day is None:
                raise ValueError("day is required for monthly universe refresh")
            if self.action != "monthly_universe_refresh" and self.day is not None:
                raise ValueError("day is only supported for monthly universe refresh")
            if self.day_of_week and self.action != "daily_scan":
                raise ValueError("day_of_week is only supported for daily scan")
            try:
                CronTrigger(timezone=self.timezone, **self.config())
            except ValueError as exc:
                raise ValueError("Invalid cron schedule") from exc
        return self

    def config(self) -> dict[str, Any]:
        if self.trigger == "interval":
            return {"minutes": self.interval_minutes}
        values: dict[str, Any] = {"hour": self.hour or 0, "minute": self.minute or 0}
        if self.action == "daily_scan":
            values["day_of_week"] = self.day_of_week or "mon-fri"
        if self.action == "monthly_universe_refresh":
            values["day"] = self.day
        return values


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    schedule = json.loads(row.pop("schedule_config"))
    return {
        **row,
        "schedule": schedule,
        "enabled": bool(row["enabled"]),
    }


def list_schedules() -> list[dict[str, Any]]:
    seed_defaults()
    rows = db.fetchall("SELECT * FROM scheduled_jobs ORDER BY created_at, id")
    return [_decode_row(row) for row in rows]


def get_schedule(schedule_id: str) -> dict[str, Any] | None:
    db.init_all_tables()
    row = db.fetchone("SELECT * FROM scheduled_jobs WHERE id = %s", (schedule_id,))
    return _decode_row(row) if row else None


def create_schedule(schedule: ScheduleInput) -> dict[str, Any]:
    db.init_all_tables()
    now = _now()
    schedule_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO scheduled_jobs (id, name, description, action, trigger_type, schedule_config, timezone, enabled, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            schedule_id,
            schedule.name,
            schedule.description,
            schedule.action,
            schedule.trigger,
            json.dumps(schedule.config()),
            schedule.timezone,
            schedule.enabled,
            now,
            now,
        ),
    )
    return get_schedule(schedule_id)  # type: ignore[return-value]


def update_schedule(schedule_id: str, schedule: ScheduleInput) -> dict[str, Any] | None:
    db.init_all_tables()
    result = db.execute(
        "UPDATE scheduled_jobs SET name = %s, description = %s, action = %s, trigger_type = %s, "
        "schedule_config = %s, timezone = %s, enabled = %s, updated_at = %s WHERE id = %s",
        (
            schedule.name,
            schedule.description,
            schedule.action,
            schedule.trigger,
            json.dumps(schedule.config()),
            schedule.timezone,
            schedule.enabled,
            _now(),
            schedule_id,
        ),
    )
    if result.rowcount == 0:
        return None
    return get_schedule(schedule_id)


def set_enabled(schedule_id: str, enabled: bool) -> dict[str, Any] | None:
    db.init_all_tables()
    result = db.execute(
        "UPDATE scheduled_jobs SET enabled = %s, updated_at = %s WHERE id = %s",
        (enabled, _now(), schedule_id),
    )
    if result.rowcount == 0:
        return None
    return get_schedule(schedule_id)


def delete_schedule(schedule_id: str) -> bool:
    db.init_all_tables()
    if not db.fetchone("SELECT id FROM scheduled_jobs WHERE id = %s", (schedule_id,)):
        return False
    db.execute("DELETE FROM scheduled_jobs WHERE id = %s", (schedule_id,))
    return True


def request_run(schedule_id: str) -> bool:
    db.init_all_tables()
    if not db.fetchone("SELECT id FROM scheduled_jobs WHERE id = %s", (schedule_id,)):
        return False
    db.execute(
        "INSERT INTO schedule_run_requests (request_id, schedule_id, requested_at) VALUES (%s, %s, %s)",
        (str(uuid.uuid4()), schedule_id, _now()),
    )
    return True


def run_pending_requests(actions: dict[Action, Any]) -> None:
    db.init_all_tables()
    requests = db.fetchall(
        "SELECT request_id, schedule_id FROM schedule_run_requests WHERE status = 'PENDING' ORDER BY requested_at"
    )
    for request in requests:
        claim_time = _now()
        # PostgreSQL compare-and-set claims keep dashboard and engine workers from double-running a click.
        claimed = db.execute(
            "UPDATE schedule_run_requests SET status = 'RUNNING', claimed_at = %s "
            "WHERE request_id = %s AND status = 'PENDING'",
            (claim_time, request["request_id"]),
        )
        if claimed.rowcount == 0:
            continue
        schedule = get_schedule(request["schedule_id"])
        status, error = "SUCCESS", None
        try:
            if schedule:
                result = actions[schedule["action"]]()
                if isinstance(result, dict) and result.get("status") in {"ERROR", "PARTIAL"}:
                    status = "FAILED" if result["status"] == "ERROR" else "PARTIAL"
                    error = result.get("error") or result.get("reason") or result.get("message")
            else:
                status = "CANCELLED"
        except Exception as exc:  # noqa: BLE001 - persist failure for the schedule UI
            status, error = "FAILED", str(exc)
        finished_at = _now()
        db.execute(
            "UPDATE schedule_run_requests SET status = %s, completed_at = %s, error = %s WHERE request_id = %s",
            (status, finished_at, error, request["request_id"]),
        )
        if schedule:
            db.execute(
                "UPDATE scheduled_jobs SET last_run_at = %s, last_status = %s, updated_at = %s WHERE id = %s",
                (_now(), status, _now(), schedule["id"]),
            )
            if status in {"FAILED", "PARTIAL"}:
                db.execute(
                    "UPDATE schedule_run_requests SET error = %s WHERE request_id = %s",
                    (error, request["request_id"]),
                )


def seed_defaults() -> None:
    """Create the original three jobs once; UI changes are persisted afterward."""
    db.init_all_tables()
    seeded = db.execute(
        "INSERT INTO scheduler_state (state_key) VALUES ('defaults_seeded') ON CONFLICT DO NOTHING"
    )
    if seeded.rowcount == 0:
        return
    settings = get_settings()
    defaults = [
        ScheduleInput(
            name="Daily universe scan",
            description="Scan NIFTY 100 and queue proposals for review.",
            action="daily_scan",
            trigger="cron",
            timezone=settings.SCHEDULER_TIMEZONE,
            hour=settings.SCAN_CRON_HOUR,
            minute=settings.SCAN_CRON_MINUTE,
            day_of_week=settings.SCAN_CRON_DAYS,
        ),
        ScheduleInput(
            name="Groww holdings sync",
            description="Refresh read-only Groww Demat holdings.",
            action="groww_demat_sync",
            trigger="interval",
            timezone=settings.SCHEDULER_TIMEZONE,
            interval_minutes=15,
        ),
        ScheduleInput(
            name="Monthly universe refresh",
            description="Refresh NIFTY 100 constituents and report changes.",
            action="monthly_universe_refresh",
            trigger="cron",
            timezone=settings.SCHEDULER_TIMEZONE,
            hour=settings.UNIVERSE_REFRESH_HOUR,
            minute=settings.UNIVERSE_REFRESH_MINUTE,
            day=settings.UNIVERSE_REFRESH_DAY_OF_MONTH,
        ),
    ]
    for schedule in defaults:
        create_schedule(schedule)


def _trigger(record: dict[str, Any]) -> CronTrigger | IntervalTrigger:
    schedule = record["schedule"]
    if record["trigger_type"] == "interval":
        return IntervalTrigger(minutes=schedule["minutes"], timezone=record["timezone"])
    return CronTrigger(timezone=record["timezone"], **schedule)


def reconcile_scheduler(scheduler: BaseScheduler, actions: dict[Action, Any]) -> None:
    """Apply shared schedule definitions to this process's live APScheduler."""
    records = list_schedules()
    desired_ids = {record["id"] for record in records if record["enabled"]}
    for job in scheduler.get_jobs():
        if job.id.startswith("managed:") and job.id.removeprefix("managed:") not in desired_ids:
            scheduler.remove_job(job.id)
    for record in records:
        job_id = f"managed:{record['id']}"
        if not record["enabled"]:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            continue
        existing = scheduler.get_job(job_id)
        trigger = _trigger(record)
        if existing:
            action = actions[record["action"]]
            if existing.func is not action:
                scheduler.remove_job(job_id)
                scheduler.add_job(
                    action, trigger=trigger, id=job_id, name=record["name"], replace_existing=True
                )
            else:
                if not _same_trigger(existing.trigger, trigger):
                    scheduler.reschedule_job(job_id, trigger=trigger)
                if existing.name != record["name"]:
                    scheduler.modify_job(job_id, name=record["name"])
        else:
            scheduler.add_job(
                actions[record["action"]],
                trigger=trigger,
                id=job_id,
                name=record["name"],
                replace_existing=True,
            )


def _same_trigger(current: Any, desired: Any) -> bool:
    if isinstance(current, IntervalTrigger) and isinstance(desired, IntervalTrigger):
        return current.interval == desired.interval and current.timezone == desired.timezone
    return str(current) == str(desired) and current.timezone == desired.timezone


def record_run(event: Any) -> None:
    if not event.job_id.startswith("managed:"):
        return
    status = "FAILED" if event.code == EVENT_JOB_ERROR else "SUCCESS"
    db.execute(
        "UPDATE scheduled_jobs SET last_run_at = %s, last_status = %s, updated_at = %s WHERE id = %s",
        (
            event.scheduled_run_time.isoformat(),
            status,
            _now(),
            event.job_id.removeprefix("managed:"),
        ),
    )


def schedule_view(record: dict[str, Any], scheduler: BaseScheduler | None = None) -> dict[str, Any]:
    if scheduler:
        job = scheduler.get_job(f"managed:{record['id']}")
        next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    elif record["enabled"]:
        now = datetime.now(timezone.utc)
        next_run_time = _trigger(record).get_next_fire_time(None, now)
        next_run = next_run_time.isoformat() if next_run_time else None
    else:
        next_run = None
    run_error = None
    last_run_at = record.get("last_run_at")
    last_status = record.get("last_status")
    if record.get("last_status") in {"PARTIAL", "FAILED"}:
        latest_sync = db.fetchone(
            "SELECT error FROM groww_sync_runs WHERE error IS NOT NULL ORDER BY started_at DESC LIMIT 1"
        )
        run_error = latest_sync.get("error") if latest_sync else None
    if record["action"] == "groww_demat_sync":
        latest_sync = db.fetchone(
            "SELECT started_at, status, error FROM groww_sync_runs ORDER BY started_at DESC LIMIT 1"
        )
        if latest_sync:
            last_run_at = latest_sync["started_at"]
            last_status = latest_sync["status"]
            run_error = latest_sync.get("error")
    latest_request = db.fetchone(
        "SELECT requested_at, completed_at, status, error FROM schedule_run_requests "
        "WHERE schedule_id = %s ORDER BY requested_at DESC LIMIT 1",
        (record["id"],),
    )
    return {
        **record,
        "last_run_at": last_run_at,
        "last_status": last_status,
        "next_run": next_run,
        "latest_run_request": latest_request,
        "last_error": run_error,
    }
