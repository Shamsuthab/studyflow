import { useEffect, useState } from "react";
import { api } from "../api";

const empty = {
  course_id: "",
  title: "",
  description: "",
  deadline: "",
  estimated_minutes: 120,
  difficulty: 3,
  priority: 3,
};

export default function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [courses, setCourses] = useState([]);
  const [form, setForm] = useState(empty);

  const load = async () => {
    const [t, c] = await Promise.all([api.get("/api/tasks"), api.get("/api/courses")]);
    setTasks(t);
    setCourses(c);
    if (!form.course_id && c[0]) setForm((f) => ({ ...f, course_id: c[0].id }));
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    await api.post("/api/tasks", {
      ...form,
      course_id: Number(form.course_id),
      deadline: new Date(form.deadline).toISOString(),
    });
    setForm({ ...empty, course_id: form.course_id });
    load();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Tasks & deadlines</h2>
          <p>New work is packed into free slots automatically. Late completions trigger a replan.</p>
        </div>
      </div>
      <div className="grid two">
        <form className="card stack" onSubmit={submit}>
          <label>
            Course
            <select value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })}>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Title
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </label>
          <label>
            Deadline
            <input
              type="datetime-local"
              value={form.deadline}
              onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              required
            />
          </label>
          <label>
            Estimated minutes
            <input
              type="number"
              min="25"
              value={form.estimated_minutes}
              onChange={(e) => setForm({ ...form, estimated_minutes: Number(e.target.value) })}
            />
          </label>
          <div className="row">
            <label>
              Priority 1–5
              <input
                type="number"
                min="1"
                max="5"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
              />
            </label>
            <label>
              Difficulty 1–5
              <input
                type="number"
                min="1"
                max="5"
                value={form.difficulty}
                onChange={(e) => setForm({ ...form, difficulty: Number(e.target.value) })}
              />
            </label>
          </div>
          <label>
            Notes
            <textarea rows="3" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <button className="btn" type="submit" disabled={!courses.length}>
            Add & schedule
          </button>
        </form>
        <div>
          {tasks.map((t) => (
            <div className="card" key={t.id} style={{ marginBottom: 12 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h3 className="task-title">{t.title}</h3>
                <span className={`badge ${t.status}`}>{t.status}</span>
              </div>
              <p className="muted">
                <span className="course-dot" style={{ background: t.course?.color }} />
                {t.course?.name} · due {new Date(t.deadline).toLocaleString()} · {t.remaining_minutes} min left
              </p>
              <p className="muted">
                Priority {t.priority} · difficulty {t.difficulty}
              </p>
              <div className="row" style={{ marginTop: 8 }}>
                {t.status !== "completed" && (
                  <button className="btn ghost" onClick={() => api.post(`/api/tasks/${t.id}/complete`).then(load)}>
                    Mark complete
                  </button>
                )}
                <button className="btn secondary" onClick={() => api.del(`/api/tasks/${t.id}`).then(load)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
