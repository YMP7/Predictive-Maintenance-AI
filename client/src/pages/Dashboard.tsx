import React, { useState, useEffect } from 'react';
import { useDashboardData, useMachineDetails } from '../hooks/useDashboardData';
import { MachineCard } from '../components/MachineCard';
import AgentChat from '../components/AgentChat';
import { apiFetch, errorMessage } from '../lib/api';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import { RefreshCw, Languages, MessageSquare } from 'lucide-react';

// ATLAS Cognition UI Components
import AtlasHeader from '../components/atlas/AtlasHeader';
import DomainTicker, { type DomainSnapshot } from '../components/atlas/DomainTicker';
import CommandPalette from '../components/atlas/CommandPalette';
import MonitoringView from '../components/atlas/views/MonitoringView';
import CognitionView from '../components/atlas/views/CognitionView';
import ExplainabilityView from '../components/atlas/views/ExplainabilityView';
import DecisionSupportView from '../components/atlas/views/DecisionSupportView';
import TransferStudyView from '../components/atlas/views/TransferStudyView';
import AblationsView from '../components/atlas/views/AblationsView';
import SystemDiagnosticsView from '../components/atlas/views/SystemDiagnosticsView';

const TRANSLATIONS: Record<string, Record<string, string>> = {
  en: {
    title: "AI Digital Twin & Predictive Maintenance",
    systemStatus: "System Status",
    activeAlerts: "Active Alerts",
    faultInjection: "Fault Injection Control",
    recommendation: "Recommendation",
    issuesDetected: "Issues Detected",
    vibrationTrend: "Vibration Trend (RMS mm/s)",
    temperatureTrend: "Temperature Trend (°C)",
    currentTrend: "Current Draw Trend (A)",
    normal: "Normal",
    warning: "Warning",
    critical: "Critical",
    inject: "Inject Fault",
    injectSuccess: "Fault injected successfully!"
  },
  hi: {
    title: "एआई डिजिटल ट्विन और प्रेडिक्टिव मेंटेनेंस",
    systemStatus: "सिस्टम की स्थिति",
    activeAlerts: "सक्रिय अलर्ट",
    faultInjection: "खराबी सिमुलेशन नियंत्रण",
    recommendation: "सुझाव",
    issuesDetected: "समस्याएं पाई गईं",
    vibrationTrend: "कंपन प्रवृत्ति (RMS mm/s)",
    temperatureTrend: "तापमान प्रवृत्ति (°C)",
    currentTrend: "करंट ड्रा प्रवृत्ति (A)",
    normal: "सामान्य",
    warning: "चेतावनी",
    critical: "गंभीर",
    inject: "खराबी डालें",
    injectSuccess: "खराबी सफलतापूर्वक दर्ज की गई!"
  },
  te: {
    title: "AI డిజిటల్ ట్విన్ & ప్రిడిక్టివ్ మెయింటెనెన్స్",
    systemStatus: "సిస్టమ్ స్థితి",
    activeAlerts: "క్రియాశీల హెచ్చరికలు",
    faultInjection: "ఫాల్ట్ ఇంజెక్షన్ నియంత్రణ",
    recommendation: "సిఫార్సు",
    issuesDetected: "సమస్యలు కనుగొనబడ్డాయి",
    vibrationTrend: "కంపన ట్రెండ్ (RMS mm/s)",
    temperatureTrend: "ఉష్ణోగ్రత ట్రెండ్ (°C)",
    currentTrend: "కరెంట్ డ్రా ట్రెండ్ (A)",
    normal: "సాధారణం",
    warning: "హెచ్చరిక",
    critical: "తీవ్రమైన",
    inject: "ఫాల్ట్ ఇంజెక్ట్ చేయి",
    injectSuccess: "ఫాల్ట్ విజయవంతంగా ఇంజెక్ట్ చేయబడింది!"
  },
  ta: {
    title: "AI டிஜிட்டல் ட்வின் & முன்கணிப்பு பராமரிப்பு",
    systemStatus: "கணினி நிலை",
    activeAlerts: "செயலில் உள்ள விழிப்பூட்டல்கள்",
    faultInjection: "தவறு ஊசி கட்டுப்பாடு",
    recommendation: "பரிந்துரை",
    issuesDetected: "கண்டறியப்பட்ட சிக்கல்கள்",
    vibrationTrend: "அதிர்வு போக்கு (RMS mm/s)",
    temperatureTrend: "வெப்பநிலை போக்கு (°C)",
    currentTrend: "தற்போதைய டிரா போக்கு (A)",
    normal: "சாதாரண",
    warning: "எச்சரிக்கை",
    critical: "மிகவும் முக்கியமானது",
    inject: "தவறை புகுத்து",
    injectSuccess: "தவறு வெற்றிகரமாக புகுத்தப்பட்டது!"
  },
  mr: {
    title: "एआय डिजिटल ट्विन आणि प्रेडिक्टिव्ह मेंटेनन्स",
    systemStatus: "सिस्टम स्थिती",
    activeAlerts: "सक्रिय अलर्ट",
    faultInjection: "दोष इंजेक्शन नियंत्रण",
    recommendation: "शिफारस",
    issuesDetected: "दोष आढळले",
    vibrationTrend: "कंपन ट्रेंड (RMS mm/s)",
    temperatureTrend: "तापमान ट्रेंड (°C)",
    currentTrend: "करंट ड्रा ट्रेंड (A)",
    normal: "सामान्य",
    warning: "इशारा",
    critical: "गंभीर",
    inject: "दोष प्रविष्ट करा",
    injectSuccess: "दोष यशस्वीरित्या प्रविष्ट केला गेला!"
  }
};

