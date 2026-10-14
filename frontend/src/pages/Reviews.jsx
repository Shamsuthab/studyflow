import { useEffect, useState } from "react";
import { api } from "../api";

export default function Reviews() {
  const [reviews, setReviews] = useState([]);

  const load = () => api.get("/api/reviews").then(setReviews);
  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <div className="page-head">
        <div>
          <h2>Spaced repetition</h2>
          <p>After a task is finished, reviews land at 1, 3, 7 and 14 days.</p>
        </div>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Course</th>
              <th>Interval</th>
              <th>Due</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {reviews.map((r) => (
              <tr key={r.id}>
                <td>{r.task_title}</td>
                <td>{r.course_name}</td>
                <td>{r.interval_days} day</td>
                <td>{new Date(r.due_at).toLocaleString()}</td>
                <td>
                  {r.completed ? (
                    <span className="badge completed">reviewed</span>
                  ) : (
                    <button className="btn ghost" onClick={() => api.post(`/api/reviews/${r.id}/complete`).then(load)}>
                      Mark reviewed
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
