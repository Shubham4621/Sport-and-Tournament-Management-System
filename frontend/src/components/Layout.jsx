import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  CalendarDays,
  ChevronRight,
  CircleHelp,
  LayoutDashboard,
  Menu,
  Medal,
  ShieldCheck,
  Trophy,
  Users,
  UsersRound,
  X,
} from "lucide-react";

const navigation = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard, end: true },
  { label: "Sports", path: "/sports", icon: Activity },
  { label: "Students", path: "/students", icon: Users },
  { label: "Teams", path: "/teams", icon: UsersRound },
  { label: "Tournaments", path: "/tournaments", icon: Trophy },
  { label: "Matches", path: "/matches", icon: CalendarDays },
  { label: "Standings", path: "/standings", icon: Medal },
];

const pageTitles = {
  "/": "Dashboard",
  "/sports": "Sports",
  "/students": "Students",
  "/teams": "Teams",
  "/tournaments": "Tournaments",
  "/matches": "Matches",
  "/standings": "Standings",
};

function Sidebar({ onNavigate, mobileOpen }) {
  return (
    <>
      {mobileOpen && <button className="sidebar-backdrop" onClick={onNavigate} aria-label="Close navigation" />}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Trophy size={21} strokeWidth={2.2} /></div>
          <div>
            <strong>SportsDesk</strong>
            <span>TOURNAMENT MANAGER</span>
          </div>
          <button className="icon-button sidebar-close" onClick={onNavigate} aria-label="Close navigation">
            <X size={19} />
          </button>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ label, path, icon: Icon, end }) => (
            <NavLink
              key={path}
              to={path}
              end={end}
              onClick={onNavigate}
              className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
            >
              <Icon size={18} />
              <span>{label}</span>
              {path === "/" && <ChevronRight className="nav-chevron" size={15} />}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-note">
          <div className="sidebar-note-icon"><ShieldCheck size={17} /></div>
          <div><strong>Open access</strong><span>Project workspace</span></div>
        </div>
        <div className="sidebar-footer">
          <CircleHelp size={15} />
          <span>Sports &amp; Tournament System</span>
        </div>
      </aside>
    </>
  );
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const title = location.pathname.startsWith("/students/")
    ? "Student details"
    : location.pathname.startsWith("/tournaments/")
      ? "Tournament details"
      : location.pathname.startsWith("/matches/")
        ? "Match details"
        : pageTitles[location.pathname] || "SportsDesk";

  return (
    <div className="app-shell">
      <Sidebar mobileOpen={mobileOpen} onNavigate={() => setMobileOpen(false)} />
      <div className="main-column">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu size={21} />
          </button>
          <div className="topbar-context">
            <span>SPORTS MANAGEMENT</span>
            <ChevronRight size={14} />
            <strong>{title}</strong>
          </div>
          <div className="topbar-status"><span className="online-dot" /> API workspace</div>
        </header>
        <main className="page-content"><Outlet /></main>
        <footer className="app-footer">
          <span>SportsDesk</span><span>Sports &amp; Tournament Management System</span>
        </footer>
      </div>
    </div>
  );
}
