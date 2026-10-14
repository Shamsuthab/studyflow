"""Learn preferred study hours from completed sessions.

Uses a decision tree when enough labelled sessions exist; otherwise falls
back to a simple completion-rate histogram by hour of day.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy.orm import Session

from .. import models

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "productivity_model.joblib"
MIN_SAMPLES = 8


def _features(hour: int, weekday: int, planned: int) -> list[float]:
    return [hour, weekday, planned, np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)]


def _labelled(db: Session) -> tuple[np.ndarray, np.ndarray]:
    rows = (
        db.query(models.StudySession)
        .filter(models.StudySession.status.in_(["completed", "missed"]))
        .all()
    )
    X, y = [], []
    for s in rows:
        start = s.actual_start or s.scheduled_start
        productive = int(s.status == "completed" and s.actual_minutes >= max(15, int(s.planned_minutes * 0.6)))
        X.append(_features(start.hour, start.weekday(), s.planned_minutes))
        y.append(productive)
    return np.array(X), np.array(y)


def train_model(db: Session) -> dict:
    X, y = _labelled(db)
    settings = db.get(models.AppSettings, 1)
    if settings is None:
        settings = models.AppSettings(id=1)
        db.add(settings)
        db.flush()

    if len(y) < MIN_SAMPLES or len(set(y.tolist())) < 2:
        settings.ml_accuracy = None
        db.commit()
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        return {"ready": False, "samples": int(len(y)), "accuracy": None}

    model = DecisionTreeClassifier(max_depth=4, min_samples_leaf=2, random_state=42)
    model.fit(X, y)
    acc = float(model.score(X, y))
    joblib.dump(model, MODEL_PATH)
    settings.ml_accuracy = round(acc, 3)
    db.commit()
    return {"ready": True, "samples": int(len(y)), "accuracy": settings.ml_accuracy}


def hour_scores(db: Session) -> dict[int, float]:
    X, y = _labelled(db)
    scores = {h: 0.5 for h in range(24)}
    if len(y) == 0:
        return scores

    if MODEL_PATH.exists() and len(y) >= MIN_SAMPLES:
        model = joblib.load(MODEL_PATH)
        for hour in range(24):
            sample = [_features(hour, 2, 45)]
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(sample)[0]
                classes = list(model.classes_)
                scores[hour] = float(proba[classes.index(1)]) if 1 in classes else 0.5
            else:
                scores[hour] = float(model.predict(sample)[0])
        return scores

    counts = {h: [0, 0] for h in range(24)}
    sessions = db.query(models.StudySession).filter(models.StudySession.status.in_(["completed", "missed"])).all()
    for s in sessions:
        start = s.actual_start or s.scheduled_start
        counts[start.hour][1] += 1
        if s.status == "completed":
            counts[start.hour][0] += 1
    for hour, (good, total) in counts.items():
        scores[hour] = (good / total) if total else 0.5
    return scores
