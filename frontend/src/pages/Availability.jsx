import { useEffect, useState } from "react";
import { api } from "../api";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Availability() {
  const [slots, setSlots] = useState([]);
  const [form, setForm] = useState({ weekday: 0, start_time: "09:00", end_time: "11:00", label: "" });

  const load = () => api.get("/api/availability").then(setSlots);
  useEffect(() => {
    load();
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    await api.post("/api/availability", {
      ...form,
      weekday: Number(form.weekday),
      start_time: form.start_time.length === 5 ? `${form.start_time}:00` : form.start_time,
      end_time: form.end_time.length === 5 ? `${form.end_time}:00` : form.end_time,
    });
    load();
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Weekly free time</h2>
          <p>The scheduler only places work inside these recurring windows.</p>
        </div>
      </div>
      <div className="grid two">
        <form className="card stack" onSubmit={submit}>
          <label>
            Day
            <select value={form.weekday} onChange={(e) => setForm({ ...form, weekday: e.target.value })}>
              {DAYS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
          </label>
          <label>
            Start
            <input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
          </label>
          <label>
            End
            <input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
          </label>
          <label>
            Label
            <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
          </label>
          <button className="btn">Add slot</button>
        </form>
        <div>
          {slots.map((s) => (
            <div className="card row" key={s.id} style={{ marginBottom: 10, justifyContent: "space-between" }}>
              <div>
                <strong>
                  {DAYS[s.weekday]} {String(s.start_time).slice(0, 5)}–{String(s.end_time).slice(0, 5)}
                </strong>
                <div className="muted">{s.label || "Study window"}</div>
              </div>
              <button className="btn secondary" onClick={() => api.del(`/api/availability/${s.id}`).then(load)}>
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
