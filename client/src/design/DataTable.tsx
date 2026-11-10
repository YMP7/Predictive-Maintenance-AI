import React, { useMemo, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from 'lucide-react';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
  /** Value used for sorting and text filtering. Omit to make the column unsortable. */
  sortValue?: (row: T) => string | number | null | undefined;
  align?: 'left' | 'right';
  width?: string;
}

export interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  /** Accessible name for the table. */
  caption: string;
  filterPlaceholder?: string;
  initialSort?: { key: string; dir: 'asc' | 'desc' };
  onRowActivate?: (row: T) => void;
  selectedKey?: string | null;
  rowTone?: (row: T) => 'critical' | 'high' | 'medium' | undefined;
  /** Fixed row height in px; rows render in a scroll window above `virtualizeAbove`. */
  rowHeight?: number;
  virtualizeAbove?: number;
  maxHeight?: string;
  empty?: React.ReactNode;
  toolbar?: React.ReactNode;
}

const OVERSCAN = 8;

function compare(a: string | number | null | undefined, b: string | number | null | undefined): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1; // missing values sort last
  if (b == null) return -1;
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true });
}

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  caption,
  filterPlaceholder = 'Filter',
  initialSort,
  onRowActivate,
  selectedKey,
  rowTone,
  rowHeight = 36,
  virtualizeAbove = 200,
  maxHeight = '32rem',
  empty,
  toolbar,
}: DataTableProps<T>) {
  const [sort, setSort] = useState(initialSort ?? null);
  const [query, setQuery] = useState('');
  const [scrollTop, setScrollTop] = useState(0);
  const [viewport, setViewport] = useState(512);
  const scrollRef = useRef<HTMLDivElement>(null);

  const view = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? rows.filter(r => columns.some(c => c.sortValue && String(c.sortValue(r) ?? '').toLowerCase().includes(q)))
      : rows;
    if (!sort) return filtered;
    const col = columns.find(c => c.key === sort.key);
    if (!col?.sortValue) return filtered;
    const dir = sort.dir === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => dir * compare(col.sortValue!(a), col.sortValue!(b)));
  }, [rows, columns, query, sort]);

  const virtual = view.length > virtualizeAbove;
  const first = virtual ? Math.max(0, Math.floor(scrollTop / rowHeight) - OVERSCAN) : 0;
  const count = virtual ? Math.ceil(viewport / rowHeight) + OVERSCAN * 2 : view.length;
  const visible = view.slice(first, first + count);
  const padTop = first * rowHeight;
  const padBottom = virtual ? Math.max(0, (view.length - first - visible.length) * rowHeight) : 0;

  const toggleSort = (key: string) =>
    setSort(s => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }));

  const onKeyRow = (e: React.KeyboardEvent<HTMLTableRowElement>, row: T) => {
    if (!onRowActivate) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onRowActivate(row);
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const sib = e.key === 'ArrowDown' ? e.currentTarget.nextElementSibling : e.currentTarget.previousElementSibling;
      (sib as HTMLElement | null)?.focus();
    }
  };

  return (
    <div className="ax-table-wrap">
      <div className="ax-table-tools">
        <label className="ax-header__search" style={{ minWidth: 0 }}>
          <Search aria-hidden width={14} height={14} />
          <span className="visually-hidden">{filterPlaceholder}</span>
          <input className="ax-input" type="search" placeholder={filterPlaceholder} value={query} onChange={e => setQuery(e.target.value)} />
        </label>
        {toolbar}
        <span className="ax-table-tools__count num" aria-live="polite">
          {view.length === rows.length ? `${rows.length} rows` : `${view.length} of ${rows.length} rows`}
        </span>
      </div>
      <div
        ref={scrollRef}
        className="ax-table-scroll"
        style={{ maxHeight }}
        onScroll={e => {
          setScrollTop(e.currentTarget.scrollTop);
          setViewport(e.currentTarget.clientHeight);
        }}
      >
        <table className="ax-table" style={{ ['--row-h' as string]: `${rowHeight}px` }} aria-rowcount={view.length + 1}>
          <caption className="visually-hidden">{caption}</caption>
          <thead>
            <tr>
              {columns.map(c => {
                const active = sort?.key === c.key;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    data-align={c.align}
                    style={{ width: c.width }}
                    aria-sort={active ? (sort!.dir === 'asc' ? 'ascending' : 'descending') : c.sortValue ? 'none' : undefined}
                  >
                    {c.sortValue ? (
                      <button type="button" onClick={() => toggleSort(c.key)}>
                        {c.header}
                        {active ? sort!.dir === 'asc' ? <ArrowUp aria-hidden /> : <ArrowDown aria-hidden /> : <ArrowUpDown aria-hidden />}
                      </button>
                    ) : (
                      <span>{c.header}</span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {padTop > 0 && (
              <tr className="ax-spacer" aria-hidden>
                <td colSpan={columns.length} style={{ height: padTop }} />
              </tr>
            )}
            {visible.map((row, i) => {
              const key = rowKey(row);
              return (
                <tr
                  key={key}
                  aria-rowindex={first + i + 2}
                  aria-selected={selectedKey != null ? selectedKey === key : undefined}
                  data-clickable={onRowActivate ? '' : undefined}
                  data-tone={rowTone?.(row)}
                  tabIndex={onRowActivate ? 0 : undefined}
                  onClick={onRowActivate ? () => onRowActivate(row) : undefined}
                  onKeyDown={e => onKeyRow(e, row)}
                >
                  {columns.map(c => (
                    <td key={c.key} data-align={c.align} className={c.align === 'right' ? 'num' : undefined}>
                      {c.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
            {padBottom > 0 && (
              <tr className="ax-spacer" aria-hidden>
                <td colSpan={columns.length} style={{ height: padBottom }} />
              </tr>
            )}
          </tbody>
        </table>
        {view.length === 0 && (empty ?? <p className="ax-palette__empty">{rows.length ? 'No rows match the filter.' : 'No rows yet.'}</p>)}
      </div>
    </div>
  );
}
