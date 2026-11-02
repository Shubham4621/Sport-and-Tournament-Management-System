import { AlertCircle, LoaderCircle, SearchX } from "lucide-react";

export function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="page-heading-action">{action}</div>}
    </div>
  );
}

export function LoadingState({ label = "Loading data…" }) {
  return (
    <div className="state-card" role="status">
      <LoaderCircle className="spinner" size={22} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state-card state-error" role="alert">
      <AlertCircle size={21} />
      <div>
        <strong>Couldn’t load this information</strong>
        <p>{error}</p>
        {onRetry && (
          <button className="button button-secondary button-small" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ title, description }) {
  return (
    <div className="state-card state-empty">
      <SearchX size={23} />
      <div>
        <strong>{title}</strong>
        {description && <p>{description}</p>}
      </div>
    </div>
  );
}

export function StatusBadge({ value }) {
  const normalized = String(value || "unknown").toLowerCase().replaceAll("_", " ");
  const color =
    normalized === "completed" || normalized === "active" || normalized === "registered"
      ? "green"
      : normalized === "live" || normalized === "in progress"
        ? "blue"
        : normalized === "cancelled" || normalized === "disqualified"
          ? "red"
          : "neutral";
  return <span className={`badge badge-${color}`}>{normalized}</span>;
}

export function DataTable({ columns, rows, emptyTitle = "No records found" }) {
  if (!rows.length) {
    return <EmptyState title={emptyTitle} description="New records will appear here when available." />;
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.id ?? row.key ?? index}>
              {columns.map((column) => (
                <td key={column.key}>
                  {column.render ? column.render(row) : row[column.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Panel({ title, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && (
        <div className="panel-heading">
          {title && <h2>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function formatDate(value, options = { dateStyle: "medium" }) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString(undefined, options);
}

export function formatDateTime(value) {
  if (!value) return "Not scheduled";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function participantName(participant) {
  return participant.team_name || participant.player_name || "Participant unavailable";
}
