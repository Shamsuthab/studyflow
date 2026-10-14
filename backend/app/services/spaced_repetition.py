from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import models

INTERVALS = (1, 3, 7, 14)


def schedule_reviews(db: Session, task: models.Task, completed_at: datetime) -> list[models.ReviewReminder]:
    existing = {r.interval_days for r in task.reviews}
    created = []
    for days in INTERVALS:
        if days in existing:
            continue
        reminder = models.ReviewReminder(
            task_id=task.id,
            due_at=completed_at + timedelta(days=days),
            interval_days=days,
            completed=False,
        )
        db.add(reminder)
        created.append(reminder)
    return created


def due_reviews(db: Session, now: datetime | None = None) -> list[models.ReviewReminder]:
    now = now or datetime.now()
    return (
        db.query(models.ReviewReminder)
        .filter(models.ReviewReminder.completed.is_(False))
        .filter(models.ReviewReminder.due_at <= now + timedelta(days=1))
        .order_by(models.ReviewReminder.due_at)
        .all()
    )
