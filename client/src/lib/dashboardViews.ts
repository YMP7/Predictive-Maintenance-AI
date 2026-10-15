// Dashboard views that can be opened directly with /dashboard?view=<id>.
// Ids match the tabs in components/atlas/AtlasHeader.tsx.

export interface DashboardView {
  id: string;
  label: string;
  answers: string;
}

export interface ViewGroup {
  task: string;
  views: DashboardView[];
}

export const VIEW_GROUPS: ViewGroup[] = [
  {
    task: 'Check a machine',
    views: [
      { id: 'legacy_iot', label: 'Shop Floor', answers: 'Factory machines that report over MQTT: live vibration, temperature and current, the 3D fault view with repair steps, fault tests and the maintenance chat.' },
      { id: 'monitoring', label: 'Connected Devices', answers: 'Live sensor streams from each connected unit (turbofan fleet, this computer, phones, server), with a 3D model of the unit and any part over its limit.' },
    ],
  },
  {
    task: 'Understand the prediction',
    views: [
      { id: 'cognition', label: 'Cognition & DNA', answers: 'Remaining useful life as a range (conservative, expected, optimistic) and the past cases the model recalls.' },
      { id: 'explainability', label: 'Explainability', answers: 'Why the model reached its prediction: grounding confidence, cited past episodes and the sensors behind it.' },
    ],
  },
  {
    task: 'Decide what to do',
    views: [
      { id: 'decision', label: 'Decision Graph', answers: 'Failure probability against each maintenance action and its lead time, to pick when to intervene.' },
    ],
  },
  {
    task: 'Validate the models',
    views: [
      { id: 'transfer', label: 'Transfer Study', answers: 'How well a model trained on one machine type holds up on another.' },
      { id: 'ablations', label: 'Ablation Suite', answers: 'Simple thresholds compared with the full pipeline on missed failures.' },
      { id: 'system', label: 'Diagnostics', answers: 'Health of the platform itself: memory, CPU load, latency and throughput.' },
    ],
  },
  {
    task: 'Administer (admins only)',
    views: [
      { id: 'devices', label: 'Manage Devices', answers: 'Add, edit or remove shop-floor machines, and set their warning and critical limits.' },
    ],
  },
];

export const DASHBOARD_VIEWS = VIEW_GROUPS.flatMap(g => g.views.map(v => v.id));
