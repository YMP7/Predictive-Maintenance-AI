import { formatPercent } from '../../design/format';
import { STATE_LABEL, type FramePart } from './types';

/** 2-D fallback when WebGL is unavailable: the same parts, states and selection as a block diagram. */
export function AssetSchematic({ parts, selected, why, onSelect, reason }: {
  parts: FramePart[];
  selected: string | null;
  why: Record<string, number> | null;
  onSelect: (id: string | null) => void;
  reason: string;
}) {
  return (
    <div className="ax-schematic" role="group" aria-label="Machine schematic, 2-D">
      <p className="ax-schematic__note">{reason} Showing the 2-D schematic instead.</p>
      <ol className="ax-schematic__grid">
        {parts.map(p => (
          <li key={p.id}>
            <button
              type="button"
              className="ax-schematic__part"
              data-state={why ? undefined : p.state}
              data-why={why && (why[p.id] ?? 0) > 0 ? 'true' : undefined}
              aria-pressed={selected === p.id}
              onClick={() => onSelect(selected === p.id ? null : p.id)}
            >
              <strong>{p.name}</strong>
              <span>{why ? `${formatPercent(why[p.id] ?? 0)} of attribution` : STATE_LABEL[p.state]}</span>
              {!why && p.load !== null && <span className="num">{formatPercent(p.load)} load</span>}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
