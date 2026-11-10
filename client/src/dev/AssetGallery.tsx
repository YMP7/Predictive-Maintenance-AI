// Dev only: the real Asset View page on synthetic TwinFrames, for screenshots, the fps and draw-call
// probe, the context-leak check and the WebGL-off test without a backend session. The frames were
// built by server/asset_view.py build_frame() from the real asset profiles with seeded random values
// (every channel SIMULATED); the attribution is random too.
import { Link, useParams } from 'react-router';

import { Page } from '../design/shell';
import AssetPage from '../pages/asset/AssetPage';
import { AssetSourceContext, sharesFromExplanation, type AssetSource } from '../pages/asset/source';
import type { TwinFrame } from '../pages/asset/types';
import fixtures from './assetFixtures.json';

type Fixture = TwinFrame & { _why: Record<string, number> | null };
const FRAMES = Object.values(fixtures as unknown as Record<string, Fixture>);

const source: AssetSource = {
  async frame(domain, machineId) {
    const f = FRAMES.find(x => x.domain === domain && x.machine_id === machineId);
    if (!f) throw new Error('API error 404: no fixture');
    return { ...f, ts: new Date().toISOString() };
  },
  async why(frame) {
    const f = FRAMES.find(x => x.domain === frame.domain)!;
    return sharesFromExplanation(frame, {
      primary_justification: 'Synthetic explanation for the dev gallery: no model ran.',
      citations: [],
      sensor_attributions: Object.entries(f._why ?? {}).map(([sensor_name, magnitude]) => ({ sensor_name, magnitude })),
      attribution_unavailable_reason: f._why ? null : 'Feature attribution exists only for the 14-feature C-MAPSS layout.',
    });
  },
};

export default function AssetGallery() {
  const { domain } = useParams();
  if (domain) {
    return (
      <AssetSourceContext.Provider value={source}>
        <AssetPage />
      </AssetSourceContext.Provider>
    );
  }
  return (
    <Page title="Asset View gallery" purpose="Dev only: the five machines on synthetic frames.">
      <ul className="ax-asset__index ax-panel">
        {FRAMES.map(f => (
          <li key={f.kind}>
            <Link to={`/dev/assets/${f.domain}/${f.machine_id}`}>{f.label}</Link>
            <span className="num">{f.kind}</span>
            <span />
          </li>
        ))}
      </ul>
    </Page>
  );
}
