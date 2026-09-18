import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../../lib/api';
import { HelpCircle, AlertTriangle, TrendingDown, TrendingUp, Info, RefreshCw } from 'lucide-react';
import type { DomainSnapshot } from '../DomainTicker';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine, Cell } from 'recharts';

interface SensorAttribution {
  sensor_index: number;
  sensor_name: string;
  magnitude: number;
  signed_delta: number;
}

interface ExplanationReportPayload {
  confidence_score: number;
  confidence_level: 'High' | 'Moderate' | 'Low' | string;
  primary_justification: string;
  citations: string[];
  note?: string;
  sensor_attributions: SensorAttribution[];
  top_contributors: string[];
  attribution_unavailable_reason?: string | null;
}

interface ExplainabilityViewProps {
  activeDomain: string;
  activeUnit: string;
  currentSnapshot: DomainSnapshot | null;
}

export const ExplainabilityView: React.FC<ExplainabilityViewProps> = ({
  activeDomain,
  activeUnit,
  currentSnapshot,
}) => {
  const [report, setReport] = useState<ExplanationReportPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadExplanation = async () => {
    try {
      setLoading(true);
      setError(null);

      // 1. Fetch live window
      const winRes = await apiFetch<{
        domain: string;
        machine_id: string;
        window: number[][];
        cycle: number;
        feature_dim: number;
      }>(`/api/atlas/domain/${activeDomain}/machine/${activeUnit}/window`);

      // 2. Query /api/explain
      const data = await apiFetch<ExplanationReportPayload>('/api/explain', {
        method: 'POST',
        body: JSON.stringify({
          domain: activeDomain,
          machine_id: activeUnit,
          cycle: winRes.cycle || currentSnapshot?.cycle || 30,
          window: winRes.window,
          k: 5,
        }),
      });

      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to compute model explainability report');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExplanation();
  }, [activeDomain, activeUnit]);

  // Confidence indicators
  const confScore = report?.confidence_score ?? 0;
  const confLevel = report?.confidence_level || 'Moderate';

  let confColor = 'var(--status-normal)';
  if (confLevel === 'Low') confColor = 'var(--status-critical)';
  else if (confLevel === 'Moderate') confColor = 'var(--status-warning)';

  const attributions = report?.sensor_attributions || [];
  const unavailableReason = report?.attribution_unavailable_reason;

  // Chart data formatting
  const chartData = attributions.map(attr => ({
    name: attr.sensor_name.split(' ')[0], // e.g. "s3"
    fullName: attr.sensor_name,
    signed_delta: attr.signed_delta,
    magnitude: attr.magnitude,
    direction: attr.signed_delta > 0 ? 'Degradation / Failure Push' : 'Health / Stability Support'
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* View Header */}
      <div className="mission-panel" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <HelpCircle size={18} color="var(--accent-cyan)" />
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px', color: 'var(--text-bright)' }}>
            ATLAS EXPLAINABILITY ENGINE: OCCLUSION ATTRIBUTION & EPISODIC GROUNDING
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={loadExplanation}
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
            RE-RUN OCCLUSION AUDIT
          </button>
          <span className="status-pill status-pill-live">
            <span className="pulse-dot" />
            EPISODIC GROUNDING ACTIVE
          </span>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'var(--status-disc-bg)', border: '1px solid var(--status-disc-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-disc)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          {error}
        </div>
      )}

      {/* Top Split: Grounding Confidence & Epistemic Justification */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 360px) 1fr', gap: '16px' }}>
        {/* Confidence Card */}
        <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '14px', margin: 0 }}>GROUNDING CONFIDENCE</h3>
            <span style={{
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              color: confColor,
              padding: '2px 8px',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-xs)',
              border: `1px solid ${confColor}`
            }}>
              {confLevel.toUpperCase()}
            </span>
          </div>

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
              Confidence Score (Bounded [0, 1])
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '42px', color: confColor, lineHeight: 1 }}>
              {confScore.toFixed(3)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              Formula: <code>avg_sim &times; [1 / (1 + variance)]</code>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Historical Grounding:</span>
              <span style={{ color: 'var(--status-normal)' }}>Verified AMKB Episodes</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Circular Guard:</span>
              <span style={{ color: 'var(--accent-cyan)' }}>Strict True-RUL Citations</span>
            </div>
            {report?.note && (
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '6px 8px', borderRadius: 'var(--radius-xs)', marginTop: '4px' }}>
                {report.note}
              </div>
            )}
          </div>
        </div>

        {/* Primary Natural Language Justification Card */}
        <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Info size={16} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: '14px', margin: 0 }}>PRIMARY INFERENCE JUSTIFICATION</h3>
          </div>

          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderLeft: '4px solid var(--accent-cyan)',
            borderRadius: 'var(--radius-sm)',
            padding: '16px',
            fontSize: '13px',
            lineHeight: 1.6,
            color: 'var(--text-bright)',
            fontFamily: 'var(--font-sans)'
          }}>
            {report?.primary_justification || 'Awaiting inference explanation generation...'}
          </div>

          {/* Top Contributing Sensors */}
          {report?.top_contributors && report.top_contributors.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                PRIMARY INFLUENTIAL CHANNELS:
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {report.top_contributors.map((c, i) => (
                  <span
                    key={i}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-hover)',
                      borderRadius: 'var(--radius-xs)',
                      padding: '4px 10px',
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--accent-cyan)',
                      fontWeight: 600
                    }}
                  >
                    #{i + 1} {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Direct Citations List */}
          {report?.citations && report.citations.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                AMKB RETRIEVAL CITATIONS:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {report.citations.map((cite, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-secondary)',
                      background: 'var(--bg-secondary)',
                      padding: '4px 8px',
                      borderRadius: 'var(--radius-xs)'
                    }}
                  >
                    &bull; {cite}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Occlusion Sensitivity Attribution Panel */}
      <div className="mission-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3 style={{ fontSize: '14px', margin: '0 0 4px 0' }}>
              SENSOR OCCLUSION ATTRIBUTION (14-CHANNEL SENSITIVITY)
            </h3>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              DIVERGING SIGNED DELTA: &Delta;RUL = RUL<sub>occluded</sub> - RUL<sub>baseline</sub>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--status-critical)' }}>
              <TrendingDown size={14} /> Red: Push Toward Shorter RUL (Degradation)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--status-normal)' }}>
              <TrendingUp size={14} /> Green: Push Toward Longer RUL (Health)
            </span>
          </div>
        </div>

        {unavailableReason ? (
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderLeft: '4px solid var(--status-warning)',
            borderRadius: 'var(--radius-sm)',
            padding: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px'
          }}>
            <AlertTriangle size={18} color="var(--status-warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: 700, fontSize: '12px', color: 'var(--text-bright)', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                OCCLUSION SENSITIVITY RESTRICTED TO C-MAPSS TURBOFAN DOMAIN
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {unavailableReason}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', fontFamily: 'var(--font-mono)' }}>
                Domains with feature_dim = 5 (Laptop, Mobile, Server) use episodic AMKB similarity and variance metrics for explainability. Occlusion sensitivity requires the full 14-sensor turbofan degradation manifold.
              </div>
            </div>
          </div>
        ) : chartData.length > 0 ? (
          <div style={{ width: '100%', height: '320px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 20, left: 10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="name"
                  stroke="var(--text-muted)"
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                />
                <YAxis
                  stroke="var(--text-muted)"
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickLine={false}
                  label={{ value: 'Signed Delta (Cycles)', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.2)" />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-elevated)',
                    borderColor: 'var(--border-hover)',
                    borderRadius: 'var(--radius-sm)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '11px',
                    color: 'var(--text-bright)'
                  }}
                  formatter={(val: any, _name: any, item: any) => [
                    `${Number(val).toFixed(2)} cycles (${item.payload.direction})`,
                    `Signed Delta`
                  ]}
                  labelFormatter={(_label: any, items: any) => {
                    if (items && items[0]) {
                      return items[0].payload.fullName;
                    }
                    return '';
                  }}
                />
                <Bar dataKey="signed_delta" radius={[3, 3, 0, 0]}>
                  {chartData.map((entry, idx) => (
                    <Cell
                      key={`cell-${idx}`}
                      fill={entry.signed_delta > 0 ? 'var(--status-critical)' : 'var(--status-normal)'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
            Computing 14-sensor occlusion sensitivity passes...
          </div>
        )}
      </div>
    </div>
  );
};

export default ExplainabilityView;
