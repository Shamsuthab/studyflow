"""Learn preferred study hours from completed sessions.

Uses a decision tree when enough labelled sessions exist. Accuracy is reported
on a held-out test split so the evaluation chapter is honest. If the split is
too small, the code falls back to a completion-rate histogram by hour of day.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy.orm import Session

from .. import models

MODEL_DIR = Path(__file__).resolve().parent.parent.parent
MIN_SAMPLES = 8


def _model_path(user_id: int) -> Path:
    return MODEL_DIR / f"productivity_model_{user_id}.joblib"
    

def _features(hour: int, weekday: int, planned: int) -> list[float]:
    return [hour, weekday, planned, np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)]


def _labelled(db: Session, user_id: int) -> tuple[np.ndarray, np.ndarray]:

    rows = (
        db.query(models.StudySession)
        .join(models.Task)
        .filter(models.Task.user_id == user_id)
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

def _settings(db: Session, user_id: int) -> models.AppSettings:
    settings = db.query(models.AppSettings).filter(models.AppSettings.user_id == user_id).first()
    if settings is None:
        settings = models.AppSettings(user_id=user_id)
        db.add(settings)
        db.flush()
    return settings

    
def train_model(db: Session, user_id: int) -> dict:
    X, y = _labelled(db, user_id)
    settings = _settings(db, user_id)
    path = _model_path(user_id)
    
    if len(y) < MIN_SAMPLES or len(set(y.tolist())) < 2:
        settings.ml_accuracy = None
         settings.ml_train_accuracy = None
        settings.ml_test_accuracy = None
        db.commit()
        if path.exists():
            path.unlink()
        return {"ready": False, "samples": int(len(y)), "train_accuracy": None, "test_accuracy": None}

    stratify = y if min(int((y == 0).sum()), int((y == 1).sum())) >= 2 else None
    test_size = 0.3 if len(y) >= 12 else 0.25
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )
    model = DecisionTreeClassifier(max_depth=4, min_samples_leaf=2, random_state=42)
    model.fit(X_train, y_train)
    train_acc = float(model.score(X_train, y_train))
    test_acc = float(model.score(X_test, y_test)) if len(y_test) else train_acc
    joblib.dump(model, path)
    settings.ml_train_accuracy = round(train_acc, 3)
    settings.ml_test_accuracy = round(test_acc, 3)
    settings.ml_accuracy = settings.ml_test_accuracy
    db.commit()
    return {
        "ready": True,
        "samples": int(len(y)),
        "train_accuracy": settings.ml_train_accuracy,
        "test_accuracy": settings.ml_test_accuracy,
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
    }


    def hour_scores(db: Session, user_id: int) -> dict[int, float]:
    X, y = _labelled(db, user_id)
    scores = {h: 0.5 for h in range(24)}
    if len(y) == 0:
        return scores

     path = _model_path(user_id)
    if path.exists() and len(y) >= MIN_SAMPLES:
        model = joblib.load(path)
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
    sessions = (
        db.query(models.StudySession)
        .join(models.Task)
        .filter(models.Task.user_id == user_id)
        .filter(models.StudySession.status.in_(["completed", "missed"]))
        .all()
    )
    for s in sessions:
        start = s.actual_start or s.scheduled_start
        counts[start.hour][1] += 1
        if s.status == "completed":
            counts[start.hour][0] += 1
    for hour, (good, total) in counts.items():
        scores[hour] = (good / total) if total else 0.5
    return scores
