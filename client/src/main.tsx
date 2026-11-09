import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// Self-hosted faces: Inter for UI, JetBrains Mono for every number.
import '@fontsource-variable/inter/index.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/600.css';
import './design/tokens.css';
import './design/base.css';
import './design/components.css';
import './design/pages.css';

import App from './App.tsx';
import { initKioskFromUrl } from './app/kioskState';

initKioskFromUrl();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
