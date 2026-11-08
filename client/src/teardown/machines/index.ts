import type { Machine } from '../parts';
import { buildLaptop } from './laptop';
import { buildMotorPump } from './motorPump';
import { buildPhone } from './phone';
import { buildServer } from './server';
import { buildTurbofan } from './turbofan';

/** Geometry by asset kind (from the TwinFrame). The server decides the kind; the client only draws it. */
export const BUILDERS: Record<string, () => Machine> = {
  turbofan: buildTurbofan,
  laptop: buildLaptop,
  phone: buildPhone,
  server: buildServer,
  motor_pump: buildMotorPump,
};
