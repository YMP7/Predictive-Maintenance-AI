# 3D Asset View: how it is built and why (P3)

## What it is
One page per machine (`/assets/:domain/:machineId`). It shows the machine as a 3D model you can turn, zoom, explode and cut open. Each part carries the live load of the sensors bound to it. "Show why" lights the parts the RUL model blamed. A tour walks through the monitored parts. The same parts and states render as a 2-D schematic when WebGL is off.

Five machines, one per asset kind:

| Kind | Domain | Reference proportions | Parts | Moving parts driven by |
|---|---|---|---|---|
| `turbofan` | `cmapss` | High-bypass two-spool turbofan, CFM56 class (fan tip radius 0.86 m), the engine type C-MAPSS simulates | fan, LPC, HPC, combustor, HPT, LPT, nozzle | fan speed `s8` (Nf); high spool at 1.6x |
| `laptop` | `laptop` | 14-inch laptop, 313 x 221 x 16 mm | processor, heat pipe and fan, memory, SSD, battery, Wi-Fi, display | nothing (no fan speed is measured) |
| `phone` | `mobile` | Android phone, 147 x 71 x 8 mm | SoC, battery, motion sensors, light and proximity, magnetometer, display | nothing |
| `server` | `server` | 2U rack server, 440 x 87 x 700 mm | processors, DIMMs, drive bays, NIC, GPU, fan wall, PSUs | nothing |
| `motor_pump` | `modbus` | IEC 132-frame TEFC motor (shaft height 132 mm) driving an end-suction pump | cooling fan, both bearings, motor body, terminal box, coupling, pump and impeller | shaft speed `speed_rpm` |

Nothing turns unless a measured speed channel drives it. Displayed rotation is slowed (0.08 + 0.5 x normalised speed, in turns per second) and labelled as such.

## Data path (TwinFrame)
```
adapter / ingest ──> domain snapshot or ConfigurableAdapter reading
                       │
server/adapters/asset_profiles.py   kind, parts, channel → part, direction, unit   (Adapter Layer)
                       │
server/asset_view.py  GET /api/assets                         every showable asset
                      GET /api/assets/{id}/frame?domain=      TwinFrame
                      GET /api/atlas/domain/{d}/profile       parts and bindings
                       │
client/src/pages/asset/AssetPage.tsx   polls the frame every 2 s
client/src/teardown/view.ts            draws it (geometry by kind only)
```
The client never branches on a domain name. Domain knowledge (which sensor belongs to which part, which way it moves under load) lives in `server/adapters/asset_profiles.py`. A machine onboarded with a sensor profile takes each channel's `part` from that profile, which overrides the default binding.

**Part load** is a stated heuristic. For each bound channel the load is its normalised value (1 - value for channels that fall under load). Neutral channels (a speed, a pressure, acceleration axes) are shown but not ranked. A part's load is its highest channel load: 0.75 or more is elevated (ISA-18.2 medium colour), 0.9 or more is high. The page says so under the parts list.

**Quality** travels per channel: SIMULATED from simulated adapters, STALE after 30 s without a reading, MISSING when no value arrived. Values come from the adapter's raw engineering unit when it reports one (C-MAPSS °R, psia, rpm; Modbus °C, mm/s, A), otherwise as a share of the channel's range.

## "Show why"
It fetches the machine's 30-reading window, posts it to the existing `/api/explain` and sums the occlusion attribution magnitudes per part through the frame's bindings. Parts glow in the interaction blue in proportion to their share; load tints are switched off meanwhile, so one colour means one thing. Occlusion attribution exists only for the 14-feature C-MAPSS layout; other machines show the engine's own `attribution_unavailable_reason`, the justification and the AMKB citation count. Explanations need an operator or admin (viewers see why it is unavailable). No model code changed.

## Rendering: the teardown kit, ported (ADR-002, ADR-014)
`client/src/teardown/` holds the port: `kit/util.ts` and `kit/warm.ts` (from the kit, MIT, credited in each file), `parts.ts` (lathed shells, rounded boxes, instanced blade rows, ribs, rotors), one file per machine under `machines/`, and `view.ts` (stage, orbit, picking, explode, cutaway, tint, tour, tiers, dispose). React mounts it imperatively in `pages/asset/AssetStage.tsx`, on a fresh canvas per mount.

