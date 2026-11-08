import { useState } from "react";
import { useForm } from "react-hook-form";
import { NavLink, Outlet } from "react-router";

// Danh sách navigation không là dữ liệu nghiệp vụ hoặc mock API.
const navigation = [
  ["/", "Dashboard"],
  ["/connections", "Connections"],
  ["/tables", "Table Management"],
  ["/dag-builder", "DAG Builder"],
  ["/monitoring", "DAG Monitoring"],
  ["/settings", "Settings"],
] as const;

export function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { register, watch } = useForm<{ search: string }>({ defaultValues: { search: "" } });
  const search = watch("search").trim().toLowerCase();
  const visible = navigation.filter(([, label]) => label.toLowerCase().includes(search));

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="mobile-header">
        <span>Airflow Automation Tool</span>
        <button type="button" aria-controls="workspace-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? "Close menu" : "Open menu"}
        </button>
      </header>
      <aside className={`sidebar ${menuOpen ? "is-open" : ""}`}>
        <div className="brand"><span className="brand-mark" aria-hidden="true">A</span><span>Airflow<br />Automation Tool</span></div>
        <p className="nav-caption">WORKSPACE</p>
        <form className="navigation-search" onSubmit={(event) => event.preventDefault()} role="search">
          <label htmlFor="navigation-search">Find a page</label>
          <input id="navigation-search" type="search" placeholder="Search pages" {...register("search")} />
        </form>
        <nav id="workspace-navigation" aria-label="Main navigation">
          {visible.map(([path, label]) => (
            <NavLink key={path} to={path} end={path === "/"} onClick={() => setMenuOpen(false)}>{label}</NavLink>
          ))}
          {visible.length === 0 && <p className="nav-empty" role="status">No matching pages.</p>}
        </nav>
        <div className="sidebar-footer"><span className="local-dot" aria-hidden="true" />Local workspace</div>
      </aside>
      <main id="main-content" tabIndex={-1}>
        <div className="workspace-bar"><span>Workspace</span><span className="service-label">Service not connected</span></div>
        <Outlet />
      </main>
    </div>
  );
}

export function WorkspacePage({ title, description }: { title: string; description: string }) {
  return (
    <section className="workspace-page" aria-labelledby="page-title">
      <p className="eyebrow">YOUR DATA WORKSPACE</p>
      <h1 id="page-title">{title}</h1>
      <p className="page-description">{description}</p>
      <div className="unavailable-panel" role="status">
        <div className="panel-icon" aria-hidden="true">↗</div>
        <h2>Workspace unavailable</h2>
        <p>The service is not connected. Workspace data and actions are unavailable.</p>
      </div>
    </section>
  );
}
