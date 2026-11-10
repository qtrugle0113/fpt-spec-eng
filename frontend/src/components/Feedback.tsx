import type { ReactNode } from 'react';

export function Feedback({ kind, children }: { kind: 'error' | 'status'; children: ReactNode }) {
  return <p className={kind === 'error' ? 'connection-error' : 'connection-notice'} role={kind === 'error' ? 'alert' : 'status'}>{children}</p>;
}
