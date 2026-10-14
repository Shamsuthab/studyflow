from datetime import datetime, timedelta, time

from app.database import Base, SessionLocal, engine
from app.models import AppSettings, AvailabilitySlot, Course, DailyStat, StudySession, Task
from app.services import ml_productivity, motivation, scheduler, spaced_repetition


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    courses = [
        Course(name="Algorithms", code="CS301", color="#2F6F4E", credits=4),
        Course(name="Linear Algebra", code="MATH210", color="#C45C26", credits=3),
        Course(name="Cognitive Psychology", code="PSY220", color="#3D5A80", credits=3),
        Course(name="Database Systems", code="CS340", color="#7A4E9A", credits=4),
    ]
    db.add_all(courses)
    db.flush()

    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    tasks = [
        Task(
            course_id=courses[0].id,
            title="Midterm problem set",
            description="Divide and conquer + dynamic programming practice.",
            deadline=now + timedelta(days=5, hours=10),
            estimated_minutes=240,
            remaining_minutes=180,
            difficulty=4,
            priority=5,
            status="in_progress",
        ),
        Task(
            course_id=courses[0].id,
            title="Graph theory reading",
            description="Chapters 22–24, with spaced review.",
            deadline=now + timedelta(days=9),
            estimated_minutes=120,
            remaining_minutes=90,
            difficulty=3,
            priority=3,
            status="in_progress",
        ),
        Task(
            course_id=courses[1].id,
            title="Eigenvalues worksheet",
            deadline=now + timedelta(days=3, hours=8),
            estimated_minutes=150,
            remaining_minutes=150,
            difficulty=4,
            priority=4,
            status="pending",
        ),
        Task(
            course_id=courses[2].id,
            title="Memory models essay draft",
            deadline=now + timedelta(days=8),
            estimated_minutes=180,
            remaining_minutes=180,
            difficulty=3,
            priority=4,
            status="pending",
        ),
        Task(
            course_id=courses[3].id,
            title="SQL lab + ER diagram",
            deadline=now + timedelta(days=4),
            estimated_minutes=120,
            remaining_minutes=60,
            difficulty=2,
            priority=3,
            status="in_progress",
        ),
        Task(
            course_id=courses[3].id,
            title="Normalization quiz prep",
            deadline=now + timedelta(days=12),
            estimated_minutes=90,
            remaining_minutes=90,
            difficulty=3,
            priority=2,
            status="pending",
        ),
    ]
    db.add_all(tasks)
    db.flush()

    slots = [
        AvailabilitySlot(weekday=0, start_time=time(8, 0), end_time=time(10, 0), label="Monday morning"),
        AvailabilitySlot(weekday=0, start_time=time(19, 0), end_time=time(21, 30), label="Monday evening"),
        AvailabilitySlot(weekday=1, start_time=time(14, 0), end_time=time(16, 30), label="Tuesday afternoon"),
        AvailabilitySlot(weekday=2, start_time=time(8, 0), end_time=time(10, 0), label="Wednesday morning"),
        AvailabilitySlot(weekday=3, start_time=time(18, 30), end_time=time(21, 0), label="Thursday evening"),
        AvailabilitySlot(weekday=4, start_time=time(9, 0), end_time=time(12, 0), label="Friday focus"),
        AvailabilitySlot(weekday=5, start_time=time(10, 0), end_time=time(13, 0), label="Saturday block"),
        AvailabilitySlot(weekday=6, start_time=time(16, 0), end_time=time(18, 0), label="Sunday review"),
    ]
    db.add_all(slots)

    completed_task = Task(
        course_id=courses[1].id,
        title="Matrix operations drill",
        deadline=now - timedelta(days=6),
        estimated_minutes=90,
        remaining_minutes=0,
        difficulty=2,
        priority=3,
        status="completed",
        completed_at=now - timedelta(days=6, hours=2),
    )
    db.add(completed_task)
    db.flush()
    spaced_repetition.schedule_reviews(db, completed_task, completed_task.completed_at)

    db.add(AppSettings(id=1, daily_goal_minutes=120, ml_enabled=True))

    # Historical sessions so the productivity model has something to learn.
    history = [
        (now - timedelta(days=8, hours=4), 50, True, 8),
        (now - timedelta(days=7, hours=-2), 45, True, 9),
        (now - timedelta(days=6, hours=1), 70, True, 10),
        (now - timedelta(days=5, hours=-9), 40, False, 21),
        (now - timedelta(days=4, hours=3), 55, True, 8),
        (now - timedelta(days=3, hours=-8), 30, False, 20),
        (now - timedelta(days=2, hours=2), 60, True, 9),
        (now - timedelta(days=1, hours=1), 45, True, 14),
        (now - timedelta(hours=26), 80, True, 10),
        (now - timedelta(hours=20), 25, False, 22),
    ]
    for start, minutes, ok, hour in history:
        start = start.replace(hour=hour, minute=0)
        sess = StudySession(
            task_id=tasks[0].id if ok else tasks[1].id,
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=minutes),
            actual_start=start,
            actual_end=start + timedelta(minutes=minutes if ok else 10),
            planned_minutes=minutes,
            actual_minutes=minutes if ok else 10,
            status="completed" if ok else "missed",
        )
        db.add(sess)
        if ok:
            motivation.record_session_minutes(db, start, minutes)

    db.commit()
    ml_productivity.train_model(db)
    scores = ml_productivity.hour_scores(db)
    scheduler.plan_schedule(db, hour_scores=scores)
    motivation.refresh_badges(db)
    db.commit()

    print("Seeded StudyFlow demo data.")
    db.close()


if __name__ == "__main__":
    seed()
