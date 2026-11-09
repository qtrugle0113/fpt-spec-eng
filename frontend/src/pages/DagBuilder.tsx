import { useState } from 'react';
import { FileSourcesPanel } from '../features/files/FileSourcesPanel';
import type { SourceFile } from '../lib/files';

export function DagBuilder() {
  const [source, setSource] = useState<SourceFile | null>(null);
  return <div className="connections-page"><header className="page-heading"><div><h1>DAG Builder</h1><p>Prepare and select validated sources for your workflows.</p></div></header>
    {source && <section className="connection-panel" aria-label="Selected ETL source"><h2>Selected ETL source</h2><p>{source.file_name} · parser revision {source.parser_revision}</p><p>Reference: <code>{source.id}</code></p><p>SHA-256: <code>{source.sha256}</code></p><button onClick={() => setSource(null)}>Clear source selection</button></section>}
    <FileSourcesPanel selected={source} onSelect={setSource} />
  </div>;
}
