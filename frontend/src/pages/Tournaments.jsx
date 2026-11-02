import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, CalendarDays, Pencil, Plus, Trophy, UserPlus, X } from "lucide-react";
import { api } from "../services/api";
import {
  DataTable,
  ErrorState,
  formatDate,
  LoadingState,
  PageHeading,
  Panel,
  StatusBadge,
} from "../components/ui";
import { ManagementModal, Notice } from "../components/ManagementModal";

const EMPTY_FORM = {
  sport_id: "",
  name: "",
  competition_format: "team",
  season: "",
  start_date: "",
  end_date: "",
  status: "planned",
  is_published: false,
  description: "",
  points_for_win: "3",
  points_for_draw: "1",
  points_for_loss: "0",
};

const STATUSES = ["planned", "registration", "in_progress", "completed"];

function TournamentForm({ form, setForm, sports, editing, saving, error, onSubmit, onCancel }) {
  return (
    <form className="management-form-grid" onSubmit={onSubmit}>
      <label>Tournament name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} maxLength="150" required /></label>
      <label>Sport<select value={form.sport_id} onChange={(event) => setForm((current) => ({ ...current, sport_id: event.target.value }))} required><option value="">Select sport</option>{sports.map((sport) => <option value={sport.sport_id} key={sport.sport_id}>{sport.name}</option>)}</select></label>
      <label>Format<select value={form.competition_format} onChange={(event) => setForm((current) => ({ ...current, competition_format: event.target.value }))}><option value="team">Team</option><option value="individual">Individual</option></select></label>
      <label>Season<input value={form.season} onChange={(event) => setForm((current) => ({ ...current, season: event.target.value }))} maxLength="40" required /></label>
      <label>Start date<input type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} required /></label>
      <label>End date<input type="date" min={form.start_date || undefined} value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} required /></label>
      {!editing && <label>Status<select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}>{STATUSES.map((status) => <option value={status} key={status}>{status.replaceAll("_", " ")}</option>)}</select></label>}
      <label className="field-wide checkbox-field"><input type="checkbox" checked={form.is_published} onChange={(event) => setForm((current) => ({ ...current, is_published: event.target.checked }))} /> Published for public viewing</label>
      <label className="field-wide">Description<textarea value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
      {form.competition_format === "team" && (
        <>
          <label>Points per win<input type="number" min="0" max="999999.99" step="0.01" value={form.points_for_win} onChange={(event) => setForm((current) => ({ ...current, points_for_win: event.target.value }))} /></label>
          <label>Points per draw<input type="number" min="0" max="999999.99" step="0.01" value={form.points_for_draw} onChange={(event) => setForm((current) => ({ ...current, points_for_draw: event.target.value }))} /></label>
          <label>Points per loss<input type="number" min="0" max="999999.99" step="0.01" value={form.points_for_loss} onChange={(event) => setForm((current) => ({ ...current, points_for_loss: event.target.value }))} /></label>
        </>
      )}
      {error && <div className="field-wide form-error" role="alert">{error}</div>}
      <div className="field-wide form-actions"><button type="button" className="button button-secondary" onClick={onCancel}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create tournament"}</button></div>
    </form>
  );
}

