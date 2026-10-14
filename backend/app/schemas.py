from __future__ import annotations

from datetime import date, datetime, time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    name: str
    code: str = ""
    color: str = "#2F6F4E"
    credits: int = 3


class CourseOut(CourseCreate):
    id: int

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    course_id: int
    title: str
    description: str = ""
    deadline: datetime
    estimated_minutes: int = 120
    difficulty: int = Field(default=3, ge=1, le=5)
    priority: int = Field(default=3, ge=1, le=5)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    remaining_minutes: Optional[int] = None
    difficulty: Optional[int] = None
    priority: Optional[int] = None
    status: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    course_id: int
    title: str
    description: str
    deadline: datetime
    estimated_minutes: int
    remaining_minutes: int
    difficulty: int
    priority: int
    status: str
    completed_at: Optional[datetime] = None
    course: Optional[CourseOut] = None

    model_config = {"from_attributes": True}


class SlotCreate(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    label: str = ""


class SlotOut(SlotCreate):
    id: int

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: int
    task_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    planned_minutes: int
    actual_minutes: int
    status: str
    notes: str
    task_title: Optional[str] = None
    course_name: Optional[str] = None
    course_color: Optional[str] = None

    model_config = {"from_attributes": True}


class SessionComplete(BaseModel):
    actual_minutes: Optional[int] = None
    notes: str = ""
    late: bool = False


class ReviewOut(BaseModel):
    id: int
    task_id: int
    due_at: datetime
    interval_days: int
    completed: bool
    completed_at: Optional[datetime] = None
    task_title: Optional[str] = None
    course_name: Optional[str] = None

    model_config = {"from_attributes": True}


class BadgeOut(BaseModel):
    id: int
    key: str
    name: str
    description: str
    earned_at: datetime

    model_config = {"from_attributes": True}


class SettingsIn(BaseModel):
    daily_goal_minutes: Optional[int] = None
    ml_enabled: Optional[bool] = None


class SettingsOut(BaseModel):
    daily_goal_minutes: int
    last_plan_at: Optional[datetime] = None
    ml_enabled: bool
    ml_accuracy: Optional[float] = None

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    streak: int
    today_minutes: int
    daily_goal_minutes: int
    pending_tasks: int
    overdue_tasks: int
    upcoming_reviews: int
    week_minutes: int
    badges: List[BadgeOut]
    hour_scores: Dict[str, float]
    ml_ready: bool
    ml_accuracy: Optional[float] = None


class DailyStatOut(BaseModel):
    day: date
    completed_minutes: int
    sessions_completed: int

    model_config = {"from_attributes": True}
