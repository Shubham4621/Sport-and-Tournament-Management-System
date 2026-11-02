import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Plus, Search, Trash2, UserRoundPlus, X } from "lucide-react";
import { api } from "../services/api";
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeading, Panel, StatusBadge } from "../components/ui";
import { Notice } from "../components/ManagementModal";

const EMPTY_FORM = {
  student_number: "",
  first_name: "",
  last_name: "",
  email: "",
  department_id: "",
  enrollment_status: "active",
};

function StudentForm({ departments, onCancel, onCreated }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const payload = {
        ...form,
        email: form.email.trim() || null,
        department_id: form.department_id ? Number(form.department_id) : null,
      };
      await api.createStudent(payload);
      setForm(EMPTY_FORM);
      onCreated();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  return (
    <Panel title="Add a student" action={<button className="icon-button" onClick={onCancel} aria-label="Close form"><X size={18} /></button>} className="form-panel">
      <form className="student-form" onSubmit={submit}>
        <label>Student number<input name="student_number" value={form.student_number} onChange={update} maxLength="50" required /></label>
        <label>First name<input name="first_name" value={form.first_name} onChange={update} maxLength="100" required /></label>
        <label>Last name<input name="last_name" value={form.last_name} onChange={update} maxLength="100" required /></label>
        <label>Email <span className="optional-label">Optional</span><input name="email" type="email" value={form.email} onChange={update} maxLength="254" /></label>
        <label>Department
          <select name="department_id" value={form.department_id} onChange={update}>
            <option value="">No department</option>
            {departments.map((department) => <option value={department.department_id} key={department.department_id}>{department.department_name}</option>)}
          </select>
        </label>
        <label>Enrollment status<input name="enrollment_status" value={form.enrollment_status} onChange={update} maxLength="30" required /></label>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="form-actions"><button type="button" className="button button-secondary" onClick={onCancel}>Cancel</button><button className="button button-primary" disabled={saving}>{saving ? "Saving…" : "Create student"}</button></div>
      </form>
    </Panel>
  );
}

