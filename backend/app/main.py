from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .services import ml_productivity, motivation, scheduler, spaced_repetition

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StudyFlow API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_settings(db: Session) -> models.AppSettings:
    row = db.get(models.AppSettings, 1)
    if row is None:
        row = models.AppSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _session_out(s: models.StudySession) -> schemas.SessionOut:
    return schemas.SessionOut(
        id=s.id,
        task_id=s.task_id,
        scheduled_start=s.scheduled_start,
        scheduled_end=s.scheduled_end,
        actual_start=s.actual_start,
        actual_end=s.actual_end,
        planned_minutes=s.planned_minutes,
        actual_minutes=s.actual_minutes,
        status=s.status,
        notes=s.notes,
        task_title=s.task.title if s.task else None,
        course_name=s.task.course.name if s.task and s.task.course else None,
        course_color=s.task.course.color if s.task and s.task.course else None,
    )


def _review_out(r: models.ReviewReminder) -> schemas.ReviewOut:
    return schemas.ReviewOut(
        id=r.id,
        task_id=r.task_id,
        due_at=r.due_at,
        interval_days=r.interval_days,
        completed=r.completed,
        completed_at=r.completed_at,
        task_title=r.task.title if r.task else None,
        course_name=r.task.course.name if r.task and r.task.course else None,
    )


def _replan(db: Session) -> None:
    settings = _ensure_settings(db)
    scores = ml_productivity.hour_scores(db) if settings.ml_enabled else {}
    scheduler.plan_schedule(db, hour_scores=scores)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "studyflow"}


