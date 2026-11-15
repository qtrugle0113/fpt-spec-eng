import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { NavLink, Outlet, useLocation } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { requestJSON } from "../lib/api";
import type { components } from "../lib/api.generated";
import { ActionLink } from "../components/ActionLink";

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
  const location = useLocation();
  useEffect(() => { document.getElementById('main-content')?.focus(); }, [location.pathname]);
  const backend = useQuery({ queryKey: ['backend-liveness'], retry: false, refetchInterval: 30_000,
    queryFn: async ({ signal }) => (await requestJSON<components['schemas']['Health']>('/health/live', { signal })).data });
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
            <NavLink key={path} to={path} end={path === "/"} onClick={() => setMenuOpen(false)}><svg className="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={path === '/' ? 'M2 2h6v6H2zM12 2h6v6h-6zM2 12h6v6H2zM12 12h6v6h-6z' : path === '/connections' ? 'M4 5c0-4 12-4 12 0v10c0 4-12 4-12 0V5m0 0c0 4 12 4 12 0M4 10c0 4 12 4 12 0' : path === '/tables' ? 'M2 3h16v14H2zM2 8h16M7 8v9M12 8v9' : path === '/dag-builder' ? 'M8 2h4v4H8zM2 14h4v4H2zM14 14h4v4h-4zM10 6v4M4 14v-4h12v4' : path === '/monitoring' ? 'M2 16h16M4 12V8M10 12V3M16 12V6' : 'M3 5h14M3 15h14M7 2v6M13 12v6'} /></svg>{label}</NavLink>
          ))}
          {visible.length === 0 && <p className="nav-empty" role="status">No matching pages.</p>}
        </nav>
        <div className="sidebar-footer"><span className="local-dot" aria-hidden="true" />Local workspace</div>
      </aside>
      <main id="main-content" tabIndex={-1}>
        <div className="workspace-bar">
          <span>Workspace</span>
          <div className="workspace-actions">
            <span className="service-label">{backend.isPending ? 'Checking backend…' : backend.data?.status === 'ALIVE' ? 'Backend available' : 'Backend unavailable'}</span>
            <ActionLink href={`${import.meta.env.BASE_URL}user-guide/Airflow-Automation-Tool-Huong-dan-su-dung.html`} download="Airflow-Automation-Tool-Huong-dan-su-dung.html">Download User Guide</ActionLink>
          </div>
        </div>
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
