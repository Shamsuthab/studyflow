from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt

from sqlalchemy.orm import Session

from .. import models
from . import ml_productivity, scheduler


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def metrics_for_plan(tasks: list[models.Task], plan: list[scheduler.PlannedBlock], now: datetime) -> dict:
    leftover = scheduler.unscheduled_minutes(tasks, plan)
    task_by_id = {t.id: t for t in tasks}
    placed_minutes = sum(b.minutes for b in plan)
    needed = sum(t.remaining_minutes for t in tasks)
    fully = sum(1 for minutes in leftover.values() if minutes == 0)
    overflow = sum(leftover.values())

lead_hours = []
    minutes_by_day: dict[str, int] = defaultdict(int)
    for block in plan:
        task = task_by_id[block.task_id]
        lead = (task.deadline - block.end).total_seconds() / 3600
        lead_hours.append(max(lead, 0))
        minutes_by_day[block.start.date().isoformat()] += block.minutes

preferred_hour_minutes = 0
    morning_minutes = sum(b.minutes for b in plan if 8 <= b.start.hour < 12)

return {
        "tasks": len(tasks),
        "tasks_fully_scheduled": fully,
        "coverage": round(placed_minutes / needed, 3) if needed else 1.0,
        "minutes_needed": needed,
        "minutes_placed": placed_minutes,
        "minutes_unscheduled": overflow,
        "session_count": len(plan),
        "avg_lead_hours": round(sum(lead_hours) / len(lead_hours), 2) if lead_hours else 0,
        "load_balance_std": round(_std([float(v) for v in minutes_by_day.values()]), 2),
        "morning_minutes": morning_minutes,
        "days_used": len(minutes_by_day),
        "preferred_hour_minutes": preferred_hour_minutes,
    }


def compare_strategies(db: Session, user_id: int, now: datetime | None = None) -> dict:
    now = now or datetime.now().replace(second=0, microsecond=0)
    tasks = (
        db.query(models.Task)
        .filter(models.Task.user_id == user_id)
        .filter(models.Task.status.in_(["pending", "in_progress", "overdue"]))
        .filter(models.Task.remaining_minutes > 0)
        .all()
    )
    slots = db.query(models.AvailabilitySlot).filter(models.AvailabilitySlot.user_id == user_id).all()
    scores = ml_productivity.hour_scores(db, user_id)

results = {}
    for name in scheduler.STRATEGIES:
        plan = scheduler.allocate(tasks, slots, now, hour_scores=scores, strategy=name)
        stats = metrics_for_plan(tasks, plan, now)
        if name == "ml" and scores:
            preferred_hours = {h for h, v in scores.items() if v >= 0.55}
            stats["preferred_hour_minutes"] = sum(b.minutes for b in plan if b.start.hour in preferred_hours)
        results[name] = stats

winner = max(
        results.items(),
        key=lambda item: (item[1]["coverage"], item[1]["avg_lead_hours"], -item[1]["load_balance_std"]),
    )[0]
    return {
        "generated_at": now.isoformat(),
        "winner": winner,
        "notes": {
            "deadline": "Earliest deadline first. Simple baseline.",
            "score": "Urgency × priority × difficulty × remaining effort.",
            "ml": "Same ranking as score, but prefers hours the model marks as productive.",
        },
        "strategies": results,
    }

