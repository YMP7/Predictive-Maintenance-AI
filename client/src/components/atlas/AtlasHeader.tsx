import React, { useState, useEffect } from 'react';
import { Shield, Search, Sun, Moon, LogOut, Cpu, Activity } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';

interface AtlasHeaderProps {
  activeView: string;
  onSelectView: (viewId: string) => void;
  onOpenCommandPalette: () => void;
  systemStatus: string;
  userRole?: string;
  onLogout?: () => void;
}

export const AtlasHeader: React.FC<AtlasHeaderProps> = ({
  activeView,
  onSelectView,
  onOpenCommandPalette,
  systemStatus,
  userRole = 'operator',
  onLogout
}) => {
  const { theme, toggleTheme } = useTheme();
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'monitoring', label: 'Domain Telemetry' },
    { id: 'cognition', label: 'Cognition & DNA' },
    { id: 'explainability', label: 'Explainability' },
    { id: 'decision', label: 'Decision Graph' },
    { id: 'transfer', label: 'Transfer Study' },
    { id: 'ablations', label: 'Ablation Suite' },
    { id: 'system', label: 'Diagnostics' },
    { id: 'legacy_iot', label: 'Phase A IoT Lab' },
  ];

  return (
    <header className="mission-panel" style={{ padding: '12px 20px', marginBottom: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        {/* Brand & Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-sm)',
              background: 'linear-gradient(135deg, var(--accent-cyan), #0077B6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px var(--accent-glow)'
            }}>
              <Cpu size={18} color="#05080E" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '18px', letterSpacing: '0.04em', color: 'var(--text-bright)' }}>
                  ATLAS
                </span>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', background: 'var(--accent-cyan-dim)', color: 'var(--accent-cyan)', padding: '2px 6px', borderRadius: 'var(--radius-xs)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                  Cognition OS
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: 0 }}>
                Adaptive Machine Cognition & Predictive Decision Support
              </p>
            </div>
          </div>

          <div style={{ height: '24px', width: '1px', background: 'var(--border-color)', margin: '0 4px' }} />

          {/* System Chronometer */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            <Activity size={14} color="var(--accent-cyan)" />
            <span>{utcTime}</span>
          </div>
        </div>

        {/* Global Controls & Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Search / Command Palette shortcut */}
          <button
            type="button"
            className="mission-btn"
            onClick={onOpenCommandPalette}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px' }}
            aria-label="Open Command Palette"
          >
            <Search size={13} />
            <span style={{ color: 'var(--text-secondary)' }}>Search units, views...</span>
            <kbd style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '3px', padding: '1px 5px', fontSize: '10px', color: 'var(--text-muted)' }}>
              Ctrl K
            </kbd>
          </button>

          {/* System Health */}
          <div className="status-pill status-pill-live" style={{ padding: '4px 10px' }}>
            <span className="pulse-dot" />
            <span>{systemStatus.toUpperCase()}</span>
          </div>

          {/* Role badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '4px 8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            <Shield size={12} color="var(--accent-cyan)" />
            <span style={{ color: 'var(--text-secondary)' }}>ROLE:</span>
            <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{userRole.toUpperCase()}</span>
          </div>

          {/* Theme Toggle */}
          <button
            type="button"
            className="mission-btn"
            onClick={toggleTheme}
            style={{ padding: '6px 10px' }}
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
          </button>

          {onLogout && (
            <button
              type="button"
              className="mission-btn"
              onClick={onLogout}
              style={{ padding: '6px 10px', color: 'var(--status-disc)' }}
              aria-label="Log Out"
            >
              <LogOut size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Primary Navigation Bar */}
      <nav className="nav-tab-list" aria-label="ATLAS Operational Modules">
        {navItems.map((item) => {
          const isActive = activeView === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectView(item.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              {item.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
};
export default AtlasHeader;
