import React, { Suspense, lazy } from 'react';
import { Activity, Cpu, ShieldCheck, ArrowRight, BarChart3, Zap, Sun, Moon } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const MachineAnimation = lazy(() => import('../components/MachineAnimation'));

const Home: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
      
      {/* Top Nav for Theme Toggle */}
      <div style={{ padding: '16px 24px', display: 'flex', justifyContent: 'flex-end' }}>
        <button 
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            padding: '8px',
            borderRadius: 'var(--radius-sm)'
          }}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>

      {/* Hero Section */}
      <header style={{
        padding: '24px 24px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '48px',
        alignItems: 'center',
        maxWidth: '1200px',
        margin: '0 auto',
        width: '100%'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', alignItems: 'flex-start' }}>
          <div className="eyebrow-tag" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={12} style={{ color: 'var(--accent-primary)' }} />
            Enterprise Industry 4.0 — Predictive Edge Analytics
          </div>

          <h1 className="gradient-text" style={{
            fontSize: 'clamp(32px, 5vw, 56px)',
            fontWeight: 800,
            lineHeight: 1.1,
            textAlign: 'left'
          }}>
            AI Digital Twin &amp; Predictive Maintenance
          </h1>

          <p style={{
            fontSize: '18px',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            textAlign: 'left'
          }}>
            Real-time machine health monitoring, fault prediction, and multilingual
            alert generation for small and medium enterprises.
          </p>

          <a
            href="/dashboard"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '14px 32px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--accent-primary)',
              color: '#fff',
              fontWeight: 700,
              fontSize: '15px',
              textDecoration: 'none',
              transition: 'transform 0.15s var(--ease-out), background-color 0.15s var(--ease-out)',
              boxShadow: '0 0 20px var(--accent-glow)'
            }}
            onMouseDown={(e) => { e.currentTarget.style.transform = 'scale(0.97)'; }}
            onMouseUp={(e) => { e.currentTarget.style.transform = 'none'; }}
          >
            Open Dashboard <ArrowRight size={18} />
          </a>
        </div>
        <div style={{ width: '100%', height: '400px', position: 'relative' }}>
          <Suspense fallback={
            <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
              Loading 3D visualization...
            </div>
          }>
            <MachineAnimation />
          </Suspense>
        </div>
      </header>

      {/* Feature Cards */}
      <section style={{
        maxWidth: '1100px',
        width: '100%',
        margin: '0 auto',
        padding: '24px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '24px'
      }}>
        {[
          {
            icon: <Cpu size={24} style={{ color: 'var(--accent-primary)' }} />,
            title: 'Digital Twin Simulation',
            description: 'Virtual replicas of physical machines with real-time sensor data synchronization and state mirroring.'
          },
          {
            icon: <ShieldCheck size={24} style={{ color: 'var(--status-normal)' }} />,
            title: 'Predictive Maintenance',
            description: 'ML-based fault classification and Remaining Useful Life (RUL) estimation to prevent unplanned downtime.'
          },
          {
            icon: <BarChart3 size={24} style={{ color: 'var(--status-warning)' }} />,
            title: 'Real-time Analytics',
            description: 'Live vibration, temperature, and current monitoring with trend visualization and anomaly detection.'
          },
          {
            icon: <Zap size={24} style={{ color: 'var(--status-critical)' }} />,
            title: 'Fault Injection Testing',
            description: 'Simulate bearing wear, misalignment, overheating, and electrical faults to validate the AI pipeline.'
          },
          {
            icon: <Activity size={24} style={{ color: 'oklch(0.62 0.18 290)' }} />,
            title: 'Edge-Ready Architecture',
            description: 'Designed for low-cost deployment on Raspberry Pi and edge gateways for Enterprise factory floors.'
          },
          {
            icon: <ShieldCheck size={24} style={{ color: 'var(--accent-primary)' }} />,
            title: 'Multilingual Alerts',
            description: 'Maintenance alerts in English, Hindi, Telugu, Tamil, and Marathi for diverse factory workforces.'
          }
        ].map((feature, idx) => (
          <div key={idx} className="bezel-outer">
            <div className="bezel-inner" style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '24px' }}>
              {feature.icon}
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>{feature.title}</h3>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {feature.description}
              </p>
            </div>
          </div>
        ))}
      </section>

      {/* Footer */}
      <footer style={{
        marginTop: 'auto',
        padding: '32px 24px',
        textAlign: 'center',
        fontSize: '13px',
        color: 'var(--text-muted)',
        borderTop: '1px solid var(--border-color)'
      }}>
        AI Digital Twin — Enterprise Industry 4.0 Predictive Maintenance System
      </footer>
    </div>
  );
};

export default Home;
