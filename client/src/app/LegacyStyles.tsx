import type { ReactNode } from 'react';

// The pre-redesign stylesheet, loaded only with the legacy pages that still need it.
// shortcut: once loaded it stays in the document until reload; removed in P7 with the legacy pages.
import '../index.css';

export default function LegacyStyles({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