@app.get("/api/courses", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(models.Course).order_by(models.Course.name).all()


@app.post("/api/courses", response_model=schemas.CourseOut)
def create_course(payload: schemas.CourseCreate, db: Session = Depends(get_db)):
    course = models.Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    db.delete(course)
    db.commit()
    _replan(db)
    return {"ok": True}


@app.get("/api/tasks", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).order_by(models.Task.deadline).all()


@app.post("/api/tasks", response_model=schemas.TaskOut)
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    task = models.Task(**data, remaining_minutes=data["estimated_minutes"], status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    _replan(db)
    db.refresh(task)
    return task


@app.patch("/api/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    updates = payload.model_dump(exclude_unset=True)
    if "estimated_minutes" in updates and "remaining_minutes" not in updates:
        delta = updates["estimated_minutes"] - task.estimated_minutes
        task.remaining_minutes = max(0, task.remaining_minutes + delta)
    for key, value in updates.items():
        setattr(task, key, value)
    db.commit()
    _replan(db)
    db.refresh(task)
    return task


@app.post("/api/tasks/{task_id}/complete", response_model=schemas.TaskOut)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    now = datetime.now()
    late = now > task.deadline
    task.status = "completed"
    task.remaining_minutes = 0
    task.completed_at = now
    spaced_repetition.schedule_reviews(db, task, now)
    db.commit()
    if late:
        _replan(db)
    else:
        _replan(db)
    motivation.refresh_badges(db)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task)
    db.commit()
    _replan(db)
    return {"ok": True}


@app.get("/api/availability", response_model=list[schemas.SlotOut])
def list_slots(db: Session = Depends(get_db)):
    return db.query(models.AvailabilitySlot).order_by(
        models.AvailabilitySlot.weekday, models.AvailabilitySlot.start_time
    ).all()


@app.post("/api/availability", response_model=schemas.SlotOut)
def create_slot(payload: schemas.SlotCreate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "End time must be after start time")
    slot = models.AvailabilitySlot(**payload.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    _replan(db)
    return slot


@app.delete("/api/availability/{slot_id}")
def delete_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.get(models.AvailabilitySlot, slot_id)
    if not slot:
        raise HTTPException(404, "Slot not found")
    db.delete(slot)
    db.commit()
    _replan(db)
    return {"ok": True}


@app.get("/api/schedule", response_model=list[schemas.SessionOut])
def get_schedule(days: int = 14, db: Session = Depends(get_db)):
    now = datetime.now() - timedelta(days=1)
    until = datetime.now() + timedelta(days=days)
    sessions = (
        db.query(models.StudySession)
        .filter(models.StudySession.scheduled_start >= now)
        .filter(models.StudySession.scheduled_start <= until)
        .order_by(models.StudySession.scheduled_start)
        .all()
    )
    return [_session_out(s) for s in sessions]


@app.post("/api/schedule/replan")
def replan(db: Session = Depends(get_db)):
    _replan(db)
    settings = _ensure_settings(db)
    return {"ok": True, "last_plan_at": settings.last_plan_at}


@app.post("/api/sessions/{session_id}/complete", response_model=schemas.SessionOut)
def complete_session(session_id: int, payload: schemas.SessionComplete, db: Session = Depends(get_db)):
    session = db.get(models.StudySession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    now = datetime.now()
    minutes = payload.actual_minutes if payload.actual_minutes is not None else session.planned_minutes
    session.status = "completed"
    session.actual_minutes = minutes
    session.actual_start = session.scheduled_start
    session.actual_end = session.scheduled_start + timedelta(minutes=minutes)
    session.notes = payload.notes
    task = session.task
    task.remaining_minutes = max(0, task.remaining_minutes - minutes)
    if task.remaining_minutes == 0:
        task.status = "completed"
        task.completed_at = now
        spaced_repetition.schedule_reviews(db, task, now)
    elif now > task.deadline or payload.late:
        task.status = "overdue"
    else:
        task.status = "in_progress"
    motivation.record_session_minutes(db, now, minutes)
    motivation.refresh_badges(db, session)
    db.commit()
    _replan(db)
    ml_productivity.train_model(db)
    db.refresh(session)
    return _session_out(session)


@app.post("/api/sessions/{session_id}/miss")
def miss_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(models.StudySession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    session.status = "missed"
    session.task.status = "overdue" if datetime.now() > session.task.deadline else "in_progress"
    db.commit()
    _replan(db)
    ml_productivity.train_model(db)
    return _session_out(session)


@app.get("/api/reviews", response_model=list[schemas.ReviewOut])
def list_reviews(db: Session = Depends(get_db)):
    rows = db.query(models.ReviewReminder).order_by(models.ReviewReminder.due_at).all()
    return [_review_out(r) for r in rows]


@app.post("/api/reviews/{review_id}/complete", response_model=schemas.ReviewOut)
def complete_review(review_id: int, db: Session = Depends(get_db)):
    review = db.get(models.ReviewReminder, review_id)
    if not review:
        raise HTTPException(404, "Review not found")
    review.completed = True
    review.completed_at = datetime.now()
    db.commit()
    db.refresh(review)
    return _review_out(review)


@app.get("/api/dashboard", response_model=schemas.DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    settings = _ensure_settings(db)
    today = date.today()
    today_row = db.query(models.DailyStat).filter(models.DailyStat.day == today).first()
    week_ago = today - timedelta(days=6)
    week_minutes = sum(
        r.completed_minutes
        for r in db.query(models.DailyStat).filter(models.DailyStat.day >= week_ago).all()
    )
    scores = ml_productivity.hour_scores(db)
    return schemas.DashboardOut(
        streak=motivation.compute_streak(db),
        today_minutes=today_row.completed_minutes if today_row else 0,
        daily_goal_minutes=settings.daily_goal_minutes,
        pending_tasks=db.query(models.Task).filter(models.Task.status != "completed").count(),
        overdue_tasks=db.query(models.Task).filter(models.Task.status == "overdue").count(),
        upcoming_reviews=db.query(models.ReviewReminder)
        .filter(models.ReviewReminder.completed.is_(False))
        .filter(models.ReviewReminder.due_at <= datetime.now() + timedelta(days=2))
        .count(),
        week_minutes=week_minutes,
        badges=db.query(models.Badge).order_by(models.Badge.earned_at.desc()).all(),
        hour_scores={str(k): round(v, 3) for k, v in scores.items()},
        ml_ready=settings.ml_accuracy is not None,
        ml_accuracy=settings.ml_accuracy,
    )


@app.get("/api/stats", response_model=list[schemas.DailyStatOut])
def stats(db: Session = Depends(get_db)):
    start = date.today() - timedelta(days=13)
    return (
        db.query(models.DailyStat)
        .filter(models.DailyStat.day >= start)
        .order_by(models.DailyStat.day)
        .all()
    )


@app.get("/api/settings", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _ensure_settings(db)


@app.patch("/api/settings", response_model=schemas.SettingsOut)
def update_settings(payload: schemas.SettingsIn, db: Session = Depends(get_db)):
    settings = _ensure_settings(db)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    if "ml_enabled" in data:
        _replan(db)
    return settings


@app.post("/api/ml/train")
def train_ml(db: Session = Depends(get_db)):
    result = ml_productivity.train_model(db)
    if result["ready"]:
        _replan(db)
    return result