export const Dashboard: React.FC = () => {
  // ATLAS View & Navigation State
  const [activeView, setActiveView] = useState<string>('monitoring');
  const [activeDomain, setActiveDomain] = useState<string>('cmapss');
  const [activeUnit, setActiveUnit] = useState<string>('unit_1');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [domainSnapshots, setDomainSnapshots] = useState<Record<string, DomainSnapshot | null>>({
    cmapss: null,
    laptop: null,
    mobile: null,
    server: null,
  });

  // Legacy Phase A State
  const [selectedLang, setSelectedLang] = useState('en');
  const [selectedMachine, setSelectedMachine] = useState<string | null>('M001');
  const { summary, loading: summaryLoading, error: summaryError } = useDashboardData(2000);
  const { telemetry } = useMachineDetails(selectedMachine, 2000);
  const [injectionStatus, setInjectionStatus] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  // Auth & Roles
  const userRoleMatch = document.cookie.match(/(^|;)\s*user_role=([^;]+)/);
  const userRole = userRoleMatch ? userRoleMatch[2] : 'operator';
  const canInjectFault = userRole === 'admin' || userRole === 'operator';

  const t = TRANSLATIONS[selectedLang] || TRANSLATIONS.en;
  const currentMachine = summary?.machines.find(m => m.machine_id === selectedMachine);

  // Poll ATLAS Cross-Domain Snapshots every 3s
  useEffect(() => {
    let isMounted = true;
    const fetchDomainSnapshots = async () => {
      try {
        const res = await apiFetch<{ comparison?: Record<string, any>; snapshots?: Record<string, any> }>('/api/atlas/cross-domain/comparison');
        const rawMap = res.comparison || res.snapshots;
        if (isMounted && rawMap) {
          const normalized: Record<string, DomainSnapshot> = {};
          for (const [dom, val] of Object.entries(rawMap)) {
            if (Array.isArray(val) && val.length > 0) {
              val.forEach((m: any) => {
                if (m && m.machine_id) {
                  normalized[m.machine_id] = m;
                }
              });
              const match = val.find((m: any) => m.machine_id === activeUnit) || val[0];
              normalized[dom] = match;
            } else if (!Array.isArray(val) && val) {
              normalized[dom] = val as DomainSnapshot;
              if ((val as any).machine_id) {
                normalized[(val as any).machine_id] = val as DomainSnapshot;
              }
            }
          }
          setDomainSnapshots(prev => ({
            ...prev,
            ...normalized
          }));
        }
      } catch {
        // Fallback: Individual domain status fetch if comparison not ready
        try {
          const domRes = await apiFetch<{ domain: string; machines: DomainSnapshot[] }>(`/api/atlas/domain/${activeDomain}/status`);
          if (isMounted && domRes.machines && domRes.machines.length > 0) {
            const unitMap: Record<string, DomainSnapshot> = {};
            domRes.machines.forEach(m => {
              if (m.machine_id) unitMap[m.machine_id] = m;
            });
            const match = domRes.machines.find(m => m.machine_id === activeUnit) || domRes.machines[0];
            setDomainSnapshots(prev => ({
              ...prev,
              ...unitMap,
              [activeDomain]: match
            }));
          }
        } catch {
          // Handled gracefully in UI
        }
      }
    };

    fetchDomainSnapshots();
    const interval = setInterval(fetchDomainSnapshots, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [activeDomain, activeUnit]);

  const handleDomainChange = (domain: string) => {
    setActiveDomain(domain);
    if (domain === 'cmapss') setActiveUnit('unit_1');
    else if (domain === 'laptop') setActiveUnit('laptop_host');
    else if (domain === 'mobile') setActiveUnit('mobile_device_1');
    else if (domain === 'server') setActiveUnit('server_node_1');
  };

  const handleSelectDomainUnit = (domain: string, unitId: string) => {
    setActiveDomain(domain);
    setActiveUnit(unitId);
    setActiveView('monitoring');
  };

  const handleLogout = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Ignore
    } finally {
      document.cookie = "auth_status=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      document.cookie = "user_role=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      window.location.href = '/login';
    }
  };

  const handleInjectFault = async (faultMode: string) => {
    if (!selectedMachine) return;
    try {
      await apiFetch(`/api/machines/${selectedMachine}/fault`, {
        method: 'POST',
        body: JSON.stringify({ fault_mode: faultMode })
      });
      setInjectionStatus({ message: `${t.injectSuccess} (${faultMode})`, type: 'success' });
      setTimeout(() => setInjectionStatus(null), 3000);
    } catch (err: unknown) {
      setInjectionStatus({ message: errorMessage(err, 'Connection error.'), type: 'error' });
      setTimeout(() => setInjectionStatus(null), 3000);
    }
  };

  const currentSnapshot = (activeUnit && domainSnapshots[activeUnit]) || domainSnapshots[activeDomain] || null;

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Top Universal Mission Control Header */}
      <AtlasHeader
        activeView={activeView}
        onSelectView={setActiveView}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        systemStatus="NOMINAL"
        userRole={userRole}
        onLogout={handleLogout}
      />

      {/* Global Command Palette Modal (Ctrl+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectView={setActiveView}
        onSelectDomainUnit={handleSelectDomainUnit}
      />

      {/* 4-Domain Operational Status Ticker (Visible across operational views) */}
      {activeView !== 'legacy_iot' && (
        <DomainTicker
          snapshots={domainSnapshots}
          activeDomain={activeDomain}
          activeUnit={activeUnit}
          onSelectDomainUnit={handleSelectDomainUnit}
          onSelectDomain={handleDomainChange}
        />
      )}

      {/* Universal Multi-Unit Switcher Strip (Visible for multi-unit domains like Mobile) */}
      {activeDomain === 'mobile' && activeView !== 'legacy_iot' && (
        <div
          className="mission-panel"
          style={{
            padding: '10px 16px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            borderLeft: '3px solid var(--accent-cyan)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              ACTIVE MOBILE UNIT:
            </span>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => setActiveUnit('mobile_device_1')}
                style={{
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-xs)',
                  border: activeUnit === 'mobile_device_1' ? '1.5px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                  background: activeUnit === 'mobile_device_1' ? 'var(--accent-cyan-dim)' : 'var(--bg-elevated)',
                  color: activeUnit === 'mobile_device_1' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  fontWeight: activeUnit === 'mobile_device_1' ? 700 : 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span className={domainSnapshots['mobile_device_1']?.adapter_status === 'live' ? "pulse-dot" : ""} style={{ width: 8, height: 8, borderRadius: '50%', background: domainSnapshots['mobile_device_1']?.adapter_status === 'live' ? 'var(--status-normal)' : 'var(--text-muted)' }} />
                <span>mobile_device_1</span>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(255,255,255,0.08)', color: 'var(--accent-cyan)', fontWeight: 700 }}>WIFI</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveUnit('mobile_device_2')}
                style={{
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-xs)',
                  border: activeUnit === 'mobile_device_2' ? '1.5px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                  background: activeUnit === 'mobile_device_2' ? 'var(--accent-cyan-dim)' : 'var(--bg-elevated)',
                  color: activeUnit === 'mobile_device_2' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  fontWeight: activeUnit === 'mobile_device_2' ? 700 : 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span className={domainSnapshots['mobile_device_2']?.adapter_status === 'live' ? "pulse-dot" : ""} style={{ width: 8, height: 8, borderRadius: '50%', background: domainSnapshots['mobile_device_2']?.adapter_status === 'live' ? 'var(--status-normal)' : 'var(--text-muted)' }} />
                <span>mobile_device_2</span>
                <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', background: 'rgba(255,255,255,0.08)', color: 'var(--accent-cyan)', fontWeight: 700 }}>USB</span>
              </button>
            </div>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            2 Hardware Units Connected Concurrently
          </div>
        </div>
      )}

      {/* Primary Dynamic Operational Workspace */}
      <main style={{ marginTop: '16px', flex: 1 }}>
        {activeView === 'monitoring' && (
          <MonitoringView
            activeDomain={activeDomain}
            activeUnit={activeUnit}
            onSelectUnit={setActiveUnit}
            currentSnapshot={currentSnapshot}
          />
        )}

        {activeView === 'cognition' && (
          <CognitionView
            activeDomain={activeDomain}
            activeUnit={activeUnit}
            currentSnapshot={currentSnapshot}
          />
        )}

        {activeView === 'explainability' && (
          <ExplainabilityView
            activeDomain={activeDomain}
            activeUnit={activeUnit}
            currentSnapshot={currentSnapshot}
          />
        )}

        {(activeView === 'decision' || activeView === 'decisions') && (
          <DecisionSupportView
            activeDomain={activeDomain}
            activeUnit={activeUnit}
            currentSnapshot={currentSnapshot}
          />
        )}

        {activeView === 'transfer' && (
          <TransferStudyView />
        )}

        {activeView === 'ablations' && (
          <AblationsView />
        )}

        {activeView === 'system' && (
          <SystemDiagnosticsView activeDomain={activeDomain} />
        )}

        {/* Phase A IoT Lab (Preserved for 100% Backward Compatibility) */}
        {activeView === 'legacy_iot' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Phase A Sub-Header */}
            <div className="mission-panel" style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h2 style={{ fontSize: '16px', fontWeight: 800, margin: 0, color: 'var(--text-bright)' }}>
                  PHASE A: IOT MOTOR DIGITAL TWIN LAB (HISTORICAL PROTOTYPE)
                </h2>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  4-Machine Fleet Digital Twin (M001–M004) with Fault Injection & Multilingual Bhashini Voice Interface
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Languages size={14} color="var(--text-secondary)" />
                  <select
                    value={selectedLang}
                    onChange={(e) => setSelectedLang(e.target.value)}
                    style={{
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-bright)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-xs)',
                      padding: '4px 8px',
                      fontSize: '11px',
                      fontFamily: 'var(--font-mono)',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="en">English</option>
                    <option value="hi">हिंदी (Hindi)</option>
                    <option value="te">తెలుగు (Telugu)</option>
                    <option value="ta">தமிழ் (Tamil)</option>
                    <option value="mr">मराठी (Marathi)</option>
                  </select>
                </div>

                <button
                  onClick={() => setChatOpen(true)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    background: 'var(--accent-cyan)',
                    color: '#070B12',
                    borderRadius: 'var(--radius-xs)',
                    cursor: 'pointer'
                  }}
                >
                  <MessageSquare size={13} />
                  AGENT CHAT
                </button>
              </div>
            </div>

            {summaryError && (
              <div style={{ padding: '12px 16px', background: 'var(--status-disc-bg)', border: '1px solid var(--status-disc-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-disc)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                <strong>API Connection Notice:</strong> FastAPI backend reachable on port 8000.
              </div>
            )}

            {/* Main IoT Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 340px) 1fr', gap: '20px' }}>
              {/* Asset List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  PHYSICAL ASSETS ({summary?.machines?.length ?? 4} MACHINES)
                </div>
                {summaryLoading ? (
                  <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}><RefreshCw className="spin" /></div>
                ) : (
                  summary?.machines.map(machine => (
                    <MachineCard
                      key={machine.machine_id}
                      machine={machine}
                      isSelected={selectedMachine === machine.machine_id}
                      onClick={() => setSelectedMachine(machine.machine_id)}
                    />
                  ))
                )}
              </div>

              {/* Machine Details & Live Telemetry Charts */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {currentMachine ? (
                  <div className="mission-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', flexWrap: 'wrap', gap: '12px' }}>
                      <div>
                        <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: 'var(--text-bright)' }}>
                          {currentMachine.machine_info.name} Digital Twin
                        </h2>
                        <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {currentMachine.machine_id} // {currentMachine.machine_info.location}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <span className={`badge badge-${currentMachine.status.toLowerCase()}`}>{currentMachine.status}</span>
                        <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                          Fault: {currentMachine.fault_type}
                        </span>
                      </div>
                    </div>

                    {/* Sensor Metric Tiles */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
                      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>VIBRATION RMS</div>
                        <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>
                          {telemetry.length > 0 && (telemetry[telemetry.length - 1]?.vibration_rms ?? telemetry[telemetry.length - 1]?.vibration?.rms) != null
                            ? `${(telemetry[telemetry.length - 1]?.vibration_rms ?? telemetry[telemetry.length - 1]?.vibration?.rms ?? 0).toFixed(2)} mm/s`
                            : '--'}
                        </div>
                      </div>
                      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>TEMPERATURE</div>
                        <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>
                          {telemetry.length > 0 && telemetry[telemetry.length - 1]?.temperature != null ? `${telemetry[telemetry.length - 1].temperature.toFixed(1)} °C` : '--'}
                        </div>
                      </div>
                      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>CURRENT DRAW</div>
                        <div style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-bright)' }}>
                          {telemetry.length > 0 && (telemetry[telemetry.length - 1]?.current_draw ?? telemetry[telemetry.length - 1]?.current) != null
                            ? `${(telemetry[telemetry.length - 1]?.current_draw ?? telemetry[telemetry.length - 1]?.current ?? 0).toFixed(2)} A`
                            : '--'}
                        </div>
                      </div>
                    </div>

                    {/* Live Charts */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {t.vibrationTrend}
                      </div>
                      <div style={{ width: '100%', height: '160px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={telemetry} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="timestamp" stroke="var(--text-muted)" fontSize={10} fontFamily="var(--font-mono)" tickFormatter={(val) => new Date(val).toLocaleTimeString()} />
                            <YAxis stroke="var(--text-muted)" fontSize={10} fontFamily="var(--font-mono)" domain={['auto', 'auto']} />
                            <Tooltip contentStyle={{ background: 'var(--bg-elevated)', borderColor: 'var(--border-hover)', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: '11px' }} />
                            <Line type="monotone" dataKey="vibration_rms" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} isAnimationActive={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Fault Injection Panel (Restricted to Operator/Admin) */}
                    {canInjectFault && (
                      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--status-warning)', fontFamily: 'var(--font-mono)' }}>
                          {t.faultInjection} (ADMIN PRIVILEGE)
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          {['Bearing Wear', 'Imbalance', 'Overheating', 'Misalignment', 'Normal'].map((mode) => (
                            <button
                              key={mode}
                              onClick={() => handleInjectFault(mode)}
                              style={{
                                padding: '6px 12px',
                                fontSize: '11px',
                                fontFamily: 'var(--font-mono)',
                                background: 'var(--bg-secondary)',
                                border: '1px solid var(--border-color)',
                                color: 'var(--text-bright)',
                                borderRadius: 'var(--radius-xs)',
                                cursor: 'pointer'
                              }}
                            >
                              {mode}
                            </button>
                          ))}
                        </div>
                        {injectionStatus && (
                          <div style={{ fontSize: '11px', color: injectionStatus.type === 'success' ? 'var(--status-normal)' : 'var(--status-critical)', fontFamily: 'var(--font-mono)' }}>
                            {injectionStatus.message}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="mission-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                    Select an asset to view digital twin telemetry.
                  </div>
                )}
              </div>
            </div>

            {/* Agent Chat Modal Overlay */}
            <AgentChat
              isOpen={chatOpen}
              onClose={() => setChatOpen(false)}
              machineId={selectedMachine || undefined}
            />
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
