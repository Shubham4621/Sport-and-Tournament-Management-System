import { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2, UsersRound, UserPlus, UserMinus } from "lucide-react";
import { api } from "../services/api";
import {
  DataTable,
  ErrorState,
  LoadingState,
  PageHeading,
  Panel,
  StatusBadge,
} from "../components/ui";
import { ManagementModal, Notice } from "../components/ManagementModal";

const EMPTY_FORM = { sport_id: "", department_id: "", name: "", team_code: "", is_active: true };

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [sports, setSports] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [players, setPlayers] = useState([]);
  const [roster, setRoster] = useState(null);
  const [membershipPlayer, setMembershipPlayer] = useState("");
  const [membershipFrom, setMembershipFrom] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [teamData, sportData, departmentData, playerData] = await Promise.all([
        api.teams({ include_inactive: true }),
        api.sports(),
        api.departments(),
        api.players({ is_active: true, per_page: 100 }),
      ]);
      setTeams(teamData.items);
      setSports(sportData.items);
      setDepartments(departmentData.items);
      setPlayers(playerData.items);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function openForm(team = null) {
    setEditing(team);
    setForm(team
      ? { sport_id: String(team.sport_id), department_id: String(team.department_id), name: team.name, team_code: team.team_code || "", is_active: Boolean(team.is_active) }
      : EMPTY_FORM);
    setFormOpen(true);
    setNotice(null);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    const payload = {
      ...form,
      sport_id: Number(form.sport_id),
      department_id: Number(form.department_id),
      team_code: form.team_code.trim() || null,
    };
    try {
      if (editing) {
        await api.updateTeam(editing.team_id, payload);
        setNotice({ tone: "success", text: "Team updated." });
      } else {
        await api.createTeam(payload);
        setNotice({ tone: "success", text: "Team created." });
      }
      setFormOpen(false);
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setSaving(false);
    }
  }

  async function remove(team) {
    if (!window.confirm(`Delete “${team.name}”? Teams with history cannot be deleted.`)) return;
    try {
      await api.deleteTeam(team.team_id);
      setNotice({ tone: "success", text: `${team.name} deleted.` });
      if (roster?.team.team_id === team.team_id) setRoster(null);
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function showRoster(team) {
    setNotice(null);
    try {
      const response = await api.team(team.team_id, { include_inactive: true });
      setRoster(response);
      setMembershipPlayer("");
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function addMember(event) {
    event.preventDefault();
    if (!roster || !membershipPlayer) return;
    try {
      await api.addTeamMember(roster.team.team_id, {
        player_id: Number(membershipPlayer),
        membership_from: membershipFrom,
      });
      await showRoster(roster.team);
      setNotice({ tone: "success", text: "Player added to the team roster." });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function removeMember(member) {
    if (!window.confirm(`End ${member.first_name} ${member.last_name}'s active membership?`)) return;
    try {
      await api.removeTeamMember(roster.team.team_id, member.player_id);
      await showRoster(roster.team);
      setNotice({ tone: "success", text: "Team membership ended; history was retained." });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  const columns = [
    { key: "team", label: "Team", render: (row) => <div className="person-cell"><span className="avatar avatar-green">{row.name?.slice(0, 2).toUpperCase()}</span><div><strong>{row.name}</strong><span>{row.team_code || `Team #${row.team_id}`}</span></div></div> },
    { key: "sport_name", label: "Sport", render: (row) => <span className="sport-cell"><span className="sport-dot" />{row.sport_name}</span> },
    { key: "department_name", label: "Department" },
    { key: "status", label: "Status", render: (row) => <StatusBadge value={row.is_active ? "active" : "inactive"} /> },
    { key: "actions", label: "Actions", render: (row) => <div className="row-actions">
      <button className="button button-secondary button-small" onClick={() => showRoster(row)}><UsersRound size={14} /> Roster</button>
      <button className="icon-button" title="Edit team" aria-label="Edit team" onClick={() => openForm(row)}><Pencil size={15} /></button>
      <button className="icon-button" title="Delete team" aria-label="Delete team" onClick={() => remove(row)}><Trash2 size={15} /></button>
    </div> },
  ];

  return (
    <>
      <PageHeading eyebrow="COMPETITION" title="Teams" description="Create teams and maintain eligible player rosters." action={<button className="button button-primary" onClick={() => openForm()}><Plus size={16} /> Create team</button>} />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      <Panel title="Team directory" action={<span className="record-count">{teams.length} teams</span>}>
        {loading ? <LoadingState label="Loading teams…" /> : error ? <ErrorState error={error} onRetry={load} /> : (
          <DataTable emptyTitle="No teams" rows={teams.map((team) => ({ ...team, id: team.team_id }))} columns={columns} />
        )}
      </Panel>
      {roster && (
        <Panel title={`${roster.team.name} roster`} className="section-spacer">
          <form className="inline-form" onSubmit={addMember}>
            <label>Eligible player
              <select value={membershipPlayer} onChange={(event) => setMembershipPlayer(event.target.value)} required>
                <option value="">Select player</option>
                {players.filter((player) => player.eligible_sport_count > 0).map((player) => <option value={player.player_id} key={player.player_id}>{player.first_name} {player.last_name} · {player.student_number}</option>)}
              </select>
            </label>
            <label>Membership starts<input type="date" value={membershipFrom} onChange={(event) => setMembershipFrom(event.target.value)} required /></label>
            <button className="button button-primary" disabled={!players.length}><UserPlus size={15} /> Add player</button>
            <button type="button" className="button button-secondary" onClick={() => setRoster(null)}>Close roster</button>
          </form>
          <DataTable
            emptyTitle="No roster history"
            rows={roster.members.map((member, index) => ({ ...member, id: `${member.player_id}-${member.membership_from}-${index}` }))}
            columns={[
              { key: "player", label: "Player", render: (row) => <div className="person-cell"><span className="avatar">{row.first_name?.[0]}{row.last_name?.[0]}</span><div><strong>{row.first_name} {row.last_name}</strong><span>{row.student_number}</span></div></div> },
              { key: "membership_from", label: "From" },
              { key: "membership_to", label: "To", render: (row) => row.membership_to || "Current" },
              { key: "action", label: "", render: (row) => (!row.membership_to || row.membership_to >= new Date().toISOString().slice(0, 10)) && <button className="button button-danger button-small" onClick={() => removeMember(row)}><UserMinus size={14} /> End membership</button> },
            ]}
          />
        </Panel>
      )}
      {formOpen && (
        <ManagementModal title={editing ? "Edit team" : "Create team"} onClose={() => setFormOpen(false)}>
          <form className="management-form-grid" onSubmit={submit}>
            <label>Team name<input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} maxLength="150" required /></label>
            <label>Team code <span className="optional-label">Optional</span><input value={form.team_code} onChange={(event) => setForm((current) => ({ ...current, team_code: event.target.value }))} maxLength="50" /></label>
            <label>Sport<select value={form.sport_id} onChange={(event) => setForm((current) => ({ ...current, sport_id: event.target.value }))} required><option value="">Select sport</option>{sports.map((sport) => <option value={sport.sport_id} key={sport.sport_id}>{sport.name}</option>)}</select></label>
            <label>Department<select value={form.department_id} onChange={(event) => setForm((current) => ({ ...current, department_id: event.target.value }))} required><option value="">Select department</option>{departments.map((department) => <option value={department.department_id} key={department.department_id}>{department.department_name}</option>)}</select></label>
            <label className="field-wide checkbox-field"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} /> Active team</label>
            {notice?.tone === "error" && <div className="field-wide form-error" role="alert">{notice.text}</div>}
            <div className="field-wide form-actions"><button type="button" className="button button-secondary" onClick={() => setFormOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : editing ? "Save team" : "Create team"}</button></div>
          </form>
        </ManagementModal>
      )}
    </>
  );
}
