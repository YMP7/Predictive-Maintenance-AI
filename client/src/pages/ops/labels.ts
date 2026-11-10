/** C-MAPSS and the device domains report status words; map them onto alarm priorities (normal has no colour). */
export const STATUS_TONE: Record<string, 'high' | 'medium' | undefined> = { Critical: 'high', Degrading: 'medium', Warning: 'medium' };

export const DOMAIN_LABEL: Record<string, string> = {
  cmapss: 'Turbofan (C-MAPSS)',
  laptop: 'Laptop',
  mobile: 'Phone',
  server: 'Server',
  modbus: 'Motor and pump (Modbus)',
};
