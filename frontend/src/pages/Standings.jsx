import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Medal, Trophy } from "lucide-react";
import { api } from "../services/api";
import { DataTable, ErrorState, LoadingState, PageHeading, Panel } from "../components/ui";

function displayPoints(value) {
  return value == null ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function Standings() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tournaments, setTournaments] = useState([]);
  const [selectedId, setSelectedId] = useState(searchParams.get("tournament_id") || "");
  const [rows, setRows] = useState([]);
  const [loadingTournaments, setLoadingTournaments] = useState(true);
  const [loadingStandings, setLoadingStandings] = useState(false);
  const [error, setError] = useState("");
  const [tournamentError, setTournamentError] = useState("");
  const [refreshVersion, setRefreshVersion] = useState(0);

  useEffect(() => {
    api.tournaments()
      .then((response) => {
        setTournaments(response.items);
        const requested = searchParams.get("tournament_id");
        const initial = response.items.some((item) => String(item.tournament_id) === requested)
          ? requested
          : String(response.items[0]?.tournament_id || "");
        setSelectedId(initial);
      })
      .catch((requestError) => setTournamentError(requestError.message))
      .finally(() => setLoadingTournaments(false));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setRows([]);
      return;
    }
    let active = true;
    setLoadingStandings(true);
    setError("");
    api.standings(selectedId)
      .then((response) => { if (active) setRows(response.standings); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoadingStandings(false); });
    setSearchParams({ tournament_id: selectedId }, { replace: true });
    return () => { active = false; };
  }, [selectedId, setSearchParams, refreshVersion]);

  const selectedTournament = tournaments.find((item) => String(item.tournament_id) === selectedId);
  const columns = [
    { key: "standings_rank", label: "Rank", render: (row) => <span className={`rank-value ${row.standings_rank <= 3 ? `rank-${row.standings_rank}` : ""}`}>{row.standings_rank <= 3 && <Medal size={15} />}{row.standings_rank}</span> },
    { key: "participant", label: "Participant", render: (row) => <div className="person-cell"><span className="avatar avatar-amber">{(row.team_name || row.player_name || "—").slice(0, 2).toUpperCase()}</span><div><strong>{row.team_name || row.player_name || "Participant unavailable"}</strong><span>{row.team_id ? "Team" : "Individual"} · entry #{row.entry_id}</span></div></div> },
    { key: "played_matches", label: "Played" },
    { key: "wins", label: "Wins" },
    { key: "draws", label: "Draws" },
    { key: "losses", label: "Losses" },
    { key: "total_points", label: "Points", render: (row) => <strong className="points-value">{displayPoints(row.total_points)}</strong> },
    { key: "best_result_rank", label: "Best rank", render: (row) => row.best_result_rank ?? "—" },
  ];

  return (
    <>
      <PageHeading eyebrow="TOURNAMENT PERFORMANCE" title="Standings" description="Live rankings calculated from completed match results." />
      <Panel title="Select tournament" className="standings-filter-panel">
        {loadingTournaments ? <LoadingState label="Loading tournaments…" /> : tournamentError ? <ErrorState error={tournamentError} /> : tournaments.length ? (
          <div className="standings-selector">
            <div className="selector-icon"><Trophy size={19} /></div>
            <label htmlFor="standings-tournament">Published tournament</label>
            <select id="standings-tournament" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              {tournaments.map((tournament) => <option key={tournament.tournament_id} value={tournament.tournament_id}>{tournament.tournament_name} · {tournament.season}</option>)}
            </select>
            {selectedTournament && <span className="format-label capitalize">{selectedTournament.competition_format}</span>}
          </div>
        ) : <div className="compact-empty">No published tournaments have standings.</div>}
      </Panel>
      {selectedTournament && (
        <Panel title={`${selectedTournament.tournament_name} standings`} action={<span className="record-count">{rows.length} entries</span>}>
          {loadingStandings ? <LoadingState label="Calculating standings…" /> : error ? <ErrorState error={error} onRetry={() => setRefreshVersion((version) => version + 1)} /> : (
            <>
              <DataTable columns={columns} rows={rows.map((row) => ({ ...row, id: row.entry_id }))} emptyTitle="No standings available" />
              {selectedTournament.competition_format === "individual" && <p className="page-footnote">Individual tournament points are not defined by the database scoring rules; rank and recorded outcomes are shown instead.</p>}
            </>
          )}
        </Panel>
      )}
      <div className="information-banner">
        <Medal size={18} />
        <p>Standings are provided by the existing database procedure and include completed match results only. Points may be blank for individual tournaments.</p>
      </div>
    </>
  );
}
