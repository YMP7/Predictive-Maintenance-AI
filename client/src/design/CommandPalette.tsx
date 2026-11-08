import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { Moon, Presentation, Sun, type LucideIcon } from 'lucide-react';

import { useTheme } from '../hooks/useTheme';
import { navFor } from './nav';

interface Command {
  id: string;
  label: string;
  hint: string;
  /** Extra words that should match, e.g. the nav group. */
  keywords?: string;
  icon: LucideIcon;
  run: () => void;
}

/** Ctrl+K / Cmd+K: jump to any page the role may see, or run a view command. */
export function CommandPalette({ role, open, onClose }: { role: string; open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const ref = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState('');
  const [index, setIndex] = useState(0);

  const commands = useMemo<Command[]>(
    () => [
      ...navFor(role).map(n => ({ id: n.path, label: n.label, hint: n.summary, keywords: `${n.group} ${n.path}`, icon: n.icon, run: () => navigate(n.path) })),
      { id: 'theme', label: theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme', hint: 'Appearance', icon: theme === 'dark' ? Sun : Moon, run: toggleTheme },
      { id: 'kiosk', label: 'Start kiosk mode', hint: 'Full screen showcase tour; Esc exits', icon: Presentation, run: () => navigate('/fleet?kiosk=1') },
    ],
    [role, theme, toggleTheme, navigate],
  );

  const q = query.trim().toLowerCase();
  const results = q ? commands.filter(c => `${c.label} ${c.hint} ${c.keywords ?? ''}`.toLowerCase().includes(q)) : commands;
  const active = Math.min(index, Math.max(0, results.length - 1));

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  const reset = () => {
    setQuery('');
    setIndex(0);
  };
  const close = () => {
    reset();
    onClose();
  };
  const run = (c: Command | undefined) => {
    if (!c) return;
    close();
    c.run();
  };

  return (
    <dialog
      ref={ref}
      className="ax-dialog ax-palette"
      aria-label="Command palette"
      onCancel={e => {
        e.preventDefault();
        close();
      }}
      onClick={e => e.target === e.currentTarget && close()}
    >
      <input
        className="ax-palette__input"
        placeholder="Go to a page or run a command"
        value={query}
        autoFocus
        role="combobox"
        aria-expanded="true"
        aria-controls="ax-palette-list"
        aria-activedescendant={results[active] ? `ax-cmd-${active}` : undefined}
        onChange={e => {
          setQuery(e.target.value);
          setIndex(0);
        }}
        onKeyDown={e => {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setIndex(i => Math.min(i + 1, results.length - 1));
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setIndex(i => Math.max(i - 1, 0));
          } else if (e.key === 'Enter') {
            e.preventDefault();
            run(results[active]);
          }
        }}
      />
      {results.length ? (
        <ul id="ax-palette-list" className="ax-palette__list" role="listbox">
          {results.map((c, i) => (
            <li
              key={c.id}
              id={`ax-cmd-${i}`}
              role="option"
              aria-selected={i === active}
              className="ax-palette__item"
              onMouseEnter={() => setIndex(i)}
              onClick={() => run(c)}
            >
              <c.icon aria-hidden />
              <span>{c.label}</span>
              <small>{c.hint}</small>
            </li>
          ))}
        </ul>
      ) : (
        <p className="ax-palette__empty">Nothing matches “{query}”.</p>
      )}
    </dialog>
  );
}
