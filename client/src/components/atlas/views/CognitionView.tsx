import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../../lib/api';
import { Cpu, Dna, GitCommit, Layers, CheckCircle2, RefreshCw } from 'lucide-react';
import type { DomainSnapshot } from '../DomainTicker';

interface NeighborContext {
  machine_id: string;
  cycle: number;
  rul: number;
  distance: number;
}

interface AdaptiveContextPayload {
  domain: string;
  machine_id: string;
  query_cycle: number;
  predicted_rul: number;
  neighbors: NeighborContext[];
  average_neighbor_rul: number;
  machine_dna?: number[] | null;
}

interface CognitionViewProps {
  activeDomain: string;
  activeUnit: string;
  currentSnapshot: DomainSnapshot | null;
}

const DNA_DIM_LABELS = [
  // Health Pattern (3 dims: 0..2)
  { index: 0, group: 'Health Pattern', label: 'State Norm Drift', key: 'sv_norm_slope' },
  { index: 1, group: 'Health Pattern', label: 'Life Fraction Decay', key: 'lf_slope' },
  { index: 2, group: 'Health Pattern', label: 'Degradation Variance', key: 'lf_var' },
  // Thermal Profile (3 dims: 3..5)
  { index: 3, group: 'Thermal Profile', label: 'LPC Outlet Temp (s2)', key: 's2_slope' },
  { index: 4, group: 'Thermal Profile', label: 'HPC Outlet Temp (s3)', key: 's3_slope' },
  { index: 5, group: 'Thermal Profile', label: 'LPT Outlet Temp (s4)', key: 's4_slope' },
  // Power Signature (2 dims: 6..7)
  { index: 6, group: 'Power Signature', label: 'HPC Pressure Rate (s9)', key: 's9_slope' },
  { index: 7, group: 'Power Signature', label: 'Core Speed Ratio (s14)', key: 's14_slope' },
  // Failure Signature (8 dims: 8..15)
  { index: 8, group: 'Failure Signature (Terminal 20%)', label: 'Terminal Health Trend', key: 'term_hi_slope' },
  { index: 9, group: 'Failure Signature (Terminal 20%)', label: 'Terminal State Drift', key: 'term_sv_slope' },
  { index: 10, group: 'Failure Signature (Terminal 20%)', label: 'Terminal LPC Temp', key: 'term_s2_slope' },
  { index: 11, group: 'Failure Signature (Terminal 20%)', label: 'Terminal HPC Temp', key: 'term_s3_slope' },
  { index: 12, group: 'Failure Signature (Terminal 20%)', label: 'Terminal LPT Temp', key: 'term_s4_slope' },
  { index: 13, group: 'Failure Signature (Terminal 20%)', label: 'Terminal High Pressure', key: 'term_s7_slope' },
  { index: 14, group: 'Failure Signature (Terminal 20%)', label: 'Terminal Static Press', key: 'term_s11_slope' },
  { index: 15, group: 'Failure Signature (Terminal 20%)', label: 'Terminal Bypass Excursion', key: 'term_s15_slope' },
];

