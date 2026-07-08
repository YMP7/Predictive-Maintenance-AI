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
      if (response.access_token) {
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('role', response.role);
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
            borderRadius: '8px'
          }}
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>

      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '24px' }}>
        <form className="glass-panel" onSubmit={handleLogin} style={{
        display: 'flex', flexDirection: 'column', gap: '16px', 
        width: '100%', maxWidth: '400px', padding: '32px'
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: '16px' }}>Digital Twin Login</h2>
        
        {error && <div style={{ color: 'var(--status-critical)', fontSize: '14px', textAlign: 'center' }}>{error}</div>}
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label>Username</label>
          <input 
            type="text" 
            value={username} 
            onChange={(e) => setUsername(e.target.value)}
            style={{
              padding: '10px', borderRadius: '6px', 
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)', color: 'var(--text-primary)'
            }}
            required 
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label>Password</label>
          <input 
            type="password" 
            value={password} 
            onChange={(e) => setPassword(e.target.value)}
            style={{
              padding: '10px', borderRadius: '6px', 
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)', color: 'var(--text-primary)'
            }}
            required 
          />
        </div>

        <button type="submit" style={{
          marginTop: '16px', padding: '12px', borderRadius: '6px',
          background: 'var(--accent-primary)', color: 'white',
          fontWeight: 600, border: 'none', cursor: 'pointer'
        }}>
          Login
        </button>

        <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '16px' }}>
          Demo Account: demo_viewer/ix_rPBrwjyX3cnOPHSZ6gg (Read-only viewer)
        </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
