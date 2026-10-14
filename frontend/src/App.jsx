import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Courses from "./pages/Courses.jsx";
import Tasks from "./pages/Tasks.jsx";
import Availability from "./pages/Availability.jsx";
import Schedule from "./pages/Schedule.jsx";
import Reviews from "./pages/Reviews.jsx";
import Progress from "./pages/Progress.jsx";

const links = [
  ["/", "Dashboard"],
  ["/tasks", "Tasks"],
  ["/schedule", "Schedule"],
  ["/courses", "Courses"],
  ["/availability", "Free time"],
  ["/reviews", "Reviews"],
  ["/progress", "Progress"],
];

export default function App() {
  return (
    <div className="app">
      <aside className="nav">
        <div>
          <h1 className="brand">StudyFlow</h1>
          <p className="tagline">Plan. Review. Keep going.</p>
        </div>
        {links.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === "/"}>
            {label}
          </NavLink>
        ))}
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/courses" element={<Courses />} />
          <Route path="/availability" element={<Availability />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/progress" element={<Progress />} />
        </Routes>
      </main>
    </div>
  );
}