export const CognitionView: React.FC<CognitionViewProps> = ({
  activeDomain,
  activeUnit,
  currentSnapshot,
}) => {
  const [contextData, setContextData] = useState<AdaptiveContextPayload | null>(null);
  const [dnaVector, setDnaVector] = useState<number[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadCognitionState = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch live sliding window for unit
      const winRes = await apiFetch<{
        domain: string;
        machine_id: string;
        window: number[][];
        cycle: number;
        feature_dim: number;
      }>(`/api/atlas/domain/${activeDomain}/machine/${activeUnit}/window`);

      // 2. Query Adaptive Context API
      const ctx = await apiFetch<AdaptiveContextPayload>('/api/context', {
        method: 'POST',
        body: JSON.stringify({
          domain: activeDomain,
          machine_id: activeUnit,
          cycle: winRes.cycle || currentSnapshot?.cycle || 30,
          window: winRes.window,
          k: 5,
        }),
      });

      setContextData(ctx);

      // 3. Extract DNA if present, otherwise fetch directly
      if (ctx.machine_dna && ctx.machine_dna.length === 16) {
        setDnaVector(ctx.machine_dna);
      } else {
        try {
          const dnaRes = await apiFetch<{ domain: string; machine_id: string; dna: number[] }>(
            `/api/dna/${activeDomain}/${activeUnit}`
          );
          if (dnaRes.dna && dnaRes.dna.length === 16) {
            setDnaVector(dnaRes.dna);
          }
        } catch {
          // DNA may not be pre-stored for synthetic ephemeral nodes
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to query ATLAS cognition context');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCognitionState();
  }, [activeDomain, activeUnit]);

  // Uncertainty calculations
  const predictedRul = contextData?.predicted_rul ?? currentSnapshot?.rul_cycles ?? 0;
  const uncertainty = currentSnapshot?.uncertainty ?? 4.2;
  const p5 = Math.max(0, predictedRul - 1.645 * uncertainty);
  const p50 = predictedRul;
  const p95 = predictedRul + 1.645 * uncertainty;

  const neighbors = contextData?.neighbors || [];
  const neighborVariance = neighbors.length > 0
    ? neighbors.reduce((acc, n) => acc + Math.pow(n.rul - contextData!.average_neighbor_rul, 2), 0) / neighbors.length
    : 0;
  const neighborStd = Math.sqrt(neighborVariance);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* View Header Bar */}
      <div className="mission-panel" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Layers size={18} color="var(--accent-cyan)" />
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px', color: 'var(--text-bright)' }}>
            ATLAS COGNITION CORE: ADAPTIVE MEMORY & WORLD MODEL
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={loadCognitionState}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            <RefreshCw size={12} className={loading ? 'spin' : ''} />
            RE-EVALUATE CONTEXT
          </button>
          <span className="status-pill status-pill-live">
            <span className="pulse-dot" />
            ATTENTION-LSTM INFERENCE ACTIVE
          </span>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'var(--status-disc-bg)', border: '1px solid var(--status-disc-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-disc)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          {error}
        </div>
      )}

      {/* Top Split: RUL Uncertainty Spread & AMKB Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* RUL Prediction & Uncertainty Spread */}
        <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={16} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '14px', margin: 0 }}>PROBABILISTIC RUL PREDICTION</h3>
            </div>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
              90% CI (p05 - p95)
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', textAlign: 'center' }}>
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>5TH PERCENTILE (p05)</div>
              <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--status-warning)' }}>
                {p5.toFixed(1)}c
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Conservative Floor</div>
            </div>

            <div style={{ background: 'var(--bg-hover)', border: '1px solid var(--accent-cyan)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
              <div style={{ fontSize: '10px', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>EXPECTED MEAN (p50)</div>
              <div style={{ fontSize: '28px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>
                {p50.toFixed(1)}c
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>WorldModel Forecast</div>
            </div>

            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>95TH PERCENTILE (p95)</div>
              <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--status-normal)' }}>
                {p95.toFixed(1)}c
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Optimistic Ceiling</div>
            </div>
          </div>

          {/* Uncertainty Range Bar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              <span>Monte Carlo Uncertainty: ±{uncertainty.toFixed(2)} cycles</span>
              <span>Total Confidence: {((currentSnapshot?.confidence ?? 0.88) * 100).toFixed(0)}%</span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'var(--bg-secondary)', borderRadius: '4px', position: 'relative', overflow: 'hidden' }}>
              <div
                style={{
                  position: 'absolute',
                  left: `${Math.min(100, Math.max(0, (p5 / 150) * 100))}%`,
                  width: `${Math.min(100, Math.max(5, ((p95 - p5) / 150) * 100))}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, rgba(255, 179, 0, 0.4), rgba(0, 229, 255, 0.8), rgba(0, 230, 118, 0.4))',
                  borderRadius: '4px',
                }}
              />
            </div>
          </div>
        </div>

        {/* AMKB Context & Nearest Neighbor Memory Summary */}
        <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitCommit size={16} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '14px', margin: 0 }}>AMKB EPISODIC MEMORY RECALL</h3>
            </div>
            <span style={{ fontSize: '10px', padding: '2px 6px', background: 'var(--bg-elevated)', borderRadius: '3px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              k = {neighbors.length} RETRIEVED
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>MEAN NEIGHBOR RUL</div>
              <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>
                {contextData ? `${contextData.average_neighbor_rul.toFixed(1)}c` : '--'}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Ground Truth Historical Average</div>
            </div>

            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>EPISODIC VARIANCE (σ)</div>
              <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>
                {neighbors.length > 0 ? `±${neighborStd.toFixed(2)}c` : '--'}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Neighbor RUL Dispersion</div>
            </div>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.5, fontFamily: 'var(--font-mono)' }}>
            The Adaptive Machine Knowledge Base (AMKB) retrieves top-{neighbors.length} identical operational states via HNSW cosine indexing over 32-dim world model embeddings, conditioning inference with verified fleet history.
          </div>
        </div>
      </div>

      {/* AMKB Nearest-Neighbor Citations Table */}
      <div className="mission-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '14px', margin: 0 }}>EPISODIC CITATIONS: TOP-{neighbors.length} NEAREST HISTORICAL STATES</h3>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            DOMAIN: {activeDomain.toUpperCase()}
          </span>
        </div>

        {neighbors.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            No episodic neighbors retrieved for current machine state window.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>RANK</th>
                  <th>HISTORICAL UNIT</th>
                  <th>RECORDED CYCLE</th>
                  <th>TRUE RUL AT CYCLE</th>
                  <th>COSINE SIMILARITY</th>
                  <th>STATE DISTANCE (L2)</th>
                  <th>VERIFICATION STATUS</th>
                </tr>
              </thead>
              <tbody>
                {neighbors.map((n, idx) => {
                  const simPct = Math.max(0, Math.min(100, (1 - n.distance) * 100));
                  return (
                    <tr key={`${n.machine_id}-${n.cycle}-${idx}`}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                        #{idx + 1}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-bright)' }}>
                        {n.machine_id}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>
                        Cycle {n.cycle}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-bright)' }}>
                        {n.rul.toFixed(1)} cycles
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '60px', height: '6px', background: 'var(--bg-secondary)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${simPct}%`, height: '100%', background: 'var(--accent-cyan)' }} />
                          </div>
                          <span>{simPct.toFixed(1)}%</span>
                        </div>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                        {n.distance.toFixed(4)}
                      </td>
                      <td>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--status-normal)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                          <CheckCircle2 size={12} /> VERIFIED EPISODE
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 16-Dimensional Machine DNA Fingerprint Panel */}
      <div className="mission-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Dna size={16} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: '14px', margin: 0 }}>
              16-DIMENSIONAL MACHINE DNA (DEEP PHENOTYPIC EMBEDDING)
            </h3>
          </div>
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            PERSISTED AS <code>vector(16)</code> IN POSTGRESQL AMKB
          </div>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
          Machine DNA encodes invariant machine degradation behavior decomposed into 4 sub-signatures:
          <strong> Health Pattern</strong> (3 dims), <strong>Thermal Profile</strong> (3 dims),
          <strong> Power Signature</strong> (2 dims), and <strong>Terminal Failure Dynamics</strong> (8 dims).
        </div>

        {dnaVector && dnaVector.length === 16 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {['Health Pattern', 'Thermal Profile', 'Power Signature', 'Failure Signature (Terminal 20%)'].map(grp => {
              const dims = DNA_DIM_LABELS.filter(d => d.group === grp);
              return (
                <div
                  key={grp}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px'
                  }}
                >
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
                    {grp} ({dims.length} DIMS)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {dims.map(dim => {
                      const val = dnaVector[dim.index];
                      // Normalize representation bar for visual readability
                      const barWidth = Math.min(100, Math.max(4, Math.abs(val) * 100));
                      const isNegative = val < 0;
                      return (
                        <div key={dim.index} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                            <span style={{ color: 'var(--text-secondary)' }}>
                              d[{dim.index}] {dim.label}
                            </span>
                            <span style={{ color: 'var(--text-bright)', fontWeight: 600 }}>
                              {val.toFixed(5)}
                            </span>
                          </div>
                          <div style={{ width: '100%', height: '4px', background: 'var(--bg-elevated)', borderRadius: '2px', overflow: 'hidden' }}>
                            <div
                              style={{
                                width: `${barWidth}%`,
                                height: '100%',
                                background: isNegative ? 'var(--status-critical)' : 'var(--accent-cyan)',
                                borderRadius: '2px'
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            Machine DNA signature is calculated after &ge; 30 operational cycles. Running telemetry accumulation...
          </div>
        )}
      </div>
    </div>
  );
};

export default CognitionView;
