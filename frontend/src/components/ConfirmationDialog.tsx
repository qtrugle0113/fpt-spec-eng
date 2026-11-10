import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

export function ConfirmationDialog({ title, children, busy, onCancel, onConfirm, confirmLabel = 'Confirm changes' }: {
  title: string; children: ReactNode; busy: boolean; onCancel: () => void; onConfirm: () => void; confirmLabel?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    dialog.current?.showModal();
    return () => { dialog.current?.close(); if (previous instanceof HTMLElement) previous.focus(); };
  }, []);
  return <dialog ref={dialog} aria-label={title} onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }}>
    <h2>{title}</h2>{children}<div className="connection-actions"><button autoFocus disabled={busy} onClick={onCancel}>Cancel</button><button disabled={busy} onClick={onConfirm}>{busy ? 'Working…' : confirmLabel}</button></div>
  </dialog>;
}
