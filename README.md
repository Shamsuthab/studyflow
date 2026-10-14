# StudyFlow

A smart study planner for university students: deadline-aware scheduling, spaced-repetition reviews, and motivation (streaks, daily goals, badges). An optional decision-tree model learns which hours of day tend to produce completed sessions and biases future timetables toward those hours.

## Stack

- **Frontend:** React + Vite (responsive web UI)
- **Backend:** FastAPI REST API
- **Database:** SQLite (SQLAlchemy)
- **Scheduler:** rule-based packing of remaining effort into weekly free-time slots
- **ML:** scikit-learn `DecisionTreeClassifier` on logged sessions

## Run locally

```bash
# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --port 8000

# frontend (another terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` to the backend.

## How scheduling works

1. Pending tasks are scored by **urgency** (time until deadline), **priority**, **difficulty**, and remaining effort.
2. Recurring free-time slots are expanded over the coming weeks.
3. Work is packed into 25–90 minute blocks **before each deadline**.
4. If the productivity model is trained, higher-scoring hours are preferred.
5. Completing a session late, missing a block, adding a task, or changing availability **rebuilds** future sessions.

Completing a task creates review reminders at **1, 3, 7, and 14 days**.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
```
