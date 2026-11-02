import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save, Trash2, UserRoundPlus, X } from "lucide-react";
import { api } from "../services/api";
import { DataTable, ErrorState, LoadingState, PageHeading, Panel, StatusBadge } from "../components/ui";
import { Notice } from "../components/ManagementModal";

const FIELDS = [
  ["student_number", "Student number", 50],
  ["first_name", "First name", 100],
  ["last_name", "Last name", 100],
  ["email", "Email", 254],
  ["enrollment_status", "Enrollment status", 30],
];

export default function StudentDetails() {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [sports, setSports] = useState([]);
  const [notice, setNotice] = useState(null);
  const [eligibilityForm, setEligibilityForm] = useState({ sport_id: "", eligible_from: new Date().toISOString().slice(0, 10), eligible_to: "" });
  const [eligibilitySaving, setEligibilitySaving] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [studentData, departmentData, sportsData] = await Promise.all([
        api.student(studentId),
        api.departments(),
        api.sports(),
      ]);
      setStudent(studentData.student);
      setDepartments(departmentData.items);
      setSports(sportsData.items);
      setForm({
        student_number: studentData.student.student_number || "",
        first_name: studentData.student.first_name || "",
        last_name: studentData.student.last_name || "",
        email: studentData.student.email || "",
        department_id: studentData.student.department_id || "",
        enrollment_status: studentData.student.enrollment_status || "",
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [studentId]);

  function update(event) {
    setSaved(false);
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const payload = {
        ...form,
        email: form.email.trim() || null,
        department_id: form.department_id ? Number(form.department_id) : null,
      };
      const result = await api.updateStudent(studentId, payload);
      setStudent(result.student);
      setSaved(true);
      setNotice({ tone: "success", text: "Student changes saved." });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function createPlayer() {
    try {
      await api.createPlayer(student.student_id);
      await load();
      setNotice({ tone: "success", text: "Player profile created." });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function addEligibility(event) {
    event.preventDefault();
    setEligibilitySaving(true);
    setNotice(null);
    try {
      await api.addPlayerEligibility(student.player.player_id, {
        sport_id: Number(eligibilityForm.sport_id),
        eligible_from: eligibilityForm.eligible_from,
        eligible_to: eligibilityForm.eligible_to || null,
      });
      await load();
      setNotice({ tone: "success", text: "Sport eligibility added." });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    } finally {
      setEligibilitySaving(false);
    }
  }

  async function endEligibility(row) {
    if (!window.confirm(`End ${row.sport_name} eligibility today?`)) return;
    try {
      await api.endPlayerEligibility(student.player.player_id, row.sport_id);
      await load();
      setNotice({ tone: "success", text: `${row.sport_name} eligibility ended.` });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function deleteStudent() {
    if (!window.confirm(`Delete ${student.first_name} ${student.last_name}? Existing related records may prevent deletion.`)) return;
    try {
      await api.deleteStudent(student.student_id);
      navigate("/students");
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="STUDENT RECORD"
        title={loading ? "Student details" : student ? `${student.first_name} ${student.last_name}` : "Student not found"}
        description={student ? `Student number ${student.student_number}` : "View and update the student record."}
        action={<div className="toolbar-wrap"><button className="button button-danger" onClick={deleteStudent}><Trash2 size={15} /> Delete student</button><Link className="button button-secondary" to="/students"><ArrowLeft size={16} /> Back to students</Link></div>}
      />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      {loading ? <LoadingState label="Loading student details…" /> : error && !student ? <ErrorState error={error} onRetry={load} /> : student && form ? (
        <div className="detail-layout">
          <Panel title="Student information">
            <form className="detail-form" onSubmit={save}>
              {FIELDS.map(([name, label, maxLength]) => (
                <label key={name}>{label}
                  <input name={name} value={form[name]} onChange={update} maxLength={maxLength} type={name === "email" ? "email" : "text"} required={name !== "email"} />
                </label>
              ))}
              <label>Department
                <select name="department_id" value={form.department_id} onChange={update}>
                  <option value="">No department</option>
                  {departments.map((department) => <option key={department.department_id} value={department.department_id}>{department.department_name}</option>)}
                </select>
              </label>
              {error && <div className="form-error" role="alert">{error}</div>}
              <div className="form-actions">
                {saved && <span className="save-confirmation">Changes saved</span>}
                <button className="button button-primary" disabled={saving}><Save size={16} /> {saving ? "Saving…" : "Save changes"}</button>
              </div>
            </form>
          </Panel>
          <Panel title="Record details" className="summary-panel">
            <div className="detail-summary">
              <div><span>Student ID</span><strong>#{student.student_id}</strong></div>
              <div><span>Current status</span><StatusBadge value={student.enrollment_status} /></div>
              <div><span>Department</span><strong>{student.department_name || "Not assigned"}</strong></div>
              <div><span>Email address</span><strong>{student.email || "Not provided"}</strong></div>
              <div><span>Created</span><strong>{student.created_at ? new Date(student.created_at).toLocaleDateString() : "—"}</strong></div>
            </div>
          </Panel>
          <Panel title="Player profile" className="section-spacer">
            {student.player ? (
              <>
                <div className="detail-summary">
                  <div><span>Player ID</span><strong>#{student.player.player_id}</strong></div>
                  <div><span>Player status</span><StatusBadge value={student.player.is_active ? "active" : "inactive"} /></div>
                </div>
                <h3 className="subsection-title">Sport eligibility</h3>
                <DataTable
                  emptyTitle="No sport eligibility"
                  rows={(student.eligibility || []).map((row) => ({ ...row, id: row.sport_id }))}
                  columns={[
                    { key: "sport_name", label: "Sport" },
                    { key: "eligible_from", label: "Eligible from" },
                    { key: "eligible_to", label: "Eligible to", render: (row) => row.eligible_to || "Ongoing" },
                    { key: "action", label: "", render: (row) => <button className="button button-danger button-small" onClick={() => endEligibility(row)} disabled={row.eligible_to && row.eligible_to < new Date().toISOString().slice(0, 10)}><X size={14} /> End</button> },
                  ]}
                />
                <form className="inline-form" onSubmit={addEligibility}>
                  <label>Sport<select value={eligibilityForm.sport_id} onChange={(event) => setEligibilityForm((current) => ({ ...current, sport_id: event.target.value }))} required><option value="">Select sport</option>{sports.filter((sport) => !(student.eligibility || []).some((record) => record.sport_id === sport.sport_id)).map((sport) => <option value={sport.sport_id} key={sport.sport_id}>{sport.name}</option>)}</select></label>
                  <label>Eligible from<input type="date" value={eligibilityForm.eligible_from} onChange={(event) => setEligibilityForm((current) => ({ ...current, eligible_from: event.target.value }))} required /></label>
                  <label>Eligible to <span className="optional-label">Optional</span><input type="date" value={eligibilityForm.eligible_to} onChange={(event) => setEligibilityForm((current) => ({ ...current, eligible_to: event.target.value }))} /></label>
                  <button className="button button-primary" disabled={eligibilitySaving || !sports.length}>{eligibilitySaving ? "Adding…" : "Add eligibility"}</button>
                </form>
              </>
            ) : (
              <div className="inline-form">
                <p className="compact-help">Create a player profile to manage sport eligibility and team rosters.</p>
                <button className="button button-primary" onClick={createPlayer}><UserRoundPlus size={16} /> Create player profile</button>
              </div>
            )}
          </Panel>
        </div>
      ) : <Panel><div className="compact-empty">Student record not found.</div><button className="button button-secondary" onClick={() => navigate("/students")}>Return to students</button></Panel>}
    </>
  );
}
