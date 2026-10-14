from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(32), default="")
    color: Mapped[str] = mapped_column(String(16), default="#2F6F4E")
    credits: Mapped[int] = mapped_column(Integer, default=3)

    tasks: Mapped[List["Task"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[datetime] = mapped_column(DateTime)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=120)
    remaining_minutes: Mapped[int] = mapped_column(Integer, default=120)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    course: Mapped["Course"] = relationship(back_populates="tasks")
    sessions: Mapped[List["StudySession"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    reviews: Mapped[List["ReviewReminder"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Mon ... 6=Sun
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    label: Mapped[str] = mapped_column(String(80), default="")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    scheduled_start: Mapped[datetime] = mapped_column(DateTime)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    planned_minutes: Mapped[int] = mapped_column(Integer)
    actual_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="scheduled")
    notes: Mapped[str] = mapped_column(Text, default="")

    task: Mapped["Task"] = relationship(back_populates="sessions")


class ReviewReminder(Base):
    __tablename__ = "review_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    due_at: Mapped[datetime] = mapped_column(DateTime)
    interval_days: Mapped[int] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="reviews")


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(255), default="")
    earned_at: Mapped[datetime] = mapped_column(DateTime)


class DailyStat(Base):
    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    completed_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sessions_completed: Mapped[int] = mapped_column(Integer, default=0)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    daily_goal_minutes: Mapped[int] = mapped_column(Integer, default=120)
    last_plan_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ml_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    ml_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
