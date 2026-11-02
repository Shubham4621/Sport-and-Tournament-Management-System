import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Matches, { MatchDetails } from "./pages/Matches";
import Standings from "./pages/Standings";
import StudentDetails from "./pages/StudentDetails";
import Students from "./pages/Students";
import Sports from "./pages/Sports";
import Teams from "./pages/Teams";
import Tournaments, { TournamentDetails } from "./pages/Tournaments";

function NotFound() {
  return (
    <div className="not-found">
      <span>404</span>
      <h1>Page not found</h1>
      <p>The page you’re looking for isn’t part of this workspace.</p>
      <a className="button button-primary" href="/">Return to dashboard</a>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="sports" element={<Sports />} />
        <Route path="students" element={<Students />} />
        <Route path="students/:studentId" element={<StudentDetails />} />
        <Route path="teams" element={<Teams />} />
        <Route path="tournaments" element={<Tournaments />} />
        <Route path="tournaments/:tournamentId" element={<TournamentDetails />} />
        <Route path="matches" element={<Matches />} />
        <Route path="matches/:matchId" element={<MatchDetails />} />
        <Route path="standings" element={<Standings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
