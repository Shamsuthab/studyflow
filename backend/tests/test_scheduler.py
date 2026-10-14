from datetime import datetime, time, timedelta

from app.database import Base
from app.models import AvailabilitySlot, Course, Task
from app.services.scheduler import plan_schedule, task_score
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_urgent_high_priority_scores_higher():
    now = datetime(2026, 10, 14, 9, 0)
    course = Course(id=1, name="X")
    soon = Task(
        id=1,
        course_id=1,
        title="soon",
        deadline=now + timedelta(hours=12),
        remaining_minutes=60,
        priority=5,
        difficulty=4,
        status="pending",
    )
    later = Task(
        id=2,
        course_id=1,
        title="later",
        deadline=now + timedelta(days=10),
        remaining_minutes=60,
        priority=2,
        difficulty=1,
        status="pending",
    )
    soon.course = course
    later.course = course
    assert task_score(soon, now) > task_score(later, now)


def test_plan_fits_blocks_before_deadline():
    db = _session()
    course = Course(name="Algo", code="CS", color="#000")
    db.add(course)
    db.flush()
    now = datetime(2026, 10, 14, 8, 0)  # Wednesday
    db.add(
        Task(
            course_id=course.id,
            title="PS1",
            deadline=now + timedelta(days=2, hours=4),
            estimated_minutes=90,
            remaining_minutes=90,
            difficulty=3,
            priority=4,
            status="pending",
        )
    )
    db.add(AvailabilitySlot(weekday=2, start_time=time(9, 0), end_time=time(12, 0), label="Wed"))
    db.add(AvailabilitySlot(weekday=3, start_time=time(9, 0), end_time=time(11, 0), label="Thu"))
    db.commit()

    sessions = plan_schedule(db, now=now)
    assert sessions
    total = sum(s.planned_minutes for s in sessions)
    assert total == 90
    assert all(s.scheduled_end <= now + timedelta(days=2, hours=4) for s in sessions)
