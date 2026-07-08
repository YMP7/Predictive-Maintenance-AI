import React, { useState } from 'react';
import { useDashboardData, useMachineDetails } from '../hooks/useDashboardData';
import { useTheme } from '../contexts/ThemeContext';
import { MachineCard } from '../components/MachineCard';
import { apiFetch } from '../lib/api';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import {
  Activity, AlertTriangle, ShieldCheck, Thermometer, Zap, RefreshCw, Languages, Info, Sun, Moon
} from 'lucide-react';

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

const Dashboard: React.FC = () => {
  const [selectedLang, setSelectedLang] = useState('en');
  const [selectedMachine, setSelectedMachine] = useState<string | null>('M001');
  const { summary, loading: summaryLoading, error: summaryError } = useDashboardData(2000);
  const { telemetry, loading: _detailsLoading } = useMachineDetails(selectedMachine, 2000);
  const [injectionStatus, setInjectionStatus] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const { theme, toggleTheme } = useTheme();

  const t = TRANSLATIONS[selectedLang] || TRANSLATIONS.en;

  const currentMachine = summary?.machines.find(m => m.machine_id === selectedMachine);

  const handleInjectFault = async (faultMode: string) => {
    if (!selectedMachine) return;
    try {
      await apiFetch(`/api/machines/${selectedMachine}/fault`, {
        method: 'POST',
        body: JSON.stringify({ fault_mode: faultMode })
      });
      setInjectionStatus({ message: `${t.injectSuccess} (${faultMode})`, type: 'success' });
      setTimeout(() => setInjectionStatus(null), 3000);
    } catch (err: any) {
      setInjectionStatus({ message: err.message || "Connection error.", type: 'error' });
      setTimeout(() => setInjectionStatus(null), 3000);
    }
  };

  const getSystemStatusIcon = () => {
    if (!summary) return null;
    const criticals = summary.machine_status_counts.Critical;
    const warnings = summary.machine_status_counts.Warning;
    if (criticals > 0) return <AlertTriangle size={20} style={{ color: 'var(--status-critical)' }} />;
    if (warnings > 0) return <AlertTriangle size={20} style={{ color: 'var(--status-warning)' }} />;
    return <ShieldCheck size={20} style={{ color: 'var(--status-normal)' }} />;
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Header Panel */}
      <header className="glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="gradient-text" style={{ fontSize: '24px', fontWeight: 800 }}>{t.title}</h1>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Enterprise Industry 4.0 Predictive Edge Analytics Gateway
          </p>
        </div>

        {/* Global Controls & Localization */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255, 255, 255, 0.03)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            {getSystemStatusIcon()}
            <span style={{ fontSize: '13px', fontWeight: 600 }}>
              {t.systemStatus}: {summary?.machine_status_counts.Critical ? t.critical : summary?.machine_status_counts.Warning ? t.warning : t.normal}
            </span>
          </div>

          <a href="/" style={{ color: 'var(--text-secondary)', fontSize: '13px', textDecoration: 'none' }}>← Home</a>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Languages size={18} style={{ color: 'var(--text-secondary)' }} />
            <select 
              value={selectedLang} 
              onChange={(e) => setSelectedLang(e.target.value)}
              style={{
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                padding: '6px 10px',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
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
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '6px'
            }}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          
          <button 
            onClick={() => { localStorage.removeItem('token'); localStorage.removeItem('role'); window.location.href='/login'; }}
            style={{
              background: 'var(--bg-secondary)', color: 'var(--text-primary)', 
              border: '1px solid var(--border-color)', padding: '6px 12px', 
              borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 600
            }}>
            Logout
          </button>
        </div>
      </header>

      {summaryError && (
        <div className="glass-panel" style={{ borderColor: 'var(--status-critical)', color: 'var(--status-critical)', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <AlertTriangle size={24} />
          <div>
            <strong>API Connection Error:</strong> Please verify the integrated FastAPI server is running on <code style={{ fontFamily: 'var(--font-mono)' }}>localhost:8000</code>.
          </div>
        </div>
      )}

      {/* Main Grid */}
      <main style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
        
        {/* Left Side: Machines Grid */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Physical Assets</h2>
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
        </section>

        {/* Right Side: Details & Digital Twin Graphs */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Active Machine details card */}
          {currentMachine ? (
            <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h2 style={{ fontSize: '20px', fontWeight: 700 }}>{currentMachine.machine_info.name} Digital Twin</h2>
                  <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{currentMachine.machine_id} // {currentMachine.machine_info.location}</span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <span className={`badge badge-${currentMachine.status.toLowerCase()}`}>{currentMachine.status}</span>
                  <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                    Fault: {currentMachine.fault_type}
                  </span>
                </div>
              </div>

              {/* Grid of details */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
                {/* Recommendation & Issues */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{t.recommendation}:</span>
                  <p style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>{currentMachine.recommendation}</p>
                  
                  {currentMachine.detected_issues.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{t.issuesDetected}:</span>
                      <ul style={{ fontSize: '13px', color: 'var(--status-warning)', marginLeft: '16px', marginTop: '4px' }}>
                        {currentMachine.detected_issues.map((issue, idx) => <li key={idx}>{issue}</li>)}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Remaining Useful Life status */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', background: 'rgba(255, 255, 255, 0.02)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Remaining Useful Life (RUL):</span>
                  <span style={{ fontSize: '32px', fontWeight: 800, fontFamily: 'var(--font-mono)', color: currentMachine.rul_days && currentMachine.rul_days < 7 ? 'var(--status-critical)' : 'var(--status-normal)' }}>
                    {currentMachine.rul_days !== null ? `${currentMachine.rul_days} Days` : 'Estimating...'}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Confidence Score: {Math.round(currentMachine.rul_confidence * 100)}%</span>
                </div>

                {/* Fault injector controls */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{t.faultInjection}:</span>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    <button onClick={() => handleInjectFault('bearing_wear')}>{t.inject} (Bearing)</button>
                    <button onClick={() => handleInjectFault('misalignment')}>{t.inject} (Align)</button>
                    <button onClick={() => handleInjectFault('overheating')}>{t.inject} (Heat)</button>
                    <button onClick={() => handleInjectFault('electrical_fault')}>{t.inject} (Elec)</button>
                    <button style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--status-normal)' }} onClick={() => handleInjectFault('normal')}>Reset Normal</button>
                  </div>
                  {injectionStatus && (
                    <div style={{ fontSize: '12px', color: injectionStatus.type === 'error' ? 'var(--status-critical)' : 'var(--status-normal)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {injectionStatus.type === 'error' ? <AlertTriangle size={12} /> : <Info size={12} />} {injectionStatus.message}
                    </div>
                  )}
                </div>
              </div>

              {/* Trend Graphs */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Real-Time Diagnostics</h3>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                  
                  {/* Vibration Chart */}
                  <div className="glass-panel" style={{ padding: '16px', height: '220px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Activity size={14} style={{ color: 'var(--accent-primary)' }} /> {t.vibrationTrend}
                      </span>
                    </div>
                    <ResponsiveContainer width="100%" height="80%">
                      <LineChart data={telemetry.map((point, idx) => ({ idx, rms: point.vibration.rms }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="idx" hide />
                        <YAxis domain={[0, 'auto']} stroke="var(--text-secondary)" />
                        <Tooltip contentStyle={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }} />
                        <Line type="monotone" dataKey="rms" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Temperature Chart */}
                  <div className="glass-panel" style={{ padding: '16px', height: '220px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Thermometer size={14} style={{ color: 'var(--status-warning)' }} /> {t.temperatureTrend}
                      </span>
                    </div>
                    <ResponsiveContainer width="100%" height="80%">
                      <LineChart data={telemetry.map((point, idx) => ({ idx, temp: point.temperature }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="idx" hide />
                        <YAxis domain={['dataMin - 5', 'auto']} stroke="var(--text-secondary)" />
                        <Tooltip contentStyle={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }} />
                        <Line type="monotone" dataKey="temp" stroke="#f59e0b" strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Current Chart */}
                  <div className="glass-panel" style={{ padding: '16px', height: '220px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Zap size={14} style={{ color: 'var(--status-critical)' }} /> {t.currentTrend}
                      </span>
                    </div>
                    <ResponsiveContainer width="100%" height="80%">
                      <LineChart data={telemetry.map((point, idx) => ({ idx, curr: point.current }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="idx" hide />
                        <YAxis domain={[0, 'auto']} stroke="var(--text-secondary)" />
                        <Tooltip contentStyle={{ background: 'var(--bg-primary)', borderColor: 'var(--border-color)' }} />
                        <Line type="monotone" dataKey="curr" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                </div>
              </div>

            </div>
          ) : (
            <div className="glass-panel" style={{ display: 'flex', justifyContent: 'center', padding: '80px' }}>
              Select a physical asset from the sidebar to inspect its digital twin telemetry.
            </div>
          )}

          {/* Alerts panel */}
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{t.activeAlerts} Log</h3>
            <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {summary && summary.total_alerts > 0 ? (
                summary.machines
                  .flatMap(m => m.detected_issues.map(issue => ({ machine: m.machine_info.name, issue, status: m.status })))
                  .map((alert, idx) => (
                    <div 
                      key={idx} 
                      style={{
                        padding: '10px 16px',
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <span style={{ fontSize: '13px', fontWeight: 500 }}>{alert.issue} ({alert.machine})</span>
                      <span className={`badge badge-${alert.status.toLowerCase()}`}>{alert.status}</span>
                    </div>
                  ))
              ) : (
                <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No active alerts detected. All systems normal.</p>
              )}
            </div>
          </div>

        </section>

      </main>

    </div>
  );
};

export default Dashboard;