export default function Tournaments() {
  const [tournaments, setTournaments] = useState([]);
  const [sports, setSports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [tournamentData, sportData] = await Promise.all([
        api.tournaments({ include_unpublished: true }),
        api.sports(),
      ]);
      setTournaments(tournamentData.items);
      setSports(sportData.items);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function openForm(tournament = null) {
    setEditing(tournament);
    setFormError("");
    setForm(tournament ? {
      sport_id: String(tournament.sport_id),
      name: tournament.tournament_name,
      competition_format: tournament.competition_format,
      season: tournament.season,
      start_date: String(tournament.start_date).slice(0, 10),
      end_date: String(tournament.end_date).slice(0, 10),
      status: tournament.tournament_status,
      is_published: Boolean(tournament.is_published),
      description: tournament.description || "",
      points_for_win: tournament.points_for_win ?? "3",
      points_for_draw: tournament.points_for_draw ?? "1",
      points_for_loss: tournament.points_for_loss ?? "0",
    } : EMPTY_FORM);
    setFormOpen(true);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    const payload = {
      sport_id: Number(form.sport_id),
      name: form.name.trim(),
      competition_format: form.competition_format,
      season: form.season.trim(),
      start_date: form.start_date,
      end_date: form.end_date,
      ...(editing ? {} : { status: form.status }),
      is_published: form.is_published,
      description: form.description.trim() || null,
      ...(form.competition_format === "team" ? {
        scoring_rules: {
          points_for_win: Number(form.points_for_win),
          points_for_draw: Number(form.points_for_draw),
          points_for_loss: Number(form.points_for_loss),
        },
      } : {}),
    };
    try {
      if (editing) await api.updateTournament(editing.tournament_id, payload);
      else await api.createTournament(payload);
      setNotice({ tone: "success", text: editing ? "Tournament updated." : "Tournament created." });
      setFormOpen(false);
      await load();
    } catch (requestError) {
      setFormError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function cancel(tournament) {
    if (!window.confirm(`Cancel ${tournament.tournament_name}? Scheduled fixtures will also be cancelled.`)) return;
    try {
      await api.cancelTournament(tournament.tournament_id);
      setNotice({ tone: "success", text: "Tournament cancelled." });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function changeStatus(tournament, status) {
    try {
      await api.updateTournamentStatus(tournament.tournament_id, status);
      setNotice({ tone: "success", text: `Tournament status changed to ${status.replaceAll("_", " ")}.` });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
      await load();
    }
  }

  const columns = [
    { key: "tournament_name", label: "Tournament", render: (row) => <div className="person-cell"><span className="avatar avatar-amber"><Trophy size={17} /></span><div><Link className="table-primary-link" to={`/tournaments/${row.tournament_id}?include_unpublished=true`}>{row.tournament_name}</Link><span>{row.season} · {row.is_published ? "Published" : "Unpublished"}</span></div></div> },
    { key: "sport_name", label: "Sport" },
    { key: "competition_format", label: "Format", render: (row) => <span className="format-label">{row.competition_format}</span> },
    { key: "dates", label: "Dates", render: (row) => <span className="date-range"><CalendarDays size={15} />{formatDate(row.start_date)} – {formatDate(row.end_date)}</span> },
    { key: "tournament_status", label: "Status", render: (row) => <select className="status-control" aria-label={`Set status for ${row.tournament_name}`} value={row.tournament_status} onChange={(event) => changeStatus(row, event.target.value)} disabled={row.tournament_status === "cancelled"}>{[...STATUSES, "cancelled"].map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select> },
    { key: "action", label: "Actions", render: (row) => <div className="row-actions"><button className="icon-button" title="Edit tournament" aria-label="Edit tournament" onClick={() => openForm(row)}><Pencil size={15} /></button><Link className="row-action" to={`/tournaments/${row.tournament_id}?include_unpublished=true`}>Details <ArrowRight size={15} /></Link>{!["completed", "cancelled"].includes(row.tournament_status) && <button className="icon-button" title="Cancel tournament" aria-label="Cancel tournament" onClick={() => cancel(row)}><X size={15} /></button>}</div> },
  ];

  return (
    <>
      <PageHeading eyebrow="COMPETITION" title="Tournaments" description="Manage published and unpublished events, registration, and scoring rules." action={<button className="button button-primary" onClick={() => openForm()}><Plus size={16} /> Create tournament</button>} />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      <Panel title="Tournament directory" action={<span className="record-count">{tournaments.length} tournaments</span>}>
        {loading ? <LoadingState label="Loading tournaments…" /> : error ? <ErrorState error={error} onRetry={load} /> : <DataTable columns={columns} rows={tournaments.map((row) => ({ ...row, id: row.tournament_id }))} emptyTitle="No tournaments" />}
      </Panel>
      <p className="page-footnote">Maximum registration capacity and a separate deadline are not available in the existing database schema.</p>
      {formOpen && <ManagementModal title={editing ? "Edit tournament" : "Create tournament"} onClose={() => setFormOpen(false)}><TournamentForm form={form} setForm={setForm} sports={sports} editing={editing} saving={saving} error={formError} onSubmit={submit} onCancel={() => setFormOpen(false)} /></ManagementModal>}
    </>
  );
}

export function TournamentDetails() {
  const { tournamentId } = useParams();
  const [searchParams] = useSearchParams();
  const includeUnpublished = searchParams.get("include_unpublished") === "true";
  const [data, setData] = useState(null);
  const [teams, setTeams] = useState([]);
  const [teamId, setTeamId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [registering, setRegistering] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [tournamentData, teamsData] = await Promise.all([
        api.tournament(tournamentId, includeUnpublished ? { include_unpublished: true } : {}),
        api.teams(),
      ]);
      setData(tournamentData);
      setTeams(teamsData.items);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [includeUnpublished, tournamentId]);

  useEffect(() => { load(); }, [load]);
  const tournament = data?.tournament;
  const participants = data?.participants || [];

  async function registerTeam(event) {
    event.preventDefault();
    setRegistering(true);
    try {
      await api.registerTeam(tournamentId, Number(teamId));
      setTeamId("");
      await load();
      setNotice({ tone: "success", text: "Team registered for this tournament." });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setRegistering(false);
    }
  }

  const registeredTeamIds = new Set(participants.map((participant) => participant.team_id).filter(Boolean));
  const eligibleTeams = teams.filter((team) =>
    team.sport_id === tournament?.sport_id && !registeredTeamIds.has(team.team_id),
  );

  return (
    <>
      <PageHeading
        eyebrow="TOURNAMENT DETAILS"
        title={tournament?.tournament_name || "Tournament"}
        description={tournament ? `${tournament.sport_name} · ${tournament.season}` : "Event information and registered participants."}
        action={<Link className="button button-secondary" to="/tournaments">All tournaments</Link>}
      />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      {loading ? <LoadingState label="Loading tournament…" /> : error ? <ErrorState error={error} onRetry={load} /> : tournament && (
        <>
          <div className="tournament-summary">
            <div className="summary-main"><span className="summary-icon"><Trophy size={22} /></span><div><span className="eyebrow">SPORT · {tournament.sport_name} · {tournament.is_published ? "PUBLISHED" : "UNPUBLISHED"}</span><h2>{tournament.tournament_name}</h2><p>{tournament.description || "No additional tournament description."}</p></div></div>
            <StatusBadge value={tournament.tournament_status} />
          </div>
          <div className="summary-facts">
            <div><span>Season</span><strong>{tournament.season}</strong></div>
            <div><span>Competition format</span><strong className="capitalize">{tournament.competition_format}</strong></div>
            <div><span>Start date</span><strong>{formatDate(tournament.start_date)}</strong></div>
            <div><span>End date</span><strong>{formatDate(tournament.end_date)}</strong></div>
            <div><span>Registered participants</span><strong>{participants.filter((row) => row.entry_status === "registered").length}</strong></div>
          </div>
          {includeUnpublished && tournament.competition_format === "team" && tournament.tournament_status === "registration" && (
            <Panel title="Register a team">
              <form className="inline-form" onSubmit={registerTeam}>
                <label>Eligible team<select value={teamId} onChange={(event) => setTeamId(event.target.value)} required><option value="">Select team for {tournament.sport_name}</option>{eligibleTeams.map((team) => <option value={team.team_id} key={team.team_id}>{team.name} · {team.department_name}</option>)}</select></label>
                <button className="button button-primary" disabled={registering || !eligibleTeams.length}><UserPlus size={15} /> {registering ? "Registering…" : "Register team"}</button>
                {!eligibleTeams.length && <span className="compact-help">No eligible unregistered active teams found.</span>}
              </form>
            </Panel>
          )}
          <Panel title={includeUnpublished ? "Tournament entries" : "Registered participants"} action={<Link className="text-link" to={`/standings?tournament_id=${tournament.tournament_id}`}>View standings <ArrowRight size={15} /></Link>}>
            <DataTable
              emptyTitle="No registered participants"
              rows={participants.map((row) => ({ ...row, id: row.entry_id }))}
              columns={[
                { key: "participant", label: "Participant", render: (row) => <div className="person-cell"><span className="avatar">{(row.team_name || row.player_name || "—").slice(0, 2).toUpperCase()}</span><div><strong>{row.team_name || row.player_name || "Participant unavailable"}</strong><span>{row.participant_type} · entry #{row.entry_id}</span></div></div> },
                ...(includeUnpublished ? [{ key: "entry_status", label: "Entry status", render: (row) => <StatusBadge value={row.entry_status} /> }] : []),
              ]}
            />
          </Panel>
          {!includeUnpublished && <p className="page-footnote">Published tournament details are read-only. Administration tools are available through the tournament directory.</p>}
        </>
      )}
    </>
  );
}
