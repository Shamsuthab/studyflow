from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .. import models

BADGE_CATALOG = {
    "first_session": ("First Focus", "Logged your first study session."),
    "streak_3": ("Warming Up", "Studied three days in a row."),
    "streak_7": ("Week Warrior", "Kept a seven-day study streak."),
    "tasks_5": ("Deadline Hunter", "Completed five tasks."),
    "tasks_10": ("Course Crusher", "Completed ten tasks."),
    "goal_met": ("On Target", "Hit a daily study goal."),
    "early_bird": ("Early Bird", "Finished a session before 9:00."),
    "deep_work": ("Deep Work", "Completed a session of 60+ minutes."),
}


def _get_or_create_day(db: Session, day: date) -> models.DailyStat:
    row = db.query(models.DailyStat).filter(models.DailyStat.day == day).first()
    if row is None:
        row = models.DailyStat(day=day, completed_minutes=0, sessions_completed=0)
        db.add(row)
        db.flush()
    return row


def record_session_minutes(db: Session, when: datetime, minutes: int) -> None:
    row = _get_or_create_day(db, when.date())
    row.completed_minutes += minutes
    row.sessions_completed += 1


def compute_streak(db: Session, today: date | None = None) -> int:
    today = today or date.today()
    days = {
        r.day
        for r in db.query(models.DailyStat).filter(models.DailyStat.completed_minutes > 0).all()
    }
    streak = 0
    cursor = today
    if today not in days:
        cursor = today - timedelta(days=1)
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def award_badge(db: Session, key: str) -> models.Badge | None:
    if db.query(models.Badge).filter(models.Badge.key == key).first():
        return None
    name, description = BADGE_CATALOG[key]
    badge = models.Badge(key=key, name=name, description=description, earned_at=datetime.now())
    db.add(badge)
    return badge


def refresh_badges(db: Session, session: models.StudySession | None = None) -> None:
    completed_sessions = (
        db.query(models.StudySession).filter(models.StudySession.status == "completed").count()
    )
    completed_tasks = db.query(models.Task).filter(models.Task.status == "completed").count()
    streak = compute_streak(db)
    settings = db.get(models.AppSettings, 1)
    goal = settings.daily_goal_minutes if settings else 120
    today = db.query(models.DailyStat).filter(models.DailyStat.day == date.today()).first()

    if completed_sessions >= 1:
        award_badge(db, "first_session")
    if streak >= 3:
        award_badge(db, "streak_3")
    if streak >= 7:
        award_badge(db, "streak_7")
    if completed_tasks >= 5:
        award_badge(db, "tasks_5")
    if completed_tasks >= 10:
        award_badge(db, "tasks_10")
    if today and today.completed_minutes >= goal:
        award_badge(db, "goal_met")
    if session and session.actual_start and session.actual_start.hour < 9:
        award_badge(db, "early_bird")
    if session and session.actual_minutes >= 60:
        award_badge(db, "deep_work")