Kept from the kit: the pale studio (PMREM soft boxes, one sun with a soft shadow on an invisible floor), parallel shader warm-up before the first frame, quality tiers, matte metals (roughness ≥ 0.45), polygon offset on the shadow catcher, and a tour that hands control to the visitor.

Left out, with reasons:
- **Post-processing (bloom, GTAO).** Bloom washes detail out of a monitoring view. GTAO on a cut model needs matched clipping planes on its normal pass (a trap the kit documents) and costs the most on integrated GPUs. Plain MSAA rendering keeps every machine at 60 fps on Intel UHD.
- **The fixed 1600 x 900 HUD, director and capture runtime.** The React side panel and the design system replace the HUD; the films are recorded from the live page instead.
- **The score.** Product pages stay silent.

## Interaction
| Control | Effect |
|---|---|
| Drag, wheel | Orbit and zoom (OrbitControls, floor-clamped) |
| Click a part, or a row in the parts list | Select: camera eases to it, a callout shows the reading that sets its load, other parts dim to 45% and covers to 20% |
| Explode | Parts and covers slide along their `apart` vectors |
| Cutaway | Covers (nacelle, deck, lid, back glass, motor frame, volute) are clipped in half |
| Isolate | Everything but the selected part drops to 12% and cannot be picked |
| Show why | Attribution glow (above) |
| Tour | Steps through the monitored parts every 6 s with a slow orbit; any input stops it. In kiosk mode it starts on its own and resumes after 25 s of quiet |
| Reset view | Default camera, nothing selected |

The parts list offers every selection by keyboard; the canvas is labelled as an image that points to it. With reduced motion, easing, rotation and the tour orbit are off and the camera jumps.

## Verification (2026-11-08, Intel UHD Graphics, Chrome, 1440 x 900)
| Check | Result |
|---|---|
| fps and draw calls, per machine at full quality | turbofan 60 fps / 100-118 calls; laptop 60 / 51; phone 54-60 / 36; server 60 / 64; pump 60 / 46-47 |
| Context leak: 20 in-app navigations across the five machines | 20 views created, never more than 1 live, 0 after leaving, a new WebGL context still created, heap 37 MB before and after, no console errors |
| WebGL off (`?no3d=1`) | No canvas; 2-D schematic with all parts, states and selection, and the reason stated |
| Kiosk at 1920 x 1080 | Tour starts on its own, explodes the model and calls out each monitored part |
| Bundle | three.js and the machines load only with the asset page (lazy chunk 152 KB gz); initial JS 99 KB gz |

Frame-by-frame review: `docs/media/films/p3-asset-tour-sheet.png` (one frame every 6 s of `p3-asset-tour.mp4`). Found and fixed in review: the turbofan camera faced the exhaust; tall machines were framed too close; selection was hidden behind covers and the laptop lid; the phone's display exploded into the camera; near-white metal washed out on the light studio; a reused canvas kept a lost context under React's dev double mount; disposing during shader warm-up threw; page state carried over between machines; the kiosk tour never started because the page reset the idle clock.

The fps figures came from an unthrottled Chrome window. The in-app browser pane caps a hidden pane at 30 fps, so the automatic tier step-down triggers only below 25 fps.

## Limits
- The machines are built from published proportions, not CAD; they are explanatory, not dimensional.
- Part load is a heuristic on normalised channels, labelled as such. It is not a diagnosis.
- Attribution glow exists only for C-MAPSS (§5 Q3 of the plan).
- The screenshots and films use the dev gallery (`/dev/assets`, dev build only) on synthetic frames built by the server's own `build_frame()` from seeded values, every channel badged SIMULATED. The live page reads the same frame shape from the API; a signed-in run against a P3 backend was not recorded.
- The Modbus motor-pump shows data only once `scripts/modbus_bridge.py` (or a real device) pushes readings for a `modbus` sensor profile; its RUL model is trained on simulated run-to-failure data (`server/atlas/train_pump_rul.py`).
