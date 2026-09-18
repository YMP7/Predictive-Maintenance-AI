import React, { useState, useEffect } from 'react';
import { apiFetch } from '../../../lib/api';
import { Compass, ShieldAlert, CheckCircle2, RefreshCw } from 'lucide-react';
import type { DomainSnapshot } from '../DomainTicker';

interface SimulationResult {
  action: string;
  expected_cost: number;
  cost_std: number;
  p_failure_before_action: number;
}

interface DecisionRecommendation {
  recommended_action: string;
  ranked_actions: SimulationResult[];
  confidence: number;
  risk: number;
  impact: number;
  urgency: number;
  explanation: {
    confidence_score: number;
    confidence_level: string;
    primary_justification: string;
    citations: string[];
  };
}

interface DecisionSupportViewProps {
  activeDomain: string;
  activeUnit: string;
  currentSnapshot: DomainSnapshot | null;
}

const ACTION_METADATA: Record<string, { label: string; leadTime: string; desc: string }> = {
  CONTINUE_OPERATION: {
    label: 'Continue Normal Operation',
    leadTime: '30 Cycles Horizon',
    desc: 'Maintain current production baseline without immediate maintenance intervention.'
  },
  SCHEDULE_MAINTENANCE_SOON: {
    label: 'Schedule Maintenance (Routine)',
    leadTime: '10 Cycles Lead Time',
    desc: 'Plan planned depot service at next scheduled turnaround shift.'
  },
  SCHEDULE_MAINTENANCE_NOW: {
    label: 'Schedule Maintenance (Expedited)',
    leadTime: '3 Cycles Lead Time',
    desc: 'Expedite priority servicing within the current 72-hour operating window.'
  },
  REPLACE_IMMEDIATELY: {
    label: 'Replace / Overhaul Immediately',
    leadTime: '0 Cycles (Instant)',
    desc: 'Immediately isolate equipment and execute hot-swap replacement to eliminate failure risk.'
  }
};

