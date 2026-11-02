import { useEffect } from "react";
import { X } from "lucide-react";

export function ManagementModal({ title, onClose, children }) {
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="management-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="modal-heading">
          <h2>{title}</h2>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export function Notice({ children, tone = "success", onClose }) {
  if (!children) return null;
  return (
    <div className={`notice notice-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span>{children}</span>
      {onClose && (
        <button type="button" className="icon-button" onClick={onClose} aria-label="Dismiss message">
          <X size={16} />
        </button>
      )}
    </div>
  );
}
