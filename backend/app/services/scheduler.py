"""Rule-based study scheduler.

Tasks are packed into weekly free-time slots before each deadline.
Ordering uses urgency, priority, estimated effort and difficulty.
Hour scores from the productivity model (when available) bias slot choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import models

MIN_BLOCK = 25
MAX_BLOCK = 90


@dataclass
class FreeBlock:
    start: datetime
    end: datetime

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)


def task_score(task: models.Task, now: datetime) -> float:
    hours_left = max((task.deadline - now).total_seconds() / 3600, 0.25)
    urgency = 48 / hours_left
    effort = task.remaining_minutes / 60
    return urgency * task.priority * (1 + task.difficulty / 5) * (1 + effort / 4)


def _expand_slots(slots: list[models.AvailabilitySlot], start: datetime, until: datetime) -> list[FreeBlock]:
    blocks: list[FreeBlock] = []
    day = start.date()
    last = until.date()
    while day <= last:
        weekday = day.weekday()
        for slot in slots:
            if slot.weekday != weekday:
                continue
            block_start = datetime.combine(day, slot.start_time)
            block_end = datetime.combine(day, slot.end_time)
            if block_end <= start:
                continue
            if block_start < start:
                block_start = start
            if block_end <= block_start:
                continue
            if block_start >= until:
                continue
            if block_end > until:
                block_end = until
            blocks.append(FreeBlock(block_start, block_end))
        day += timedelta(days=1)
    blocks.sort(key=lambda b: b.start)
    return blocks


def _block_preference(block: FreeBlock, hour_scores: dict[int, float]) -> float:
    if not hour_scores:
        return 1.0
    hour = block.start.hour
    return 0.35 + hour_scores.get(hour, 0.4)


def plan_schedule(db: Session, now: datetime | None = None, hour_scores: dict[int, float] | None = None) -> list[models.StudySession]:
    now = now or datetime.now().replace(second=0, microsecond=0)
    hour_scores = hour_scores or {}

    slots = db.query(models.AvailabilitySlot).all()
    tasks = (
        db.query(models.Task)
        .filter(models.Task.status.in_(["pending", "in_progress", "overdue"]))
        .filter(models.Task.remaining_minutes > 0)
        .all()
    )

    db.query(models.StudySession).filter(
        models.StudySession.status == "scheduled",
        models.StudySession.scheduled_start >= now,
    ).delete(synchronize_session=False)
    db.flush()

    if not slots or not tasks:
        db.commit()
        return []

    horizon = now + timedelta(days=28)
    latest_deadline = max(t.deadline for t in tasks)
    until = max(horizon, latest_deadline)

    free = _expand_slots(slots, now, until)
    ranked = sorted(tasks, key=lambda t: task_score(t, now), reverse=True)
    created: list[models.StudySession] = []

    remaining = {t.id: t.remaining_minutes for t in ranked}

    for task in ranked:
        need = remaining[task.id]
        if need <= 0:
            continue
        cutoff = min(task.deadline, until)
        candidates = [b for b in free if b.start < cutoff and b.minutes >= MIN_BLOCK]
        candidates.sort(key=lambda b: (-_block_preference(b, hour_scores), b.start))

        for block in list(candidates):
            if remaining[task.id] <= 0:
                break
            if block not in free or block.start >= cutoff:
                continue
            take = min(MAX_BLOCK, remaining[task.id], block.minutes)
            if take < MIN_BLOCK and remaining[task.id] >= MIN_BLOCK:
                continue
            take = max(take, min(block.minutes, remaining[task.id]))
            sess_end = block.start + timedelta(minutes=take)
            session = models.StudySession(
                task_id=task.id,
                scheduled_start=block.start,
                scheduled_end=sess_end,
                planned_minutes=take,
                status="scheduled",
            )
            db.add(session)
            created.append(session)
            remaining[task.id] -= take
            free.remove(block)
            leftover = FreeBlock(sess_end, block.end)
            if leftover.minutes >= MIN_BLOCK:
                free.append(leftover)
                free.sort(key=lambda b: b.start)

        if remaining[task.id] > 0 and task.deadline < now:
            task.status = "overdue"
        elif task.status == "pending":
            task.status = "in_progress"

    _touch_plan(db, now)
    db.commit()
    for s in created:
        db.refresh(s)
    return created


def _settings(db: Session) -> models.AppSettings:
    row = db.get(models.AppSettings, 1)
    if row is None:
        row = models.AppSettings(id=1)
        db.add(row)
        db.flush()
    return row


def _touch_plan(db: Session, now: datetime) -> models.AppSettings:
    row = _settings(db)
    row.last_plan_at = now
    return row
