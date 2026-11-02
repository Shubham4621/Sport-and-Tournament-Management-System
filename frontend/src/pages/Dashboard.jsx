import { useEffect, useState } from "react";
import { ArrowRight, CalendarDays, CircleDot, Clock3, Trophy, Users, UsersRound, Volleyball, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import {
  DataTable,
  ErrorState,
  formatDate,
  formatDateTime,
  LoadingState,
  PageHeading,
  Panel,
  StatusBadge,
} from "../components/ui";

function StatCard({ label, value, note, icon: Icon, tone }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon stat-icon-${tone}`}><Icon size={19} /></div>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value ?? "—"}</strong>
      <span className="stat-note">{note}</span>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [stats, sports, matches, results] = await Promise.all([
        api.dashboardStats(),
        api.sports({ include_inactive: true }),
        api.matches({ include_unpublished: true }),
        api.matchResultsReport({ include_unpublished: true }),
      ]);
      setData({
        stats: stats.stats,
        sports: sports.items,
        matches: matches.items,
        results: results.items,
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingState label="Loading your dashboard…" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  const { stats, sports, matches, results } = data;
  const now = Date.now();
  const upcomingMatches = matches
    .filter((match) => match.match_status === "scheduled" && match.scheduled_at && new Date(match.scheduled_at).getTime() >= now)
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));
  const recentMatches = [...upcomingMatches].slice(0, 5);
  const recentResults = [...results]
    .sort((a, b) => new Date(b.declared_at) - new Date(a.declared_at))
    .slice(0, 8);
  const cards = [
    { label: "Total sports", value: sports.length, note: "All catalog sports", icon: Volleyball, tone: "blue" },
    { label: "Total players", value: stats?.total_players, note: "Player profiles", icon: Users, tone: "violet" },
    { label: "Total teams", value: stats?.total_teams, note: "Active and inactive", icon: UsersRound, tone: "green" },
    { label: "Total tournaments", value: stats?.total_tournaments, note: "Published and unpublished", icon: Trophy, tone: "amber" },
    { label: "Upcoming matches", value: upcomingMatches.length, note: "Scheduled from today onward", icon: CalendarDays, tone: "teal" },
    { label: "Completed matches", value: stats?.completed_matches, note: "All tournament matches", icon: CheckCircle2, tone: "green" },
  ];

  return (
    <>
      <PageHeading
        eyebrow="OVERVIEW"
        title="Dashboard"
        description="Current player, team, tournament, and match activity across the system."
        action={<span className="date-chip"><Clock3 size={15} /> Updated just now</span>}
      />
      <div className="stats-grid">
        {cards.map((card) => <StatCard key={card.label} {...card} />)}
      </div>
      <div className="dashboard-grid">
        <Panel title="Recent results" action={<Link className="text-link" to="/matches">View matches <ArrowRight size={15} /></Link>}>
          <DataTable
            emptyTitle="No completed match results"
            rows={recentResults.map((row) => ({
              ...row,
              id: `${row.match_id}-${row.entry_id}`,
            }))}
            columns={[
              { key: "tournament_name", label: "Tournament", render: (row) => <Link className="table-primary-link" to={`/matches/${row.match_id}`}>{row.tournament_name}</Link> },
              { key: "participant", label: "Participant", render: (row) => row.team_name || row.player_name || `Entry ${row.entry_id}` },
              { key: "outcome", label: "Result", render: (row) => <StatusBadge value={row.outcome} /> },
              { key: "declared_at", label: "Recorded", render: (row) => formatDateTime(row.declared_at) },
            ]}
          />
        </Panel>
        <Panel title="Upcoming matches" action={<Link className="text-link" to="/matches">View all <ArrowRight size={15} /></Link>}>
          {recentMatches.length ? (
            <div className="recent-list">
              {recentMatches.map((match) => (
                <Link className="recent-match" to={`/matches/${match.match_id}`} key={match.match_id}>
                  <div className="recent-match-icon"><CircleDot size={17} /></div>
                  <div className="recent-match-main">
                    <strong>{match.tournament_name}</strong>
                    <span>{match.participants || `Match ${match.match_number}`} · {match.sport_name}</span>
                  </div>
                  <div className="recent-match-meta">
                    <StatusBadge value={match.match_status} />
                    <span>{formatDateTime(match.scheduled_at)}</span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="compact-empty">No upcoming scheduled matches.</div>
          )}
        </Panel>
      </div>
      <div className="dashboard-footnote">
        <span><Trophy size={15} /> Counts include published and unpublished tournament records.</span>
        <span><CalendarDays size={15} /> Upcoming matches are scheduled fixtures with a future date/time.</span>
      </div>
    </>
  );
}
