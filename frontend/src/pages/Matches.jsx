import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CalendarDays, MapPin, Pencil, Plus, Save, Trophy, X } from "lucide-react";
import { api } from "../services/api";
import {
  DataTable,
  ErrorState,
  formatDateTime,
  LoadingState,
  PageHeading,
  Panel,
  participantName,
  StatusBadge,
} from "../components/ui";
import { ManagementModal, Notice } from "../components/ManagementModal";

const EMPTY_SCHEDULE = {
  tournament_id: "",
  match_number: "",
  scheduled_at: "",
  stage: "",
  round_name: "",
  venue: "",
};

function ScheduleForm({ form, setForm, tournaments, entries, selectedEntries, setSelectedEntries, onTournamentChange, error, saving, onSubmit, onCancel }) {
  const teamFormat = tournaments.find((tournament) => String(tournament.tournament_id) === form.tournament_id)?.competition_format === "team";
  return (
    <form className="management-form" onSubmit={onSubmit}>
      <label>Tournament<select value={form.tournament_id} onChange={(event) => onTournamentChange(event.target.value)} required><option value="">Select a tournament</option>{tournaments.filter((row) => !["completed", "cancelled"].includes(row.tournament_status)).map((row) => <option value={row.tournament_id} key={row.tournament_id}>{row.tournament_name} · {row.season}</option>)}</select></label>
      <div className="form-field"><span>Registered participants {teamFormat ? "(select two teams)" : "(select at least two)"}</span><div className="check-list">{entries.length ? entries.map((entry) => <label key={entry.entry_id}><input type="checkbox" checked={selectedEntries.includes(entry.entry_id)} onChange={(event) => setSelectedEntries((current) => event.target.checked ? [...current, entry.entry_id] : current.filter((id) => id !== entry.entry_id))} />{entry.team_name || entry.player_name || `Entry #${entry.entry_id}`} · entry #{entry.entry_id}</label>) : <p className="compact-help">Choose a tournament with registered participants.</p>}</div></div>
      <div className="management-form-grid">
        <label>Match number<input type="number" min="1" value={form.match_number} onChange={(event) => setForm((current) => ({ ...current, match_number: event.target.value }))} required /></label>
        <label>Date &amp; time<input type="datetime-local" value={form.scheduled_at} onChange={(event) => setForm((current) => ({ ...current, scheduled_at: event.target.value }))} /></label>
        <label>Stage<input value={form.stage} onChange={(event) => setForm((current) => ({ ...current, stage: event.target.value }))} maxLength="60" placeholder="e.g. Semi-final" /></label>
        <label>Round<input value={form.round_name} onChange={(event) => setForm((current) => ({ ...current, round_name: event.target.value }))} maxLength="100" placeholder="e.g. Round 1" /></label>
        <label className="field-wide">Venue<input value={form.venue} onChange={(event) => setForm((current) => ({ ...current, venue: event.target.value }))} maxLength="200" /></label>
      </div>
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="form-actions"><button type="button" className="button button-secondary" onClick={onCancel}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Scheduling…" : "Schedule match"}</button></div>
    </form>
  );
}

export default function Matches() {
  const [matches, setMatches] = useState([]);
  const [tournaments, setTournaments] = useState([]);
  const [tournamentId, setTournamentId] = useState("");
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_SCHEDULE);
  const [entries, setEntries] = useState([]);
  const [selectedEntries, setSelectedEntries] = useState([]);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (selectedTournament = tournamentId, selectedStatus = status) => {
    setLoading(true);
    setError("");
    try {
      const [matchResponse, tournamentResponse] = await Promise.all([
        api.matches({
          include_unpublished: true,
          ...(selectedTournament ? { tournament_id: selectedTournament } : {}),
          ...(selectedStatus !== "all" ? { status: selectedStatus } : {}),
        }),
        api.tournaments({ include_unpublished: true }),
      ]);
      setMatches(matchResponse.items);
      setTournaments(tournamentResponse.items);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [status, tournamentId]);

  useEffect(() => { load("", "all"); }, []);

  async function changeScheduleTournament(id) {
    setForm((current) => ({ ...current, tournament_id: id }));
    setSelectedEntries([]);
    setEntries([]);
    if (!id) return;
    try {
      const data = await api.tournament(id, { include_unpublished: true });
      setEntries((data.participants || []).filter((entry) => entry.entry_status === "registered"));
    } catch (requestError) {
      setFormError(requestError.message);
    }
  }

  async function scheduleMatch(event) {
    event.preventDefault();
    const format = tournaments.find((row) => String(row.tournament_id) === form.tournament_id)?.competition_format;
    if (selectedEntries.length < 2 || (format === "team" && selectedEntries.length !== 2)) {
      setFormError(format === "team" ? "Select exactly two registered teams." : "Select at least two registered participants.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await api.createMatch({
        tournament_id: Number(form.tournament_id),
        match_number: Number(form.match_number),
        entry_ids: selectedEntries,
        scheduled_at: form.scheduled_at || null,
        stage: form.stage.trim() || null,
        round_name: form.round_name.trim() || null,
        venue: form.venue.trim() || null,
      });
      setFormOpen(false);
      setNotice({ tone: "success", text: "Match scheduled." });
      await load();
    } catch (requestError) {
      setFormError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  function openScheduleForm() {
    setForm(EMPTY_SCHEDULE);
    setEntries([]);
    setSelectedEntries([]);
    setFormError("");
    setFormOpen(true);
  }

  const columns = [
    { key: "fixture", label: "Fixture", render: (row) => <div><Link className="table-primary-link" to={`/matches/${row.match_id}`}>{row.tournament_name}</Link><span className="table-subtext">{row.sport_name} · Match {row.match_number}{row.stage ? ` · ${row.stage}` : ""}</span></div> },
    { key: "participants", label: "Participants", render: (row) => <span className="participant-line">{row.participants || "Participants not assigned"}</span> },
    { key: "scheduled_at", label: "Date & time", render: (row) => formatDateTime(row.scheduled_at) },
    { key: "venue", label: "Venue", render: (row) => row.venue || "—" },
    { key: "match_status", label: "Status", render: (row) => <StatusBadge value={row.match_status} /> },
    { key: "action", label: "", render: (row) => <Link className="row-action" to={`/matches/${row.match_id}`}>Manage <span aria-hidden="true">→</span></Link> },
  ];

  return (
    <>
      <PageHeading eyebrow="FIXTURES" title="Matches" description="Schedule fixtures, update results, and review match history." action={<button className="button button-primary" onClick={openScheduleForm}><Plus size={16} /> Schedule match</button>} />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      <Panel title="Match schedule" action={<span className="record-count">{matches.length} matches</span>}>
        <div className="table-toolbar match-filters">
          <label className="filter-control"><span>Tournament</span><select value={tournamentId} onChange={(event) => { setTournamentId(event.target.value); load(event.target.value, status); }}><option value="">All tournaments</option>{tournaments.map((tournament) => <option value={tournament.tournament_id} key={tournament.tournament_id}>{tournament.tournament_name}</option>)}</select></label>
          <label className="filter-control"><span>Match status</span><select value={status} onChange={(event) => { setStatus(event.target.value); load(tournamentId, event.target.value); }}><option value="all">All statuses</option><option value="scheduled">Scheduled</option><option value="live">Live</option><option value="completed">Completed</option><option value="postponed">Postponed</option><option value="cancelled">Cancelled</option></select></label>
        </div>
        {loading ? <LoadingState label="Loading match schedule…" /> : error ? <ErrorState error={error} onRetry={() => load()} /> : <DataTable columns={columns} rows={matches.map((row) => ({ ...row, id: row.match_id }))} emptyTitle="No matches match these filters" />}
      </Panel>
      {formOpen && <ManagementModal title="Schedule a match" onClose={() => setFormOpen(false)}><ScheduleForm form={form} setForm={setForm} tournaments={tournaments} entries={entries} selectedEntries={selectedEntries} setSelectedEntries={setSelectedEntries} onTournamentChange={changeScheduleTournament} error={formError} saving={saving} onSubmit={scheduleMatch} onCancel={() => setFormOpen(false)} /></ManagementModal>}
    </>
  );
}

export function MatchDetails() {
  const { matchId } = useParams();
  const [match, setMatch] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({ scheduled_at: "", stage: "", round_name: "", venue: "" });
  const [resultForm, setResultForm] = useState({});
  const [scoreForm, setScoreForm] = useState({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [matchResponse, participantResponse, resultResponse] = await Promise.all([
        api.match(matchId, { include_unpublished: true }),
        api.matchParticipants(matchId, { include_unpublished: true }),
        api.matchResults(matchId, { include_unpublished: true }),
      ]);
      setMatch(matchResponse.match);
      setParticipants(participantResponse.participants);
      setResults(resultResponse.results);
      setScheduleForm({
        scheduled_at: matchResponse.match.scheduled_at ? String(matchResponse.match.scheduled_at).replace(" ", "T").slice(0, 16) : "",
        stage: matchResponse.match.stage || "",
        round_name: matchResponse.match.round_name || "",
        venue: matchResponse.match.venue || "",
      });
      setResultForm(Object.fromEntries(participantResponse.participants.map((participant) => {
        return [participant.entry_id, {
          outcome: participant.outcome || "",
          result_rank: participant.result_rank || "",
        }];
      })));
      setScoreForm(Object.fromEntries(participantResponse.participants.map((participant) => [
        participant.entry_id,
        participant.scores?.length
          ? participant.scores.map((score) => ({
              segment_number: score.segment_number,
              segment_label: score.segment_label || "",
              numeric_value: score.numeric_value ?? "",
              text_value: score.text_value ?? "",
            }))
          : [{ segment_number: 1, segment_label: "", numeric_value: "", text_value: "" }],
      ])));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [matchId]);

  useEffect(() => { load(); }, [load]);

  const teamFormat = match?.competition_format === "team";
  const scoreRows = useMemo(() => participants.flatMap((participant) =>
    (scoreForm[participant.entry_id] || []).flatMap((score) => {
      if (score.numeric_value === "" && score.text_value === "") return [];
      return [{
        entry_id: participant.entry_id,
        segment_number: Number(score.segment_number),
        segment_label: score.segment_label.trim() || null,
        numeric_value: score.numeric_value === "" ? null : Number(score.numeric_value),
        text_value: score.text_value === "" ? null : score.text_value,
      }];
    }),
  ), [participants, scoreForm]);

  function updateResult(entryId, key, value) {
    setResultForm((current) => ({
      ...current,
      [entryId]: { ...current[entryId], [key]: value },
    }));
  }

  function updateScore(entryId, index, key, value) {
    setScoreForm((current) => ({
      ...current,
      [entryId]: current[entryId].map((score, scoreIndex) => {
        if (scoreIndex !== index) return score;
        const updated = { ...score, [key]: value };
        if (key === "numeric_value" && value !== "") updated.text_value = "";
        if (key === "text_value" && value !== "") updated.numeric_value = "";
        return updated;
      }),
    }));
  }

  function addScoreSegment(entryId) {
    setScoreForm((current) => {
      const currentScores = current[entryId] || [];
      const segmentNumber = Math.max(0, ...currentScores.map((score) => Number(score.segment_number) || 0)) + 1;
      return {
        ...current,
        [entryId]: [...currentScores, {
          segment_number: segmentNumber,
          segment_label: "",
          numeric_value: "",
          text_value: "",
        }],
      };
    });
  }

  async function saveSchedule(event) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.updateMatch(matchId, {
        scheduled_at: scheduleForm.scheduled_at || null,
        stage: scheduleForm.stage.trim() || null,
        round_name: scheduleForm.round_name.trim() || null,
        venue: scheduleForm.venue.trim() || null,
      });
      setScheduleOpen(false);
      setNotice({ tone: "success", text: "Match schedule updated." });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(status) {
    if (status === "cancelled" && !window.confirm("Cancel this match?")) return;
    try {
      await api.updateMatchStatus(matchId, status);
      setNotice({ tone: "success", text: `Match marked ${status}.` });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function submitResults(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    const submittedResults = participants.map((participant) => {
      const value = resultForm[participant.entry_id] || {};
      return {
        entry_id: participant.entry_id,
        outcome: value.outcome,
        result_rank: value.result_rank ? Number(value.result_rank) : null,
      };
    });
    if (submittedResults.some((row) => !row.outcome)) {
      setNotice({ tone: "error", text: "Choose an outcome for every participant." });
      setSaving(false);
      return;
    }
    try {
      await api.declareMatchResults(matchId, submittedResults, scoreRows);
      setNotice({ tone: "success", text: "Scores and results saved; match marked completed." });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setSaving(false);
    }
  }

  async function saveScoresOnly() {
    if (!scoreRows.length) {
      setNotice({ tone: "error", text: "Enter at least one score first." });
      return;
    }
    setSaving(true);
    try {
      await api.saveMatchScores(matchId, scoreRows);
      setNotice({ tone: "success", text: "Scores saved." });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setSaving(false);
    }
  }

  const outcomeOptions = teamFormat ? ["win", "loss", "draw"] : ["win", "loss", "draw", "did not start"];

  return (
    <>
      <PageHeading
        eyebrow="MATCH DETAILS"
        title={match ? `${match.tournament_name} · Match ${match.match_number}` : "Match details"}
        description={match ? `${match.sport_name} · ${match.season}` : "Fixture information and declared results."}
        action={<div className="toolbar-wrap">{match && !["completed", "cancelled"].includes(match.match_status) && <><button className="button button-secondary" onClick={() => setScheduleOpen(true)}><Pencil size={15} /> Edit schedule</button><select className="status-control" aria-label="Change match status" value={match.match_status} onChange={(event) => changeStatus(event.target.value)}><option value="scheduled">Scheduled</option><option value="live">Live</option><option value="postponed">Postponed</option><option value="cancelled">Cancelled</option></select></>}<Link className="button button-secondary" to="/matches"><ArrowLeft size={16} /> Back to matches</Link></div>}
      />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      {loading ? <LoadingState label="Loading match details…" /> : error ? <ErrorState error={error} onRetry={load} /> : match && (
        <>
          <div className="match-detail-banner">
            <div className="match-detail-title"><span className="match-detail-icon"><CalendarDays size={22} /></span><div><span className="eyebrow">{match.sport_name} · {match.competition_format}</span><h2>{match.tournament_name}</h2><p>{match.stage || match.round_name || "Tournament fixture"} · Match {match.match_number}</p></div></div>
            <StatusBadge value={match.match_status} />
          </div>
          <div className="summary-facts">
            <div><span>Scheduled</span><strong>{formatDateTime(match.scheduled_at)}</strong></div>
            <div><span>Venue</span><strong><MapPin size={15} />{match.venue || "Not announced"}</strong></div>
            <div><span>Participants</span><strong>{participants.length || match.participant_count}</strong></div>
            <div><span>Round</span><strong>{match.round_name || "—"}</strong></div>
          </div>
          <Panel title="Participants and playing squads">
            {participants.length ? (
              <div className="match-squads">
                {participants.map((participant) => (
                  <div className="match-squad" key={participant.entry_id}>
                    <strong>{participant.team_name || participant.player_name || `Entry ${participant.entry_id}`}</strong>
                    {participant.team_name ? (
                      participant.roster_players?.length ? (
                        <div className="participant-chips roster-chips">
                          {participant.roster_players.map((playerName) => <span className="participant-chip" key={playerName}>{playerName}</span>)}
                        </div>
                      ) : <span className="table-subtext">No players assigned</span>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : <div className="compact-empty">No participants have been assigned to this fixture.</div>}
          </Panel>
          <Panel title="Scores and result management" className="results-panel">
            {participants.length < 2 ? <div className="compact-empty">At least two match participants are required before recording scores or results.</div> : (
              <form className="management-form result-editor" onSubmit={submitResults}>
                {participants.map((participant) => {
                  const value = resultForm[participant.entry_id] || {};
                  return (
                    <div className="result-participant" key={participant.entry_id}>
                      <strong>{participant.team_name || participant.player_name || `Entry ${participant.entry_id}`}</strong>
                      <label>Outcome<select value={value.outcome || ""} onChange={(event) => updateResult(participant.entry_id, "outcome", event.target.value)}><option value="">Choose…</option>{outcomeOptions.map((outcome) => <option value={outcome} key={outcome}>{outcome}</option>)}</select></label>
                      {!teamFormat && <label>Result rank<input type="number" min="1" value={value.result_rank || ""} onChange={(event) => updateResult(participant.entry_id, "result_rank", event.target.value)} /></label>}
                      <div className="participant-scores">
                        {(scoreForm[participant.entry_id] || []).map((score, index) => (
                          <div className="score-segment" key={`${participant.entry_id}-${index}`}>
                            <strong>Segment {score.segment_number}</strong>
                            <label>Label<input maxLength="80" value={score.segment_label} onChange={(event) => updateScore(participant.entry_id, index, "segment_label", event.target.value)} /></label>
                            <label>Numeric score<input type="number" step="0.001" value={score.numeric_value} onChange={(event) => updateScore(participant.entry_id, index, "numeric_value", event.target.value)} /></label>
                            <label>Text score<input maxLength="255" value={score.text_value} onChange={(event) => updateScore(participant.entry_id, index, "text_value", event.target.value)} /></label>
                          </div>
                        ))}
                        <button type="button" className="button button-secondary button-small" onClick={() => addScoreSegment(participant.entry_id)} disabled={match.match_status === "completed"}>Add score segment</button>
                      </div>
                    </div>
                  );
                })}
                <p className="compact-help">Choose one score type per participant (numeric or text). Submitting results records all outcomes and marks the match completed in one transaction. Tied individual ranks are supported.</p>
                <div className="form-actions">
                  {match.match_status !== "completed" && <button type="button" className="button button-secondary" onClick={saveScoresOnly} disabled={saving}><Save size={15} /> Save scores only</button>}
                  <button className="button button-primary" disabled={saving}>{saving ? "Saving…" : match.match_status === "completed" ? "Update results" : "Declare results & complete"}</button>
                </div>
              </form>
            )}
          </Panel>
          <Panel title="Match results">
            <DataTable emptyTitle="No declared results" rows={results.map((result) => ({ ...result, id: result.entry_id }))} columns={[
              { key: "participant", label: "Participant", render: (row) => <div><strong>{participantName(row)}</strong><span className="table-subtext">{row.participant_type}</span></div> },
              { key: "outcome", label: "Outcome", render: (row) => <StatusBadge value={row.outcome} /> },
              { key: "result_rank", label: "Rank", render: (row) => row.result_rank ?? "—" },
              { key: "score_summary", label: "Score", render: (row) => row.score_summary || "—" },
              { key: "official_note", label: "Official note", render: (row) => row.official_note || "—" },
            ]} />
          </Panel>
        </>
      )}
      {scheduleOpen && (
        <ManagementModal title="Edit match schedule" onClose={() => setScheduleOpen(false)}>
          <form className="management-form-grid" onSubmit={saveSchedule}>
            <label>Date &amp; time<input type="datetime-local" value={scheduleForm.scheduled_at} onChange={(event) => setScheduleForm((current) => ({ ...current, scheduled_at: event.target.value }))} /></label>
            <label>Venue<input maxLength="200" value={scheduleForm.venue} onChange={(event) => setScheduleForm((current) => ({ ...current, venue: event.target.value }))} /></label>
            <label>Stage<input maxLength="60" value={scheduleForm.stage} onChange={(event) => setScheduleForm((current) => ({ ...current, stage: event.target.value }))} /></label>
            <label>Round<input maxLength="100" value={scheduleForm.round_name} onChange={(event) => setScheduleForm((current) => ({ ...current, round_name: event.target.value }))} /></label>
            <div className="field-wide form-actions"><button type="button" className="button button-secondary" onClick={() => setScheduleOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Save schedule"}</button></div>
          </form>
        </ManagementModal>
      )}
    </>
  );
}
