import { useCallback, useEffect, useState } from "react";
import { Activity, CircleCheck, Info, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../services/api";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeading,
  StatusBadge,
} from "../components/ui";
import { ManagementModal, Notice } from "../components/ManagementModal";

const EMPTY_FORM = { name: "", description: "", is_active: true };

export default function Sports() {
  const [sports, setSports] = useState([]);
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
      const response = await api.sports({ include_inactive: true });
      setSports(response.items);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function openForm(sport = null) {
    setFormOpen(true);
    setEditing(sport);
    setForm(sport
      ? { name: sport.name, description: sport.description || "", is_active: Boolean(sport.is_active) }
      : EMPTY_FORM);
    setNotice(null);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setNotice(null);
    try {
      if (editing) {
        await api.updateSport(editing.sport_id, form);
        setNotice({ tone: "success", text: "Sport updated." });
      } else {
        await api.createSport(form);
        setNotice({ tone: "success", text: "Sport created." });
      }
      setFormOpen(false);
      setEditing(null);
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setSaving(false);
    }
  }

  async function remove(sport) {
    if (!window.confirm(`Delete “${sport.name}”? This is only allowed if no records depend on it.`)) return;
    setNotice(null);
    try {
      await api.deleteSport(sport.sport_id);
      setNotice({ tone: "success", text: `${sport.name} deleted.` });
      await load();
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="CATALOG"
        title="Sports"
        description="Manage sports and their availability in the competition catalog."
        action={<button className="button button-primary" onClick={() => openForm()}><Plus size={17} /> Add sport</button>}
      />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      {loading ? <LoadingState label="Loading sports…" /> : error ? <ErrorState error={error} onRetry={load} /> : sports.length ? (
        <div className="sport-grid">
          {sports.map((sport, index) => (
            <article className="sport-card" key={sport.sport_id}>
              <div className={`sport-card-symbol sport-symbol-${index % 5}`}><Activity size={21} /></div>
              <div className="sport-card-top"><span className="sport-id">SPORT {String(sport.sport_id).padStart(3, "0")}</span><StatusBadge value={sport.is_active ? "active" : "inactive"} /></div>
              <h2>{sport.name}</h2>
              <p>{sport.description || "No description has been added for this sport."}</p>
              <div className="sport-card-footer"><CircleCheck size={15} /><span>{sport.is_active ? "Available for competition" : "Unavailable for new competition"}</span></div>
              <div className="row-actions">
                <button className="button button-secondary button-small" onClick={() => openForm(sport)}><Pencil size={14} /> Edit</button>
                <button className="button button-danger button-small" onClick={() => remove(sport)}><Trash2 size={14} /> Delete</button>
              </div>
            </article>
          ))}
        </div>
      ) : <EmptyState title="No sports" description="Add a sport to populate the catalog." />}
      <div className="information-banner">
        <Info size={18} />
        <p>Sports referenced by teams, players, or tournaments cannot be deleted. Deactivate them instead to preserve historical records.</p>
      </div>
      {formOpen && (
        <ManagementModal title={editing ? "Edit sport" : "Add sport"} onClose={() => setFormOpen(false)}>
          <form className="management-form" onSubmit={submit}>
            <label>Sport name<input autoFocus name="name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} maxLength="100" required /></label>
            <label>Description<textarea name="description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
            <label className="checkbox-field"><input type="checkbox" checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} /> Active for new competitions</label>
            {notice?.tone === "error" && <div className="form-error" role="alert">{notice.text}</div>}
            <div className="form-actions"><button type="button" className="button button-secondary" onClick={() => setFormOpen(false)}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create sport"}</button></div>
          </form>
        </ManagementModal>
      )}
    </>
  );
}
