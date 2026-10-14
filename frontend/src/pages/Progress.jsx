import { useEffect, useState } from "react";
import { api } from "../api";

export default function Progress() {
  const [dash, setDash] = useState(null);
  const [stats, setStats] = useState([]);
  const [settings, setSettings] = useState({ daily_goal_minutes: 120, ml_enabled: true });

  const load = async () => {
    const [d, s, st] = await Promise.all([api.get("/api/dashboard"), api.get("/api/stats"), api.get("/api/settings")]);
    setDash(d);
    setStats(s);
    setSettings(st);
  };

  useEffect(() => {
    load();
  }, []);

  if (!dash) return null;
  const maxMin = Math.max(1, ...stats.map((x) => x.completed_minutes));

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Motivation</h2>
          <p>Streaks, daily goals and badges from logged sessions.</p>
        </div>
      </div>
      <div className="grid two">
        <div className="card">
          <h3>Last two weeks</h3>
          <div className="row" style={{ alignItems: "end", height: 140, marginTop: 16 }}>
            {stats.map((s) => (
              <div key={s.day} style={{ textAlign: "center" }}>
                <div
                  style={{
                    width: 18,
                    height: `${(s.completed_minutes / maxMin) * 110}px`,
                    background: "#2F6F4E",
                    borderRadius: 6,
                    margin: "0 auto 6px",
                  }}
                />
                <div className="muted">{s.day.slice(5)}</div>
              </div>
            ))}
          </div>
        </div>
        <form
          className="card stack"
          onSubmit={async (e) => {
            e.preventDefault();
            await api.patch("/api/settings", {
              daily_goal_minutes: Number(settings.daily_goal_minutes),
              ml_enabled: settings.ml_enabled,
            });
            load();
          }}
        >
          <h3>Settings</h3>
          <label>
            Daily goal (minutes)
            <input
              type="number"
              value={settings.daily_goal_minutes}
              onChange={(e) => setSettings({ ...settings, daily_goal_minutes: e.target.value })}
            />
          </label>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={settings.ml_enabled}
              onChange={(e) => setSettings({ ...settings, ml_enabled: e.target.checked })}
            />
            Bias the timetable toward predicted productive hours
          </label>
          <button className="btn" type="submit">
            Save
          </button>
          <button
            className="btn secondary"
            type="button"
            onClick={() => api.post("/api/ml/train").then(load)}
          >
            Retrain productivity model
          </button>
        </form>
      </div>
      <div className="grid cards" style={{ marginTop: 16 }}>
        {dash.badges.map((b) => (
          <div className="card" key={b.id}>
            <h3>{b.name}</h3>
            <p className="muted">{b.description}</p>
            <p className="muted">Earned {new Date(b.earned_at).toLocaleDateString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
