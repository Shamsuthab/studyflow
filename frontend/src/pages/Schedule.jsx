import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function startOfWeek(d) {
  const date = new Date(d);
  const day = (date.getDay() + 6) % 7;
  date.setDate(date.getDate() - day);
  date.setHours(0, 0, 0, 0);
  return date;
}

export default function Schedule() {
  const [sessions, setSessions] = useState([]);
  const [msg, setMsg] = useState("");

  const load = () => api.get("/api/schedule?days=14").then(setSessions);
  useEffect(() => {
    load();
  }, []);

  const weekStart = startOfWeek(new Date());
  const columns = useMemo(() => {
    const cols = Array.from({ length: 7 }, (_, i) => {
      const day = new Date(weekStart);
      day.setDate(weekStart.getDate() + i);
      return { day, items: [] };
    });
    for (const s of sessions) {
      const start = new Date(s.scheduled_start);
      const idx = Math.floor((start - weekStart) / 86400000);
      if (idx >= 0 && idx < 7) cols[idx].items.push(s);
    }
    return cols;
  }, [sessions, weekStart]);

  const complete = async (id) => {
    await api.post(`/api/sessions/${id}/complete`, {});
    setMsg("Session logged. Remaining work was rescheduled.");
    load();
  };

  const miss = async (id) => {
    await api.post(`/api/sessions/${id}/miss`);
    setMsg("Marked missed. The planner shifted leftover effort.");
    load();
  };

  const notify = () => {
    if (!("Notification" in window)) return;
    Notification.requestPermission().then((perm) => {
      if (perm === "granted") {
        const next = sessions.find((s) => s.status === "scheduled");
        if (next) {
          new Notification("StudyFlow reminder", {
            body: `${next.task_title} · ${new Date(next.scheduled_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
          });
        }
      }
    });
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>This week</h2>
          <p>Rule-based packing before each deadline, biased toward your productive hours.</p>
        </div>
        <div className="row">
          <button className="btn secondary" onClick={notify}>
            Enable reminders
          </button>
          <button
            className="btn"
            onClick={() => api.post("/api/schedule/replan").then(() => { setMsg("Schedule rebuilt."); load(); })}
          >
            Replan now
          </button>
        </div>
      </div>
      {msg && <p className="toast">{msg}</p>}
      <div className="week">
        {columns.map((col, i) => (
          <div className="day-col" key={i}>
            <h4>
              {DAYS[i]} {col.day.getDate()}
            </h4>
            {col.items.map((s) => (
              <div className="block" key={s.id} style={{ background: s.course_color || "#2F6F4E", opacity: s.status === "scheduled" ? 1 : 0.55 }}>
                <strong>{s.task_title}</strong>
                <small>
                  {new Date(s.scheduled_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  {" · "}
                  {s.planned_minutes}m · {s.status}
                </small>
                {s.status === "scheduled" && (
                  <div className="row" style={{ marginTop: 6 }}>
                    <button className="btn ghost" onClick={() => complete(s.id)}>
                      Done
                    </button>
                    <button className="btn secondary" onClick={() => miss(s.id)}>
                      Missed
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
