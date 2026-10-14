import { useEffect, useState } from "react";
import { api } from "../api";

const COLORS = ["#2F6F4E", "#C45C26", "#3D5A80", "#7A4E9A", "#B0892C", "#8C3A3A"];

export default function Courses() {
  const [courses, setCourses] = useState([]);
  const [form, setForm] = useState({ name: "", code: "", credits: 3, color: COLORS[0] });

  const load = () => api.get("/api/courses").then(setCourses);
  useEffect(() => {
    load();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    await api.post("/api/courses", form);
    setForm({ name: "", code: "", credits: 3, color: COLORS[0] });
    load();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Courses</h2>
          <p>Group assignments and exams by module.</p>
        </div>
      </div>
      <div className="grid two">
        <form className="card stack" onSubmit={submit}>
          <label>
            Name
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Code
            <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          </label>
          <label>
            Credits
            <input
              type="number"
              min="1"
              value={form.credits}
              onChange={(e) => setForm({ ...form, credits: Number(e.target.value) })}
            />
          </label>
          <div className="row">
            {COLORS.map((c) => (
              <button
                type="button"
                key={c}
                onClick={() => setForm({ ...form, color: c })}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: c,
                  border: form.color === c ? "3px solid #1c241c" : "0",
                }}
              />
            ))}
          </div>
          <button className="btn" type="submit">
            Add course
          </button>
        </form>
        <div className="grid cards">
          {courses.map((c) => (
            <div className="card" key={c.id}>
              <h3>
                <span className="course-dot" style={{ background: c.color }} />
                {c.name}
              </h3>
              <p className="muted">
                {c.code || "No code"} · {c.credits} credits
              </p>
              <button className="btn secondary" onClick={() => api.del(`/api/courses/${c.id}`).then(load)}>
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
