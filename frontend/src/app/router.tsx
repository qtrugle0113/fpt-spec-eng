import { createBrowserRouter } from "react-router";
import { App, WorkspacePage } from "./App";

export const sections = [
  { path: "/", label: "Dashboard", detail: "An overview of your workflows and executions." },
  { path: "/connections", label: "Connections", detail: "Manage the databases your workflows use." },
  { path: "/tables", label: "Table Management", detail: "Define and create tables from Excel workbooks." },
  { path: "/dag-builder", label: "DAG Builder", detail: "Prepare source files and define your data workflows." },
  { path: "/monitoring", label: "DAG Monitoring", detail: "Follow executions, task attempts, and logs." },
  { path: "/settings", label: "Settings", detail: "Manage defaults for your workspace." },
] as const;

export const router = createBrowserRouter([
  {
    element: <App />,
    children: [
      ...sections.map(({ path, label, detail }) => ({
        path,
        element: <WorkspacePage title={label} description={detail} />,
      })),
      { path: "*", element: <WorkspacePage title="Page not found" description="Choose a page from the navigation to continue." /> },
    ],
  },
]);
