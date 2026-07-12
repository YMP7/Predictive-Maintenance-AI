import React, { useState } from 'react';
import { apiFetch } from '../lib/api';
import { useTheme } from '../contexts/ThemeContext';
import { Sun, Moon } from 'lucide-react';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { theme, toggleTheme } = useTheme();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiFetch<any>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
      });
      if (response && response.role) {
        window.location.href = '/dashboard';
      }
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      minHeight: '100vh', background: 'var(--bg-primary)'
    }}>
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

      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '24px' }}>
        <form onSubmit={handleLogin} className="bezel-outer" style={{ width: '100%', maxWidth: '400px', borderColor: error ? 'var(--status-critical)' : 'var(--border-color)' }}>
          <div className="bezel-inner" style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '32px' }}>
            <h2 style={{ textAlign: 'center', marginBottom: '16px', fontSize: '20px', fontWeight: 700 }}>Digital Twin Login</h2>
            
            {error && <div style={{ color: 'var(--status-critical)', fontSize: '13px', textAlign: 'center', fontWeight: 500 }}>{error}</div>}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>Username</label>
              <input 
                type="text" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)}
                style={{ borderColor: error ? 'var(--status-critical)' : 'var(--border-color)' }}
                required 
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>Password</label>
              <input 
                type="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)}
                style={{ borderColor: error ? 'var(--status-critical)' : 'var(--border-color)' }}
                required 
              />
            </div>

            <button type="submit" className="primary" style={{ marginTop: '16px', padding: '12px', fontWeight: 600 }}>
              Login
            </button>

            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '16px', lineHeight: 1.4 }}>
              Demo Account: <code style={{ color: 'var(--text-secondary)' }}>demo_viewer / demo_viewer_public_pw_123</code>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
