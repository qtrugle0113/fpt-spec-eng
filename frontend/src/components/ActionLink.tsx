import type { ComponentProps } from 'react';

// Giữ anchor semantics và đích tải/navigation; icon không đổi accessible name.
export function ActionLink({ children, className = '', download, ...props }: ComponentProps<'a'>) {
  return <a {...props} download={download} className={`action-link ${className}`}>
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {download !== undefined && download !== false
        ? <path d="M10 2v10m-4-4 4 4 4-4M3 13v4h14v-4" />
        : <path d="M11 3h6v6m0-6-9 9M8 4H3v13h13v-5" />}
    </svg>{children}
  </a>;
}