export default function Students() {
  const [response, setResponse] = useState({ items: [], total: 0, page: 1, per_page: 25 });
  const [departments, setDepartments] = useState([]);
  const [departmentsError, setDepartmentsError] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [playerFilter, setPlayerFilter] = useState("");
  const [sportFilter, setSportFilter] = useState("");
  const [sports, setSports] = useState([]);
  const [notice, setNotice] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (page = 1, query = search, filters) => {
    setLoading(true);
    setError("");
    const activeFilters = filters ?? {
      department_id: departmentFilter,
      has_player: playerFilter,
      sport_id: sportFilter,
    };
    try {
      const data = await api.students({
        page,
        per_page: 25,
        ...(query ? { search: query } : {}),
        ...(activeFilters.department_id ? { department_id: activeFilters.department_id } : {}),
        ...(activeFilters.has_player ? { has_player: activeFilters.has_player } : {}),
        ...(activeFilters.sport_id ? { sport_id: activeFilters.sport_id } : {}),
      });
      setResponse(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [search, departmentFilter, playerFilter, sportFilter]);

  useEffect(() => {
    load(1, "");
    api.departments()
      .then((data) => setDepartments(data.items))
      .catch((requestError) => setDepartmentsError(requestError.message));
    api.sports()
      .then((data) => setSports(data.items))
      .catch((requestError) => setDepartmentsError((current) => current || requestError.message));
  }, []);

  function searchStudents(event) {
    event.preventDefault();
    const query = searchInput.trim();
    setSearch(query);
    load(1, query, {
      department_id: departmentFilter,
      has_player: playerFilter,
      sport_id: sportFilter,
    });
  }

  async function createPlayer(student) {
    try {
      await api.createPlayer(student.student_id);
      setNotice({ tone: "success", text: `Player profile created for ${student.first_name} ${student.last_name}.` });
      await load(response.page, search, {
        department_id: departmentFilter,
        has_player: playerFilter,
        sport_id: sportFilter,
      });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  async function deleteStudent(student) {
    if (!window.confirm(`Delete student ${student.first_name} ${student.last_name}? Linked records may prevent deletion.`)) return;
    try {
      await api.deleteStudent(student.student_id);
      setNotice({ tone: "success", text: `${student.student_number} deleted.` });
      await load(response.page, search, {
        department_id: departmentFilter,
        has_player: playerFilter,
        sport_id: sportFilter,
      });
    } catch (requestError) {
      setNotice({ tone: "error", text: requestError.message });
    }
  }

  const columns = [
    { key: "student_number", label: "Student no.", render: (row) => <Link className="table-primary-link" to={`/students/${row.student_id}`}>{row.student_number}</Link> },
    { key: "full_name", label: "Student", render: (row) => <div className="person-cell"><span className="avatar">{row.first_name?.charAt(0)}{row.last_name?.charAt(0)}</span><div><strong>{row.first_name} {row.last_name}</strong><span>{row.email || "No email provided"}</span></div></div> },
    { key: "department_name", label: "Department" },
    { key: "enrollment_status", label: "Status", render: (row) => <StatusBadge value={row.enrollment_status} /> },
    { key: "actions", label: "Actions", render: (row) => <div className="row-actions">
      {!row.player_id && <button className="icon-button" title="Create player profile" aria-label="Create player profile" onClick={() => createPlayer(row)}><UserRoundPlus size={16} /></button>}
      <Link className="row-action" to={`/students/${row.student_id}`}>View <ChevronRight size={15} /></Link>
      <button className="icon-button" title="Delete student" aria-label="Delete student" onClick={() => deleteStudent(row)}><Trash2 size={15} /></button>
    </div> },
  ];

  return (
    <>
      <PageHeading
        eyebrow="PEOPLE"
        title="Students"
        description="Manage student records and department details."
        action={<button className="button button-primary" onClick={() => setShowForm((value) => !value)}><Plus size={17} /> Add student</button>}
      />
      {notice && <Notice tone={notice.tone} onClose={() => setNotice(null)}>{notice.text}</Notice>}
      {showForm && <StudentForm departments={departments} onCancel={() => setShowForm(false)} onCreated={() => { setShowForm(false); load(1); }} />}
      {showForm && departmentsError && <div className="form-error department-load-error" role="alert">Department options could not be loaded: {departmentsError}</div>}
      <Panel title="Student directory" action={<span className="record-count">{response.total} records</span>}>
        <form className="table-toolbar toolbar-wrap" onSubmit={searchStudents}>
          <div className="search-field"><Search size={17} /><input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Search students…" aria-label="Search students" /></div>
          <label className="filter-control"><span>Department</span><select value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)}><option value="">All departments</option>{departments.map((department) => <option value={department.department_id} key={department.department_id}>{department.department_name}</option>)}</select></label>
          <label className="filter-control"><span>Player profile</span><select value={playerFilter} onChange={(event) => setPlayerFilter(event.target.value)}><option value="">All students</option><option value="true">Players</option><option value="false">Non-players</option></select></label>
          <label className="filter-control"><span>Sport eligibility</span><select value={sportFilter} onChange={(event) => setSportFilter(event.target.value)}><option value="">Any sport</option>{sports.map((sport) => <option value={sport.sport_id} key={sport.sport_id}>{sport.name}</option>)}</select></label>
          <button className="button button-secondary" type="submit">Search</button>
          {(search || departmentFilter || playerFilter || sportFilter) && <button className="button button-quiet" type="button" onClick={() => { setSearch(""); setSearchInput(""); setDepartmentFilter(""); setPlayerFilter(""); setSportFilter(""); load(1, "", {}); }}>Clear</button>}
        </form>
        {loading ? <LoadingState label="Loading students…" /> : error ? <ErrorState error={error} onRetry={() => load(response.page)} /> : (
          <>
            <DataTable columns={columns} rows={response.items.map((row) => ({ ...row, id: row.student_id }))} emptyTitle={search ? "No students match this search" : "No student records"} />
            <div className="pagination">
              <span>Showing {response.items.length ? (response.page - 1) * response.per_page + 1 : 0}–{Math.min(response.page * response.per_page, response.total)} of {response.total}</span>
              <div>
                <button className="icon-button" aria-label="Previous page" disabled={response.page <= 1} onClick={() => load(response.page - 1)}><ChevronLeft size={18} /></button>
                <button className="icon-button" aria-label="Next page" disabled={response.page * response.per_page >= response.total} onClick={() => load(response.page + 1)}><ChevronRight size={18} /></button>
              </div>
            </div>
          </>
        )}
      </Panel>
    </>
  );
}
