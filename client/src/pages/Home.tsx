import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { VIEW_GROUPS } from '../lib/dashboardViews';
import { RECOGNISED_MODELS } from '../twin/machineModels';

// The flow is what the code does today: adapters in server/adapters, models in ml/ and server/atlas.
const FLOW = [
  { stage: 'Sensors and adapters', detail: 'MQTT sensor feeds from the shop floor, this computer\'s OS telemetry, Android phones over Wi-Fi or USB, server telemetry and NASA C-MAPSS turbofan data.' },
  { stage: 'Models', detail: 'A fault classifier names the fault type. An Attention-LSTM forecasts remaining useful life with an uncertainty range.' },
  { stage: 'Dashboard', detail: 'A 3D model of each machine marks the failing part, with the evidence, an explanation and repair steps.' },
  { stage: 'Alerts', detail: 'When enabled: SMS, voice call or email, in English, Hindi, Telugu, Tamil or Marathi.' },
];

// Running row number across groups, for the ledger numbering.
const GROUP_START = VIEW_GROUPS.map((_, i) => VIEW_GROUPS.slice(0, i).reduce((n, g) => n + g.views.length, 0));

const Home: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const signedIn = document.cookie.includes('auth_status=true');
  const entry = signedIn ? { href: '/dashboard', label: 'Open the dashboard' } : { href: '/login', label: 'Sign in to ATLAS' };

  return (
    <div className="home">
      <header className="home-bar">
        <a href="/" className="home-wordmark" aria-label="ATLAS home">
          ATLAS <span>Predictive maintenance</span>
        </a>
        <nav className="home-bar-actions" aria-label="Site">
          <button
            type="button"
            className="home-icon-btn"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            {theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
          </button>
          <a href={entry.href} className="home-btn home-btn-primary">{signedIn ? 'Dashboard' : 'Sign in'}</a>
        </nav>
      </header>

      <main>
        <section className="home-hero" aria-labelledby="home-title">
          <div className="home-hero-copy">
            <h1 id="home-title">Find the failing part before the machine stops.</h1>
            <p className="home-lede">
              ATLAS reads vibration, temperature and current from your machines, forecasts how long each one has left,
              and marks the faulty part on a 3D model of the machine with the steps to fix it.
            </p>
            <div className="home-actions">
              <a href={entry.href} className="home-btn home-btn-primary">{entry.label}</a>
              {!signedIn && (
                <span className="home-note">Accounts are created by your administrator.</span>
              )}
            </div>
          </div>

        </section>

        <section className="home-section" aria-labelledby="home-views">
          <div className="home-section-head">
            <h2 id="home-views">Where to go in the dashboard</h2>
            <p>Pick what you need to do. Each line opens that view directly after you sign in.</p>
          </div>
          <div className="home-ledger">
            {VIEW_GROUPS.map((group, gi) => (
              <div key={group.task} className="home-ledger-group">
                <h3>{group.task}</h3>
                <ol>
                  {group.views.map((view, vi) => (
                      <li key={view.id}>
                        <a href={`/dashboard?view=${view.id}`} className="home-ledger-row">
                          <span className="home-ledger-num" aria-hidden="true">{String(GROUP_START[gi] + vi + 1).padStart(2, '0')}</span>
                          <span className="home-ledger-name">{view.label}</span>
                          <span className="home-ledger-desc">{view.answers}</span>
                          <span className="home-ledger-open">Open</span>
                        </a>
                      </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </section>

        <section className="home-section home-split" aria-labelledby="home-machines">
          <div>
            <h2 id="home-machines">Machines it recognises</h2>
            <p>
              When a machine is linked, ATLAS picks its 3D model from the machine's registered type or the adapter it
              connects through. Any other machine gets a generic model until you set its type.
            </p>
          </div>
          <ul className="home-machine-list">
            {RECOGNISED_MODELS.map(m => (
              <li key={m.kind}>
                <span>{m.label}</span>
                <span className="home-machine-parts">{m.parts.length} parts</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="home-section" aria-labelledby="home-flow">
          <div className="home-section-head">
            <h2 id="home-flow">How data reaches the dashboard</h2>
          </div>
          <ol className="home-flow">
            {FLOW.map(f => (
              <li key={f.stage}>
                <h3>{f.stage}</h3>
                <p>{f.detail}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="home-footer">
        <span>ATLAS predictive maintenance and digital twin</span>
        <nav aria-label="Footer">
          <a href="/login">Sign in</a>
          <a href="/dashboard">Dashboard</a>
        </nav>
      </footer>
    </div>
  );
};

export default Home;