export const DecisionSupportView: React.FC<DecisionSupportViewProps> = ({
  activeDomain,
  activeUnit,
  currentSnapshot,
}) => {
  const [decision, setDecision] = useState<DecisionRecommendation | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadDecision = async () => {
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

      // 2. Query /api/decide
      const data = await apiFetch<DecisionRecommendation>('/api/decide', {
        method: 'POST',
        body: JSON.stringify({
          domain: activeDomain,
          machine_id: activeUnit,
          cycle: winRes.cycle || currentSnapshot?.cycle || 30,
          window: winRes.window,
          k: 5,
        }),
      });

      setDecision(data);
    } catch (err: any) {
      setError(err.message || 'Failed to query ATLAS decision graph');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDecision();
  }, [activeDomain, activeUnit]);

  const recommendedAction = decision?.recommended_action || 'CONTINUE_OPERATION';
  const ranked = decision?.ranked_actions || [];
  const topAction = ranked.find(r => r.action === recommendedAction) || ranked[0];

  // Check whether a safety constraint override is active:
  // An override occurs if CONTINUE_OPERATION has non-zero failure probability and a more urgent action was mandated
  const continueAction = ranked.find(r => r.action === 'CONTINUE_OPERATION');
  const isSafetyOverride =
    recommendedAction !== 'CONTINUE_OPERATION' &&
    continueAction &&
    continueAction.p_failure_before_action > 0.005;

  const riskScore = decision ? Math.min(1.0, decision.risk) : 0;
  const impactScore = decision?.impact ?? 0;
  const urgencyScore = decision?.urgency ?? 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header Bar */}
      <div className="mission-panel" style={{ padding: '12px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Compass size={18} color="var(--accent-cyan)" />
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '14px', color: 'var(--text-bright)' }}>
            ATLAS DECISION GRAPH: MONTE CARLO RISK SIMULATION & ACTION RANKING
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={loadDecision}
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
            RE-SIMULATE ACTIONS
          </button>
          <span className="status-pill status-pill-live">
            <span className="pulse-dot" />
            1,000 MONTE CARLO SAMPLES
          </span>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'var(--status-disc-bg)', border: '1px solid var(--status-disc-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-disc)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          {error}
        </div>
      )}

      {/* Safety Override Banner */}
      {isSafetyOverride && (
        <div style={{
          background: 'rgba(255, 59, 48, 0.12)',
          border: '1px solid var(--status-critical)',
          borderRadius: 'var(--radius-sm)',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert size={20} color="var(--status-critical)" />
            <div>
              <div style={{ fontWeight: 800, fontSize: '12px', color: 'var(--status-critical)', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>
                SAFETY CONSTRAINT OVERRIDE ACTIVE
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-bright)', marginTop: '2px' }}>
                Passive continuation rejected: <code>p(fail before 30c) = {((continueAction?.p_failure_before_action ?? 0) * 100).toFixed(1)}%</code> exceeds permissible safety threshold. System elevated to <strong>{recommendedAction}</strong>.
              </div>
            </div>
          </div>
          <span style={{ fontSize: '11px', padding: '4px 8px', background: 'var(--status-critical)', color: '#fff', borderRadius: 'var(--radius-xs)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
            DEF-008 ZERO-MISS SAFETY PARITY ENFORCED
          </span>
        </div>
      )}

      {/* Recommended Action Hero Panel */}
      <div className="mission-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
            ATLAS AUTONOMOUS RECOMMENDATION
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            UNIT: <strong style={{ color: 'var(--text-bright)' }}>{activeUnit}</strong> | DOMAIN: <strong style={{ color: 'var(--text-bright)' }}>{activeDomain.toUpperCase()}</strong>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '24px', color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
              {ACTION_METADATA[recommendedAction]?.label || recommendedAction}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {ACTION_METADATA[recommendedAction]?.desc}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>EXPECTED COST</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '24px', color: 'var(--status-normal)' }}>
                ${topAction?.expected_cost.toFixed(2) ?? '--'}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>FAILURE PROBABILITY</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '24px', color: (topAction?.p_failure_before_action ?? 0) > 0.05 ? 'var(--status-critical)' : 'var(--status-normal)' }}>
                {topAction ? `${(topAction.p_failure_before_action * 100).toFixed(1)}%` : '--'}
              </div>
            </div>
          </div>
        </div>

        {/* 3 Core Higher-Level Operational Signals: Risk, Impact, Urgency */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginTop: '8px' }}>
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              OPERATIONAL RISK
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: riskScore > 0.4 ? 'var(--status-critical)' : riskScore > 0.15 ? 'var(--status-warning)' : 'var(--status-normal)' }}>
              {(riskScore * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              p(fail) + &sigma;<sub>cost</sub> / $1k
            </div>
          </div>

          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              DECISION IMPACT
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
              ${impactScore.toFixed(1)}
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Cost spread vs worst action
            </div>
          </div>

          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              ACTION URGENCY
            </div>
            <div style={{ fontSize: '20px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: urgencyScore > 5 ? 'var(--status-critical)' : urgencyScore > 2 ? 'var(--status-warning)' : 'var(--status-normal)' }}>
              {urgencyScore.toFixed(2)}x
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              100 / (RUL + &sigma;<sup>2</sup> + 1)
            </div>
          </div>
        </div>
      </div>

      {/* 4-Action Ranking Table */}
      <div className="mission-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '14px', margin: 0 }}>
            DISCRETE ACTION EVALUATION MATRIX (SORTED BY EXPECTED COST)
          </h3>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            N = 1,000 PROPAGATED MONTE CARLO TRIALS
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>RANK</th>
                <th>ACTION CANDIDATE</th>
                <th>ASSUMED LEAD TIME</th>
                <th>EXPECTED COST (E[C])</th>
                <th>COST DISPERSION (&sigma;)</th>
                <th>FAILURE RISK P(FAIL &le; LEAD)</th>
                <th>OPTIMALITY STATUS</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((res, idx) => {
                const isSelected = res.action === recommendedAction;
                const meta = ACTION_METADATA[res.action];
                return (
                  <tr
                    key={res.action}
                    style={{
                      background: isSelected ? 'var(--bg-hover)' : 'transparent',
                    }}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                      #{idx + 1}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: isSelected ? 700 : 500, color: 'var(--text-bright)' }}>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span>{meta?.label || res.action}</span>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{res.action}</span>
                      </div>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {meta?.leadTime || '--'}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-bright)' }}>
                      ${res.expected_cost.toFixed(2)}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      &plusmn;${res.cost_std.toFixed(2)}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      <span style={{
                        color: res.p_failure_before_action > 0.05 ? 'var(--status-critical)' : res.p_failure_before_action > 0 ? 'var(--status-warning)' : 'var(--status-normal)',
                        fontWeight: 600
                      }}>
                        {(res.p_failure_before_action * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      {isSelected ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          background: 'rgba(0, 229, 255, 0.15)',
                          color: 'var(--accent-cyan)',
                          padding: '3px 8px',
                          borderRadius: 'var(--radius-xs)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '11px',
                          fontWeight: 700,
                          border: '1px solid var(--accent-cyan)'
                        }}>
                          <CheckCircle2 size={12} /> RECOMMENDED
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          SUB-OPTIMAL
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DecisionSupportView;
