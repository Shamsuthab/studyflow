import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Dashboard() {
  const [dash, setDash] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [d, s] = await Promise.all([api.get("/api/dashboard"), api.get("/api/schedule?days=3")]);
      setDash(d);
      setSchedule(s.filter((x) => x.status === "scheduled").slice(0, 5));
    } catch (e) {
      setError("Could not reach the StudyFlow API. Start the backend on port 8000.");
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (error) return <p>{error}</p>;
  if (!dash) return <p>Loading…</p>;

  const goalPct = Math.min(100, Math.round((dash.today_minutes / dash.daily_goal_minutes) * 100) || 0);
  const hours = Object.entries(dash.hour_scores).map(([h, v]) => [Number(h), v]);

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Today’s flow</h2>
          <p>Deadlines, reviews and a schedule that reshuffles when plans slip.</p>
        </div>
        <Link className="btn" to="/schedule">
          Open schedule
        </Link>
      </div>

      <div className="grid stats">
        <div className="card stat">
          <div className="label">Study streak</div>
          <div className="value">{dash.streak}d</div>
        </div>
        <div className="card stat">
          <div className="label">Open tasks</div>
          <div className="value">{dash.pending_tasks}</div>
        </div>
        <div className="card stat">
          <div className="label">Overdue</div>
          <div className="value">{dash.overdue_tasks}</div>
        </div>
        <div className="card stat">
          <div className="label">Reviews due</div>
          <div className="value">{dash.upcoming_reviews}</div>
        </div>
      </div>

      <div className="grid two" style={{ marginTop: 16 }}>
        <div className="card">
          <h3>Daily goal</h3>
          <p className="muted">
            {dash.today_minutes} / {dash.daily_goal_minutes} minutes · {dash.week_minutes} this week
          </p>
          <div className="progress" style={{ margin: "12px 0 18px" }}>
            <i style={{ width: `${goalPct}%` }} />
          </div>
          <h3>Next sessions</h3>
          {schedule.length === 0 && <p className="muted">No upcoming blocks. Add tasks and free-time slots.</p>}
          {schedule.map((s) => (
            <div key={s.id} style={{ marginTop: 10 }}>
              <strong>{s.task_title}</strong>
              <div className="muted">
                {new Date(s.scheduled_start).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}
                {" · "}
                {s.planned_minutes} min · {s.course_name}
              </div>
            </div>
          ))}
        </div>
        <div className="card">
          <h3>Productive hours</h3>
          <p className="muted">
            {dash.ml_ready
              ? `Decision tree fitted on your logs (train accuracy ${(dash.ml_accuracy * 100).toFixed(0)}%).`
              : "Histogram fallback until enough completed/missed sessions exist."}
          </p>
          <div className="bars" style={{ marginTop: 16 }}>
            {hours.map(([h, v]) => (
              <span key={h} title={`${h}:00 · ${(v * 100).toFixed(0)}%`} style={{ height: `${Math.max(8, v * 100)}%` }} />
            ))}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            00:00 — 23:00
          </div>
          <div style={{ marginTop: 16 }}>
            {dash.badges.slice(0, 4).map((b) => (
              <span className="badge" key={b.id} style={{ margin: "0 8px 8px 0" }}>
                {b.name}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
