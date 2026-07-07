import React from 'react';
import { AlertTriangle } from 'lucide-react';

const NotFound: React.FC = () => {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '24px',
      textAlign: 'center',
      padding: '24px'
    }}>
      <AlertTriangle size={48} style={{ color: 'var(--status-warning)' }} />
      <h1 className="gradient-text" style={{ fontSize: '48px', fontWeight: 800 }}>404</h1>
      <p style={{ fontSize: '18px', color: 'var(--text-secondary)', maxWidth: '400px' }}>
        The page you are looking for does not exist or has been moved.
      </p>
      <a
        href="/"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '12px 24px',
          borderRadius: '10px',
          background: 'var(--accent-primary)',
          color: '#fff',
          fontWeight: 600,
          fontSize: '14px',
          textDecoration: 'none',
          boxShadow: '0 0 15px var(--accent-glow)'
        }}
      >
        ← Back to Home
      </a>
    </div>
  );
};

export default NotFound;
