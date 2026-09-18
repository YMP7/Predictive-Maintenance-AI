import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Activity, Cpu, Layers, GitCompare, FileText, Settings, Radio } from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectView: (viewId: string) => void;
  onSelectDomainUnit: (domain: string, unitId: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSelectView,
  onSelectDomainUnit
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onSelectView(window.location.pathname.replace('/', '') || 'monitoring');
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, onSelectView]);

  if (!isOpen) return null;

  const items = [
    // Views
    { type: 'view', id: 'monitoring', title: 'Domain Telemetry & Monitoring', desc: 'Live sensor readings across 4 domains', icon: Activity },
    { type: 'view', id: 'cognition', title: 'Cognition, Uncertainty & DNA', desc: 'Monte Carlo RUL spread, 16-dim DNA fingerprint', icon: Cpu },
    { type: 'view', id: 'explainability', title: 'Explainability & Attribution', desc: 'Sensor attribution deltas & AMKB citations', icon: Layers },
    { type: 'view', id: 'decision', title: 'Decision Graph & Simulation', desc: 'Ranked candidate actions & safety override triggers', icon: GitCompare },
    { type: 'view', id: 'transfer', title: 'Cross-Domain Transfer Study', desc: 'MMD divergence matrix & Negative Transfer Index', icon: FileText },
    { type: 'view', id: 'ablations', title: 'Ablation Suite Results', desc: 'Cost savings (47.17%) and confidence calibration', icon: FileText },
    { type: 'view', id: 'system', title: 'System Diagnostics & Benchmarks', desc: 'Latency percentiles, memory RSS & pool status', icon: Settings },
    { type: 'view', id: 'legacy_iot', title: 'Phase A IoT Lab (Legacy)', desc: 'Motor digital twin with fault injection & agent chat', icon: Activity },

    // Domains & Units
    { type: 'unit', domain: 'cmapss', id: 'unit_1', title: 'C-MAPSS: Unit 1', desc: 'NASA Turbofan FD001 (High degradation)', icon: Radio },
    { type: 'unit', domain: 'cmapss', id: 'unit_2', title: 'C-MAPSS: Unit 2', desc: 'NASA Turbofan FD001 (Mid cycle)', icon: Radio },
    { type: 'unit', domain: 'cmapss', id: 'unit_3', title: 'C-MAPSS: Unit 3', desc: 'NASA Turbofan FD001 (Healthy fleet unit)', icon: Radio },
    { type: 'unit', domain: 'laptop', id: 'laptop_host', title: 'Laptop: Host OS', desc: 'Local machine psutil live telemetry', icon: Radio },
    { type: 'unit', domain: 'mobile', id: 'mobile_device_1', title: 'Mobile: Device 1 (Wi-Fi)', desc: 'Termux / Lumia live Wi-Fi telemetry', icon: Radio },
    { type: 'unit', domain: 'mobile', id: 'mobile_device_2', title: 'Mobile: Device 2 (USB)', desc: 'ADB cable hardware telemetry stream', icon: Radio },
    { type: 'unit', domain: 'server', id: 'server_node_1', title: 'Server: Cloud Node 1', desc: 'Multi-core & GPU workload telemetry', icon: Radio },
  ];

  const filtered = items.filter(i => 
    i.title.toLowerCase().includes(query.toLowerCase()) || 
    i.desc.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(5, 8, 14, 0.75)',
      backdropFilter: 'blur(8px)',
      WebkitBackdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'center',
      paddingTop: '15vh',
      zIndex: 1000
    }} onClick={onClose} role="dialog" aria-modal="true" aria-label="Command Palette">
      <div
        className="mission-panel"
        style={{
          width: '100%',
          maxWidth: '560px',
          background: 'var(--bg-elevated)',
          overflow: 'hidden',
          boxShadow: '0 16px 40px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 229, 255, 0.15)',
          border: '1px solid var(--border-hover)'
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Input Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '14px 16px',
          borderBottom: '1px solid var(--border-color)'
        }}>
          <Search size={16} color="var(--accent-cyan)" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Type a command, view, or machine ID..."
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              color: 'var(--text-bright)',
              fontFamily: 'var(--font-mono)',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            aria-label="Close Command Palette"
          >
            <X size={16} />
          </button>
        </div>

        {/* Results List */}
        <div style={{ maxHeight: '340px', overflowY: 'auto', padding: '6px' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
              No commands or units matching "{query}"
            </div>
          ) : (
            filtered.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={`${item.type}-${item.id}-${idx}`}
                  onClick={() => {
                    if (item.type === 'view') {
                      onSelectView(item.id);
                    } else if (item.type === 'unit' && item.domain) {
                      onSelectDomainUnit(item.domain, item.id);
                    }
                    onClose();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    transition: 'background 0.1s var(--ease-out)',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.02)'
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{
                    padding: '6px',
                    borderRadius: 'var(--radius-xs)',
                    background: 'var(--bg-secondary)',
                    color: 'var(--accent-cyan)'
                  }}>
                    <Icon size={14} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {item.desc}
                    </div>
                  </div>
                  <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: '3px' }}>
                    {item.type}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '8px 16px',
          background: 'var(--bg-secondary)',
          borderTop: '1px solid var(--border-color)',
          fontSize: '11px',
          color: 'var(--text-muted)',
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: 'var(--font-mono)'
        }}>
          <span>Navigate with mouse or Tab</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
};
export default CommandPalette;
