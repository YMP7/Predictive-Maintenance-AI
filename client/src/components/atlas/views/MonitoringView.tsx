import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../../lib/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Activity, Radio, Cpu } from 'lucide-react';
import type { DomainSnapshot } from '../DomainTicker';

interface MonitoringViewProps {
  activeDomain: string;
  activeUnit: string;
  onSelectUnit: (unitId: string) => void;
  currentSnapshot: DomainSnapshot | null;
}

interface TelemetryPoint {
  time: string;
  cycle: number;
  [key: string]: string | number;
}

interface UnitOption {
  id: string;
  label: string;
  isLive: boolean;
}

export const MonitoringView: React.FC<MonitoringViewProps> = ({
  activeDomain,
  activeUnit,
  onSelectUnit,
  currentSnapshot
}) => {
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPoint[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<string>('');
  const [availableUnits, setAvailableUnits] = useState<UnitOption[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Fetch domain units periodically
  useEffect(() => {
    let isMounted = true;
    async function loadDomainStatus() {
      try {
        setError(null);
        const res = await apiFetch<{ domain: string; machines: DomainSnapshot[]; count: number }>(
          `/api/atlas/domain/${activeDomain}/status`
        );
        if (isMounted && res.machines && res.machines.length > 0) {
          const units: UnitOption[] = res.machines.map(m => {
            const isLive = m.adapter_status === 'live' || m.adapter_status === 'connected';
            const src = m.operational_ctx?.source || m.metadata?.source;
            let displayLabel = m.machine_id;
            if (activeDomain === 'mobile') {
              if (m.machine_id === 'mobile_device_1') {
                displayLabel = `mobile_device_1 (Wi-Fi${src ? ` · ${src}` : ''})`;
              } else if (m.machine_id === 'mobile_device_2') {
                displayLabel = `mobile_device_2 (USB${src ? ` · ${src}` : ''})`;
              } else if (src) {
                displayLabel = `${m.machine_id} (${src})`;
              }
            } else if (src) {
              displayLabel = `${m.machine_id} (${src})`;
            }
            return {
              id: m.machine_id,
              label: displayLabel,
              isLive
            };
          });
          setAvailableUnits(units);
          const ids = units.map(u => u.id);
          if (!ids.includes(activeUnit)) {
            onSelectUnit(ids[0]);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load domain status');
        }
      }
    }
    loadDomainStatus();
    const interval = setInterval(loadDomainStatus, 4000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeDomain, activeUnit]);

  // Clear telemetry history when domain or unit changes so charts are never mixed across units
  useEffect(() => {
    setTelemetryHistory([]);
  }, [activeDomain, activeUnit]);

  // Synchronize selectedSensor when domain/unit changes or features change
  useEffect(() => {
    if (!currentSnapshot?.features) return;
    const featKeys = Object.keys(currentSnapshot.features);
    if (featKeys.length === 0) return;

    // If no sensor is selected, or if the selected sensor does not belong to the current domain features:
    if (!selectedSensor || !featKeys.includes(selectedSensor)) {
      setSelectedSensor(featKeys[0]);
    }
  }, [activeDomain, activeUnit, currentSnapshot?.features, selectedSensor]);

  // Buffer live readings into rolling telemetry history (max 30 points)
  useEffect(() => {
    if (!currentSnapshot || !currentSnapshot.features) return;

    const feat = currentSnapshot.features;
    const newPt: TelemetryPoint = {
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      cycle: currentSnapshot.cycle ?? Date.now(),
      ...feat
    };

    setTelemetryHistory(prev => {
      if (prev.length === 0) {
        // Seed an initial predecessor point so Recharts draws an immediate line segment
        const initialPt: TelemetryPoint = {
          time: new Date(Date.now() - 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          cycle: Math.max(0, (newPt.cycle ?? 1) - 1),
          ...feat
        };
        return [initialPt, newPt];
      }
      // Avoid duplicate consecutive cycles if cycle is unchanged
      if (prev[prev.length - 1].cycle === newPt.cycle) {
        return [...prev.slice(0, -1), newPt];
      }
      const updated = [...prev, newPt];
      return updated.slice(-30);
    });
  }, [currentSnapshot]);

  const features = currentSnapshot?.features || {};
  const featureKeys = Object.keys(features);

  const health = currentSnapshot?.health_index ?? 1.0;
  const healthPercent = Math.round(health * 100);

  let healthColor = 'var(--status-normal)';
  if (health < 0.4) healthColor = 'var(--status-critical)';
  else if (health < 0.75) healthColor = 'var(--status-warning)';

  const adapterStatus = currentSnapshot?.adapter_status?.toLowerCase() || 'simulation';
  const isLive = adapterStatus === 'connected' || adapterStatus === 'live';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Unit Selector & Live State Bar */}
      <div className="mission-panel" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={16} color="var(--accent-cyan)" />
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px', color: 'var(--text-bright)' }}>
              DOMAIN: {activeDomain.toUpperCase()}
            </span>
          </div>

          <div style={{ height: '18px', width: '1px', background: 'var(--border-color)' }} />

          {/* Unit selector dropdown and quick-switch buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>UNIT:</span>

            {/* Quick-switch buttons for domains with small unit counts (e.g. mobile) */}
            {availableUnits.length <= 4 && (
              <div style={{ display: 'flex', gap: '6px' }}>
                {availableUnits.map(u => {
                  const isUnitActive = activeUnit === u.id;
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => onSelectUnit(u.id)}
                      style={{
                        padding: '3px 8px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        borderRadius: 'var(--radius-xs)',
                        border: isUnitActive ? '1px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                        background: isUnitActive ? 'var(--accent-cyan-dim)' : 'var(--bg-secondary)',
                        color: isUnitActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        fontWeight: isUnitActive ? 700 : 500
                      }}
                    >
                      <span className={u.isLive ? "pulse-dot" : ""} style={{ width: 6, height: 6, borderRadius: '50%', background: u.isLive ? 'var(--status-normal)' : 'var(--text-muted)' }} />
                      <span>{u.id}</span>
                    </button>
                  );
                })}
              </div>
            )}

            <select
              value={activeUnit}
              onChange={e => onSelectUnit(e.target.value)}
              style={{ padding: '4px 8px', fontSize: '12px', fontFamily: 'var(--font-mono)' }}
              aria-label="Select Machine Unit"
            >
              {availableUnits.map(u => (
                <option key={u.id} value={u.id}>
                  {u.isLive ? '🟢 ' : '⚪ '}{u.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {isLive ? (
            <span className="status-pill status-pill-live">
              <span className="pulse-dot" />
              LIVE TELEMETRY STREAM
            </span>
          ) : (
            <span className="status-pill status-pill-sim">
              <Radio size={12} />
              CALIBRATED SIMULATION
            </span>
          )}

          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            CYCLE: <strong style={{ color: 'var(--text-primary)' }}>{currentSnapshot?.cycle ?? '--'}</strong>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'var(--status-disc-bg)', border: '1px solid var(--status-disc-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-disc)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          {error}
        </div>
      )}

      {/* Main 2-Column Monitoring Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 340px) 1fr', gap: '16px' }}>
        {/* Left: Health & RUL Snapshot Card */}
        <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '14px', margin: 0 }}>UNIT STATUS</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {currentSnapshot?.operational_ctx?.transport && (
                <span style={{ fontSize: '10px', textTransform: 'uppercase', padding: '2px 6px', background: 'var(--bg-elevated)', border: '1px solid var(--border-color)', borderRadius: '3px', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                  {currentSnapshot.operational_ctx.transport.toUpperCase()}
                </span>
              )}
              <span style={{ fontSize: '10px', textTransform: 'uppercase', padding: '2px 6px', background: 'var(--bg-elevated)', borderRadius: '3px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {currentSnapshot?.machine_id || activeUnit}
              </span>
            </div>
          </div>

          {/* Large Gauge / Metric Display */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-sm)',
            padding: '16px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px'
          }}>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {currentSnapshot?.rul_label || (activeDomain === 'cmapss' ? 'Health Index' : 'Instantaneous Stress Score')}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '42px', color: healthColor, lineHeight: 1 }}>
              {healthPercent}%
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              Status: <strong style={{ color: 'var(--text-bright)' }}>{currentSnapshot?.status || 'Active'}</strong>
            </div>
          </div>

          {/* RUL & Uncertainty Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '10px' }}>
              <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                PREDICTED RUL
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700, color: 'var(--text-bright)' }}>
                {typeof currentSnapshot?.rul_cycles === 'number' ? `${Math.round(currentSnapshot.rul_cycles)}c` : '--'}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {typeof currentSnapshot?.rul_days === 'number' ? `≈ ${currentSnapshot.rul_days.toFixed(1)} days` : '--'}
              </div>
            </div>

            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '10px' }}>
              <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                UNCERTAINTY
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700, color: 'var(--text-bright)' }}>
                {typeof currentSnapshot?.uncertainty === 'number' ? `±${currentSnapshot.uncertainty.toFixed(1)}` : '--'}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Confidence: {typeof currentSnapshot?.confidence === 'number' ? `${(currentSnapshot.confidence * 100).toFixed(0)}%` : '--'}
              </div>
            </div>
          </div>

          {/* Model Provenance & Adapter Info */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Telemetry Source:</span>
              <span style={{ color: isLive ? 'var(--status-normal)' : 'var(--text-secondary)' }}>
                {currentSnapshot?.operational_ctx?.source || currentSnapshot?.metadata?.source || (isLive ? 'Hardware Stream' : 'Calibrated Simulation')}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Inference Model:</span>
              <span style={{ color: currentSnapshot?.using_lstm ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
                {currentSnapshot?.using_lstm ? 'Attention-LSTM WorldModel' : 'EMA Fallback'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Updated:</span>
              <span>{currentSnapshot?.timestamp ? new Date(currentSnapshot.timestamp).toLocaleTimeString() : '--'}</span>
            </div>
          </div>
        </div>

        {/* Right: Live Telemetry Stream Chart & Feature Matrix */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Live Telemetry Chart */}
          <div className="mission-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: '14px', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>LIVE TELEMETRY STREAM</span>
                  {selectedSensor && (
                    <span style={{ fontSize: '12px', color: 'var(--accent-cyan)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                      [{selectedSensor.toUpperCase()}: {typeof features[selectedSensor] === 'number' ? features[selectedSensor].toFixed(3) : '--'}]
                    </span>
                  )}
                </h3>
              </div>

              {/* Sensor selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>SENSOR:</span>
                <select
                  value={selectedSensor}
                  onChange={e => setSelectedSensor(e.target.value)}
                  style={{ padding: '4px 8px', fontSize: '12px', fontFamily: 'var(--font-mono)' }}
                  aria-label="Select Telemetry Sensor"
                >
                  {featureKeys.map(k => {
                    let label = k;
                    if (k === 'thermal_headroom') label = `${k} [Tier c: Heuristic Estimate]`;
                    else if (k === 'vibration_rms') label = `${k} [Tier b: Triaxial Norm]`;
                    else if (k === 'magnetic_field') label = `${k} [Tier b: Flux Norm]`;
                    return (
                      <option key={k} value={k}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>

            <div style={{ width: '100%', height: '240px' }} aria-label={`Telemetry chart for ${selectedSensor}`}>
              {telemetryHistory.length === 0 ? (
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  Waiting for live telemetry readings...
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={telemetryHistory} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey="cycle" stroke="var(--text-muted)" fontSize={10} fontFamily="var(--font-mono)" tickLine={false} />
                    <YAxis
                      stroke="var(--text-muted)"
                      fontSize={10}
                      fontFamily="var(--font-mono)"
                      tickLine={false}
                      domain={[
                        (dataMin: number) => (isNaN(dataMin) ? 0 : Math.max(0, Number((dataMin - 0.05).toFixed(2)))),
                        (dataMax: number) => (isNaN(dataMax) ? 1 : Number((dataMax + 0.05).toFixed(2)))
                      ]}
                      tickFormatter={(v) => typeof v === 'number' ? v.toFixed(2) : v}
                    />
                    <Tooltip
                      contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-xs)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}
                      labelStyle={{ color: 'var(--text-muted)' }}
                      formatter={(val: any) => [typeof val === 'number' ? val.toFixed(3) : val, selectedSensor]}
                    />
                    <Line
                      type="monotone"
                      dataKey={selectedSensor}
                      stroke={
                        selectedSensor === 'thermal_headroom' ? 'var(--status-warning)' :
                        (selectedSensor === 'vibration_rms' || selectedSensor === 'magnetic_field') ? 'var(--accent-purple)' :
                        'var(--accent-cyan)'
                      }
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Full Acquired Feature Matrix (Grouped by Provenance Tier) */}
          <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* 1. Directly Sensed Hardware Channels (Tier a) */}
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '10px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>
                  {activeDomain === 'laptop' 
                    ? `ACQUIRED HARDWARE & KERNEL SENSORS (${featureKeys.filter(k => k !== 'thermal_headroom').length} CHANNELS)` 
                    : activeDomain === 'mobile'
                    ? `DIRECT HARDWARE TELEMETRY (${featureKeys.filter(k => !['vibration_rms', 'magnetic_field'].includes(k)).length} CHANNELS)`
                    : `ACQUIRED FEATURE MATRIX (${featureKeys.length} CHANNELS)`}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--status-normal)', fontFamily: 'var(--font-mono)' }}>
                  ● TIER (a) DIRECTLY MEASURED
                </span>
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
                gap: '8px'
              }}>
                {featureKeys.filter(k => k !== 'thermal_headroom' && !(activeDomain === 'mobile' && ['vibration_rms', 'magnetic_field'].includes(k))).map(k => {
                  const isSelected = selectedSensor === k;
                  const val = features[k];
                  return (
                    <div
                      key={k}
                      onClick={() => setSelectedSensor(k)}
                      style={{
                        background: isSelected ? 'var(--bg-hover)' : 'var(--bg-secondary)',
                        border: `1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border-color)'}`,
                        borderRadius: 'var(--radius-xs)',
                        padding: '8px 10px',
                        cursor: 'pointer',
                        transition: 'all 0.1s var(--ease-out)'
                      }}
                    >
                      <div style={{ fontSize: '10px', color: isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
                        {k}
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 700, color: 'var(--text-bright)' }}>
                        {typeof val === 'number' ? val.toFixed(3) : val}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 2. Physically Derived Metrics (Tier b - Mobile: vibration_rms, magnetic_field) */}
            {activeDomain === 'mobile' && (
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>PHYSICALLY DERIVED METRICS (2 CHANNELS)</span>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(168, 85, 247, 0.15)', border: '1px solid var(--accent-purple)', color: 'var(--accent-purple)', fontWeight: 700 }}>
                      TIER (b) DERIVED NORM
                    </span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    TRI-AXIAL EUCLIDEAN NORMS
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: 1.4 }}>
                  Computed deterministically from raw triaxial sensor vectors: vibration RMS from Bosch BMI320 (normalized to 20 m/s²), magnetic field from QMC6308 (normalized to 100 μT).
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
                  {['vibration_rms', 'magnetic_field'].filter(k => featureKeys.includes(k)).map(k => {
                    const isSelected = selectedSensor === k;
                    const val = features[k];
                    return (
                      <div
                        key={k}
                        onClick={() => setSelectedSensor(k)}
                        style={{
                          background: isSelected ? 'rgba(168, 85, 247, 0.12)' : 'var(--bg-secondary)',
                          border: `1px solid ${isSelected ? 'var(--accent-purple)' : 'rgba(168, 85, 247, 0.4)'}`,
                          borderRadius: 'var(--radius-xs)',
                          padding: '10px 12px',
                          cursor: 'pointer',
                          transition: 'all 0.1s var(--ease-out)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '10px', color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', fontWeight: 700 }}>
                            {k}
                          </span>
                          <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            [DERIVED]
                          </span>
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 800, color: 'var(--text-bright)', marginTop: '4px' }}>
                          {typeof val === 'number' ? val.toFixed(3) : val}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. Operational Heuristic Model Estimates (Tier c - Laptop: thermal_headroom) */}
            {featureKeys.includes('thermal_headroom') && (
              <div style={{
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: '14px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-warning)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>DERIVED & ESTIMATED METRICS (1 MODEL ESTIMATE)</span>
                    <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(255, 179, 0, 0.15)', border: '1px solid var(--status-warning)', color: 'var(--status-warning)', fontWeight: 700 }}>
                      TIER (c) HEURISTIC ESTIMATE
                    </span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    NOT A DIRECT PHYSICAL THERMISTOR READING
                  </span>
                </div>
                
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: 1.4 }}>
                  Windows user-mode permissions restrict ring-0 CPU thermistor access. This thermodynamic channel is modeled from core load, frequency boost, and memory churn (35°C–95°C range).
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
                  {['thermal_headroom'].map(k => {
                    const isSelected = selectedSensor === k;
                    const val = features[k];
                    return (
                      <div
                        key={k}
                        onClick={() => setSelectedSensor(k)}
                        style={{
                          background: isSelected ? 'rgba(255, 179, 0, 0.12)' : 'var(--bg-secondary)',
                          border: `1px dashed ${isSelected ? 'var(--status-warning)' : 'rgba(255, 179, 0, 0.4)'}`,
                          borderRadius: 'var(--radius-xs)',
                          padding: '10px 12px',
                          cursor: 'pointer',
                          transition: 'all 0.1s var(--ease-out)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '10px', color: 'var(--status-warning)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', fontWeight: 700 }}>
                            {k}
                          </span>
                          <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            [ESTIMATED]
                          </span>
                        </div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 800, color: 'var(--text-bright)', marginTop: '4px' }}>
                          {typeof val === 'number' ? val.toFixed(3) : val}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default MonitoringView;
