import React from 'react';
import { Plane, Laptop, Smartphone, Server, Radio, AlertCircle } from 'lucide-react';

export interface DomainSnapshot {
  domain: string;
  machine_id: string;
  timestamp: string;
  health_index: number;
  cycle: number;
  rul_label: string;
  rul_cycles: number;
  rul_days: number;
  confidence: number;
  uncertainty: number;
  status: string;
  using_lstm: boolean;
  features: Record<string, number>;
  adapter_status: string; // "connected" | "simulation" | "disconnected"
  operational_ctx?: Record<string, any>;
  metadata?: Record<string, any>;
}

interface DomainTickerProps {
  snapshots: Record<string, DomainSnapshot | null>;
  activeDomain: string;
  activeUnit?: string;
  onSelectDomainUnit?: (domain: string, unitId: string) => void;
  onSelectDomain: (domain: string) => void;
}

export const DomainTicker: React.FC<DomainTickerProps> = ({
  snapshots,
  activeDomain,
  activeUnit,
  onSelectDomainUnit,
  onSelectDomain
}) => {
  const domainsMeta = [
    {
      id: 'cmapss',
      domain: 'cmapss',
      name: 'Turbofan Fleet',
      domainLabel: 'NASA C-MAPSS (FD001)',
      icon: Plane,
      defaultMachine: 'unit_1',
      snapshotKey: 'cmapss',
    },
    {
      id: 'laptop',
      domain: 'laptop',
      name: 'Local OS Host',
      domainLabel: 'Windows psutil Telemetry',
      icon: Laptop,
      defaultMachine: 'laptop_local',
      snapshotKey: 'laptop',
    },
    {
      id: 'mobile_wifi',
      domain: 'mobile',
      name: 'Android Mobile (Wi-Fi)',
      domainLabel: 'Termux / Lumia Bridge',
      icon: Smartphone,
      defaultMachine: 'mobile_device_1',
      snapshotKey: 'mobile_device_1',
      badge: 'WIFI',
    },
    {
      id: 'mobile_usb',
      domain: 'mobile',
      name: 'Android Mobile (USB)',
      domainLabel: 'ADB Hardware Cable',
      icon: Smartphone,
      defaultMachine: 'mobile_device_2',
      snapshotKey: 'mobile_device_2',
      badge: 'USB',
    },
    {
      id: 'server',
      domain: 'server',
      name: 'Cloud Node',
      domainLabel: 'SSH Host Telemetry',
      icon: Server,
      defaultMachine: 'server_prod_1',
      snapshotKey: 'server',
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
      gap: '12px',
      marginBottom: '16px'
    }} role="region" aria-label="Live Domain Ticker">
      {domainsMeta.map((d) => {
        const snap = snapshots[d.snapshotKey] || (d.domain === 'mobile' && d.defaultMachine === activeUnit ? snapshots['mobile'] : null) || snapshots[d.domain];
        const isSelected = activeDomain === d.domain && (
          d.domain === 'mobile' ? (activeUnit === d.defaultMachine) : true
        );
        const Icon = d.icon;
        const adapterStatus = snap?.adapter_status?.toLowerCase() || 'simulation';
        const isLive = adapterStatus === 'connected' || adapterStatus === 'live';
        const isSim = adapterStatus === 'simulation';

        const health = snap?.health_index ?? 1.0;
        const healthPercent = Math.round(health * 100);

        let healthColor = 'var(--status-normal)';
        if (health < 0.4) healthColor = 'var(--status-critical)';
        else if (health < 0.75) healthColor = 'var(--status-warning)';

        const handleClick = () => {
          if (onSelectDomainUnit && d.defaultMachine) {
            onSelectDomainUnit(d.domain, d.defaultMachine);
          } else {
            onSelectDomain(d.domain);
          }
        };

        return (
          <button
            key={d.id}
            type="button"
            onClick={handleClick}
            className="mission-panel"
            style={{
              padding: '14px',
              textAlign: 'left',
              cursor: 'pointer',
              borderWidth: isSelected ? '1.5px' : '1px',
              borderColor: isSelected ? 'var(--accent-cyan)' : undefined,
              boxShadow: isSelected ? '0 0 16px var(--accent-cyan-dim)' : undefined,
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}
            aria-pressed={isSelected}
            aria-label={`${d.name} telemetry card`}
          >
            {/* Header: Icon, Title & Badge */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  padding: '6px',
                  borderRadius: 'var(--radius-sm)',
                  background: isSelected ? 'var(--accent-cyan-dim)' : 'var(--bg-elevated)',
                  color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)'
                }}>
                  <Icon size={16} />
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '13px', color: 'var(--text-bright)' }}>
                    {d.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {d.domainLabel}
                  </div>
                </div>
              </div>

              {/* Transport & Adapter Connection Status Pill */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {d.badge && (
                  <span style={{
                    fontSize: '9px',
                    padding: '2px 5px',
                    borderRadius: '3px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: 'var(--accent-cyan)',
                    border: '1px solid var(--border-color)',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700
                  }}>
                    {d.badge}
                  </span>
                )}
                {isLive ? (
                  <span className="status-pill status-pill-live" title="Live hardware telemetry connected">
                    <span className="pulse-dot" />
                    LIVE
                  </span>
                ) : isSim ? (
                  <span className="status-pill status-pill-sim" title="Simulation fallback stream active">
                    <Radio size={10} />
                    SIMULATION
                  </span>
                ) : (
                  <span className="status-pill status-pill-disc" title="Adapter disconnected">
                    <AlertCircle size={10} />
                    DISCONNECTED
                  </span>
                )}
              </div>
            </div>

            {/* Metrics Row: Score Gauge & RUL / Cycle */}
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: '4px' }}>
              <div>
                <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {snap?.rul_label || (d.id === 'cmapss' ? 'Health Index' : 'Stress Score')}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '20px', color: healthColor }}>
                    {healthPercent}%
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {snap?.status || 'Active'}
                  </span>
                </div>
              </div>

              <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                  {d.id === 'cmapss' ? 'Cycle / RUL' : 'Cycle / Load'}
                </div>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {snap && snap.cycle != null ? (
                    d.id === 'cmapss' 
                      ? `${snap.cycle} / ${typeof snap.rul_cycles === 'number' ? `${Math.round(snap.rul_cycles)}c` : '--'}`
                      : `Cycle ${snap.cycle}`
                  ) : (
                    'Waiting...'
                  )}
                </div>
              </div>
            </div>

            {/* Sub-bar / Model Tag */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '6px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: '10px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)'
            }}>
              <span>ID: {snap?.machine_id || d.defaultMachine}</span>
              <span style={{ color: snap?.using_lstm ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                {snap?.using_lstm ? 'Attention-LSTM' : 'EMA Baseline'}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
};
export default DomainTicker;
