# MSME Deployment, Integration and Adoption: Enhancements for ATLAS

Scope: what it takes to move ATLAS (FastAPI + React 3D twin; C-MAPSS, laptop, server, mobile and simulated Modbus adapters; RUL, anomaly, decision support, LLM chat; Mosquitto MQTT in `scripts/` and `server/mqtt_client.py`) from research prototype into real Indian MSME factory use. This extends `LANDSCAPE_REPORT_2026-11.md` (which already covered TSFMs, conformal RUL, AAS/BaSyx mention, the Atlas CMMS name collision, ThingsBoard gateway, EU AI Act, and vendor-sourced Indian MSME cost numbers). Those items are not repeated here except where new evidence changes them.

Relevant existing repo files the ideas plug into: `server/adapters/base_adapter.py`, `server/adapters/modbus_adapter.py`, `scripts/modbus_bridge.py`, `server/mqtt_client.py`, `scripts/generate_mqtt_passwords.py`, `server/alert_handler.py`, `server/auth.py`, `docs/ADAPTER_SDK_SPEC.md`, `tests/test_notifications.py`.

Effort key: S = 1–3 days, M = 1–2 weeks, L = 3+ weeks.

## Q1. Low-cost sensing, retrofit and edge inference

### Takeaway
A peer-reviewed 2025 design (ESP32 + MEMS accelerometer + mic, on-device anomaly detection) and several ESP32 + ADXL345 studies show that a ~sub-₹5k retrofit node is technically credible for small rotating machines; the ADXL345 is adequate for low-frequency broadband severity (ISO 10816/20816 style RMS velocity), while bearing-defect frequencies need a lower-noise part such as the ADXL355. ATLAS's missing piece is a real-hardware adapter plus an edge-side anomaly mode, not more models.

### Cited Findings
- Kolok et al., "Low-Cost IoT-Based Predictive Maintenance Using Vibration" (Sensors 2025, 25(21):6610): ESP32 node with MEMS accelerometer and microphone targeting small rotating equipment (fans, low-power motors) where commercial systems are too costly; performs on-device anomaly detection — [PMC12609400](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12609400/)
- KMITL induction-motor system: ESP32 + ADXL345 computes vibration velocity, sends over Wi-Fi to a dashboard, classifies using ISO 10816 severity levels — [KMITL repository](https://dspace.kmitl.ac.th/items/28d053d4-e4ed-4231-98bf-f47b02acc067)
- Alvares & da Silva: ADXL345 + ESP32 with FFT tracked vibration accurately in misalignment tests; framed as economical PdM for SMEs — [Pamator journal PDF](https://journal.trunojoyo.ac.id/pamator/article/download/32854/11735); [conference PDF](https://static.even3.com/anais/1236403.pdf)
- Practitioner guidance recommends ADXL355 over ADXL345 for noise performance (not peer-reviewed) — [Zbotic guide](https://zbotic.in/industrial-vibration-sensor-predictive-maintenance-guide/)
- Edge Impulse's official tutorial builds a K-means anomaly model on spectral features of motor power data only (no extra sensor) and fits on a Raspberry Pi Pico-class MCU — [Edge Impulse docs](https://docs.edgeimpulse.com/experts/brushless-dc-motor-anomaly-detection)
- ESP32 TinyML community projects (MPU-6050 at 100 Hz, FFT features) pair a supervised classifier for known faults with a K-means anomaly model for unknown faults; self-reported >85–90% accuracy, hobbyist quality — [ElectronicWings VibroSense](https://www.electronicwings.com/users/JEEVITHT/projects/6655/vibrosense-real-time-machine-anomaly-detection-using-tinyml-on-esp32); [ElectronicWings fault project](https://www.electronicwings.com/users/RajneeshKumar/projects/6672/predicting-machinery-fault-by-analyzing-vibrations)
- Prior ATLAS report: retrofit sensors ~₹1–2 lakh per 20–30 machines (vendor estimate) — [cionlabs](https://cionlabs.com/brownfield-iot-retrofitting-legacy-indian-machinery-with-smart-wireless-intelligence/)
- Systematic review (search window 2014–2024, 46 articles): barriers in data-scarce PdM are legacy equipment, sensor deployment cost, and rarity of critical failures; low-cost sensors and federated learning named as enablers (publication date metadata inconsistent; verify) — [IIETA JESA review](https://www.iieta.org/journals/jesa/paper/10.18280/jesa.590611)

### Inferences (enhancement ideas)
1. **ESP32 vibration node firmware + `Esp32VibrationAdapter`** (M). What: open firmware (ESP32 + ADXL345 default, ADXL355 option, optional SCT-013 CT clamp and DS18B20 temp) that computes RMS velocity (10–1000 Hz band), peak, crest factor, kurtosis and a coarse FFT on-device and publishes JSON over MQTT. Why: gives ATLAS its first real non-simulated industrial domain; papers above show feasibility. Plug-in: new adapter subclassing `base_adapter.py`, subscribing via existing `mqtt_client.py`; follows `docs/ADAPTER_SDK_SPEC.md` and gets a conformance test in `tests/test_adapter_conformance.py`. Publish a BOM (cost in ₹) and wiring diagram in docs.
2. **ISO 20816-3 severity zoning as a deterministic baseline** (S). See Q2; gives the "no-ML, no-history" day-one value that matches the KMITL design.
3. **Anomaly-first / baseline-learning mode on the edge** (M). What: per-machine K-means or isolation-forest on features learned over a commissioning window (e.g., first 3–7 days), RUL only shown once enough history exists. Why: MSME machines have no run-to-failure labels (review above); Edge Impulse and community projects show K-means fits on MCUs. Plug-in: the landscape report's "anomaly-first mode" (#8) can run either server-side or exported to the ESP32 as a fixed centroid table.
4. **Offline-first edge gateway profile** (M). What: a Raspberry Pi 4/5 (or old PC) "ATLAS Edge" docker-compose: Mosquitto + ATLAS backend + SQLite/Timescale + store-and-forward to optional cloud. Why: intermittent connectivity is the norm on Indian shop floors (inference; no source found quantifying it). Plug-in: reuse existing backend; add a compose profile and MQTT bridge config with local persistence (`persistence true`, queued QoS1).
5. **CT-clamp "machine on/off + load" adapter** (S). What: SCT-013 current transformer on ESP32 ADC giving run-hours and load proxy. Why: the cheapest signal for utilization and for power-signature anomaly (Edge Impulse BLDC tutorial uses power data only). Plug-in: same adapter as #1 with a `current_rms` feature; also feeds OEE-lite metrics MSMEs ask for.
6. **Commissioning wizard in the UI** (M). What: step-by-step "add a machine" flow: pick machine class (ISO 20816 group, rigid/flexible), mount point photo, baseline capture timer. Why: adoption barriers are skills, not algorithms (Q5). Plug-in: React UI + an asset-profile record in `asset_profiles.py`.

### Gaps
- No peer-reviewed per-node cost in ₹ was extracted (Kolok paper cost table not read in full).
- No source found quantifying factory connectivity/uptime in Indian MSME clusters.
- Jetson-class edge was not researched; for vibration features it is likely overkill versus ESP32/RPi (inference only).

## Q2. Industrial interoperability standards: what to adopt first

### Takeaway
For a small project the sensible order is: (1) ISO 20816-3 severity zones as interpretable thresholds, (2) MQTT with Sparkplug B (now ISO/IEC 20237:2023) for device-to-ATLAS payloads, (3) an OPC UA client only for machines that already expose it, (4) AAS export using the new IDTA PredictiveMaintenance submodel (IDTA 02048, June 2025) for standards credibility. ISO 13374 / OSA-CBM, ISO 17359 and ISA-95 are better used as documentation mappings than implemented.

### Cited Findings
- Sparkplug 3.0 was published as ISO/IEC 20237:2023 (Oct 2023); Eclipse says the two are equivalent and conformance is checked with the Sparkplug TCK — [ISO catalogue](https://www.iso.org/standard/86204.html); [Eclipse newsroom](https://newsroom.eclipse.org/node/39754)
- Sparkplug B adds topic namespace, state management (birth/death certificates) and a typed payload on top of plain MQTT, fixing the "Wild West" payload problem — [Eclipse Sparkplug article](https://sparkplug.eclipse.org/resources/articles/2022-07-12-the-key-differences-between-opc-ua-and-mqtt-sparkplug/)
- OPC UA spec has 14+ parts with hundreds of pages each; one source says access cost is a barrier for SMEs (single blog, treat cautiously); vendor comparisons mostly come from MQTT vendors (bias) — [EMQX comparison](https://www.emqx.com/en/blog/a-comparison-of-iiot-protocols-mqtt-sparkplug-vs-opc-ua)
- Common pattern: gateway reads OPC UA locally and republishes to a Unified Namespace over MQTT/Sparkplug; small single-line plants may prefer simpler architectures first — [Proxus](https://proxus.io/blog/mqtt-vs-opc-ua-in-modern-iiot/)
- IDTA 02048 "Predictive Maintenance" AAS submodel template v1.0 (June 2025) standardizes metadata for PdM in automated production lines — [IDTA 02048 PDF](https://industrialdigitaltwin.org/wp-content/uploads/2025/06/IDTA-02048_Submodel_PredictiveMaintenance.pdf)
- IDTA 02029-1 "Sensor 4.0 MeasurementValue" (Dec 2025) gives a generic structure for sensor measurement values — [IDTA 02029-1 PDF](https://industrialdigitaltwin.org/en/wp-content/uploads/sites/2/2025/12/IDTA-02029-1_Sensor4.0_MeasurementValue.pdf)
- IDTA 02019 Plant Asset Management (Nov 2024) notes condition-monitoring data is better handled by a separate submodel — [IDTA 02019 PDF](https://industrialdigitaltwin.org/wp-content/uploads/2024/11/IDTA-02019-1-0_Submodel_PlantAssetManagement.pdf)
- IDTA 02058 "AIDataset" submodel (Feb 2025) exists for describing AI training datasets — [IDTA 02058 PDF](https://industrialdigitaltwin.org/wp-content/uploads/2025/02/IDTA-02058-1-0_Submodel_AIDataset.pdf)
- ISO 20816-3 zone boundaries (broadband RMS velocity, 10–1000 Hz, mm/s, rigid supports): Group 1 (>300 kW) A/B 2.3, B/C 4.5, C/D 7.1; Group 2 (15–300 kW) A/B 1.4, B/C 2.8, C/D 4.5; flexible supports higher (G1: 3.5/7.1/11.0; G2: 2.3/4.5/7.1). Vendor blogs, not the ISO text — [Fabrico](https://www.fabrico.io/blog/iso-20816-vibration-severity-zones/); [Sensemore calculator](https://sensemore.io/tools/iso-20816-vibration-severity-calculator/)
- Suggested alarm = baseline + 25% of Zone B upper limit, not above 1.25× Zone B upper; trip ≤ 1.25× Zone C upper (secondary sources) — [Fabrico ISO 10816-3](https://www.fabrico.io/blog/iso-10816-3-vibration-severity/)

### Inferences (enhancement ideas)
7. **ISO 20816 severity module** (S). Function `severity_zone(rms_mm_s, group, support)` returning A–D plus alarm/trip derived from the machine's own baseline. Shown as a colour band on the 3D twin and used as a rule-based feature beside the ML anomaly score. Cite as "per ISO 20816-3, values via secondary sources; verify against standard". Small unit test with the table above.
8. **Sparkplug B topic/payload support in `mqtt_client.py`** (M). Use `spBv1.0/<group>/<DDATA|NDATA|NBIRTH|NDEATH>/<edge_node>/<device>` and the protobuf payload (Eclipse Tahu Python library). Birth/death certificates give free "sensor offline" detection — a top MSME pain point. Keep plain-JSON MQTT as a fallback for hobby firmware.
9. **OPC UA read-only client adapter** (M). `asyncua` (Python) polling configured NodeIds into the existing adapter interface; only for newer CNC/PLCs that expose OPC UA. Lower priority than Sparkplug for MSMEs whose machines are mostly legacy (inference).
10. **Real Modbus RTU/TCP path** (S–M). `scripts/modbus_bridge.py` already exists; add a documented RS-485-to-USB (or TCP gateway) recipe for energy meters and VFDs, which are the most common Modbus devices already installed in MSME panels (inference; no source fetched).
11. **AAS export endpoint** (M). `/assets/{id}/aas` producing AAS JSON with Nameplate, TechnicalData (IDTA 02003), Sensor MeasurementValue (02029) and PredictiveMaintenance (02048) submodels; validate by loading into Eclipse BaSyx. Upgrades landscape-report item #11 with the specific, now-published templates.
12. **ISO 13374 / OSA-CBM layer mapping in docs** (S). One table mapping ATLAS pipeline stages to the six OSA-CBM blocks (data acquisition, manipulation, state detection, health assessment, prognostics, advisory generation). Documentation-only; good for paper reviewers. (Block names from background knowledge; see Gaps.)

### Gaps
- ISO 13374, ISO 17359 and ISA-95 primary sources were not retrieved in this pass; the six-block OSA-CBM naming above is from background knowledge and must be verified before citing.
- No standalone IDTA "Condition Monitoring" submodel template was found; check the IDTA template registry.
- OPC UA licensing claim (cost barrier) rests on one blog; OPC Foundation specs are in practice readable after free registration (not verified here).

## Q3. Integration with maintenance workflows (CMMS, alerts, language)

### Takeaway
A prediction only creates value when it becomes a work order that a technician sees on WhatsApp in a language they read. The cheapest high-impact path is: WhatsApp utility-template alerts (≈₹0.115–0.145 per message in India), one CMMS connector (Atlas CMMS or ERPNext, both self-hostable, REST APIs), and Hindi/regional UI via Bhashini or AI4Bharat models.

### Cited Findings
- Since 1 July 2025 Meta bills WhatsApp Business Platform per delivered template message by category and country — [Meta developer docs](https://developers.facebook.com/docs/whatsapp/pricing)
- India utility template ≈ ₹0.115/message ex-GST; marketing rose to ₹0.8631 on 1 Jan 2026 — [Montymobile](https://montymobile.com/blogs/whatsapp-business-api-pricing-in-india-inr-rates-gst-and-the-2026-currency-migration-deadline); a BSP quotes ₹0.145 utility (likely with markup) and says in-window utility messages are now charged — [AiSensy](https://m.aisensy.com/blog/whatsapp-per-message-pricing-update-effective-january-1-2026/); other sources put that change at 1 Oct 2026 — [SleekFlow](https://help.sleekflow.io/en_US/pricing) (conflict noted)
- Atlas CMMS: open-source (GPLv3 per project; one directory says AGPL-3.0), Docker self-hosting (API 8080, UI 3000, MinIO 9000), REST API exists, work orders with assignment, priority, time logs, history — [GitHub Grashjs/cmms](https://github.com/Grashjs/cmms); [SourceForge listing](https://sourceforge.net/software/product/Atlas-CMMS)
- Bhashini provides translation, ASR and TTS across 22 scheduled languages with free registration-based API credentials for low volume (secondary sources); speech translation may cover only 14 languages — [Apolitical case study](https://apolitical.co/en/navigator/case-studies/india-using-ai-to-make-government-services-available-in-22-languages); [Analytics India Magazine](https://analyticsindiamag.com/exclusive-bhashinis-amitabh-nag-on-breaking-language-barriers-in-india)
- AI4Bharat IndicTrans2 is an open-source translation model usable self-hosted — [Analytics India Magazine](https://analyticsindiamag.com/it-services/bhashini-will-truly-democratise-ai-in-india)
- Prior ATLAS report flagged the "ATLAS" name collision with Atlas CMMS — integrating with it makes the collision more visible (see landscape report §7 #1)

### Inferences (enhancement ideas)
13. **WhatsApp alert channel in `alert_handler.py`** (S–M). Pre-approved utility templates ("Machine {{1}} vibration Zone C, est. {{2}} days to action, reply 1=Ack 2=Create WO"). Webhook receives replies → acknowledge alert / create work order. Cost at ~₹0.12/msg: 20 machines × 2 alerts/day ≈ ₹150/month. Keep SMS (e.g., via an Indian DLT-registered gateway) and email as fallbacks; `tests/test_notifications.py` already exists to extend.
14. **Alert hygiene: escalation and suppression** (S). De-dup, hysteresis (zone must persist N minutes), quiet hours, escalate supervisor → owner if unacknowledged. Alert fatigue is a classic PdM failure mode (inference); cheap to implement.
15. **CMMS connector interface + one implementation** (M). `WorkOrderSink` with `create(asset, priority, description, evidence_url)`; first target ERPNext Maintenance (very common in Indian SMEs using Frappe/ERPNext; inference) or Atlas CMMS. Built-in "mini-CMMS" (work order list with status, technician, closure notes) for MSMEs with no CMMS at all. Closure notes double as failure labels for retraining — closing the feedback loop the ML needs.
16. **Failure/maintenance logbook as label source** (S). Every closed work order records failure mode (simple pick list: bearing, misalignment, looseness, lubrication, electrical). Feeds learning module retraining already in the repo history (commit `232e9a6`).
17. **Hindi + one regional language UI** (M). react-i18next string extraction; machine translation via Bhashini/IndicTrans2 then human review; LLM agent answers in the user's language (prompt flag). Voice notes in WhatsApp → ASR → agent query is a later step (L).
18. **Shift report PDF/WhatsApp digest** (S). Daily one-page summary per plant: machines by zone, open WOs, run-hours. Matches how owners consume information (inference).

### Gaps
- Atlas CMMS API endpoints and auth scheme were not documented in search results; read the repo before committing.
- ERPNext Maintenance module API was not researched in this pass.
- No survey data found on WhatsApp usage for maintenance in Indian factories specifically (widely assumed, not cited).

## Q4. Security, deployment model, privacy and MLOps

### Takeaway
Target IEC 62443 Security Level 2 thinking (asset inventory, zones/conduits, least privilege, MFA), ship on-prem/edge-first with optional cloud, and treat DPDP as relevant only for personal data (operator names, phone numbers for WhatsApp, chat logs) — the DPDP Rules 2025 were notified 13 Nov 2025 with full obligations by ~13 May 2027.

### Cited Findings
- SL2 is described as the practical target for most manufacturers (defends against casual/opportunistic attackers); first steps: asset inventory, zones and conduits, IT/DMZ/OT separation, least privilege + MFA, removable-media controls, OT-specific incident response (vendor/blog sources) — [FlowFuse](https://flowfuse.com/blog/2026/05/nis2-iec-62443-manufacturers); [Security Boulevard SME guide](https://securityboulevard.com/2026/06/zone-and-conduit-modelling-under-iec-62443-a-practical-guide-for-uk-smes/)
- NIST MEP publishes a free "where to start" cybersecurity guide for small and medium manufacturers — [NIST MEP](https://nist.gov/mep/cybersecurity-resources-manufacturers/where-start)
- DPDP Rules 2025 notified 13 Nov 2025 (G.S.R. 846(E)); Data Protection Board constituted immediately; consent manager registration from Nov 2026; core obligations at 18 months (13 or 12 May 2027 — sources differ) — [AZB & Partners](https://www.azbpartners.com/bank/update-indias-digital-personal-data-protection-framework-comes-into-effect/); [Legal500/Saga Legal](https://www.legal500.com/firms/237811-saga-legal/c-india/news-and-developments/the-privacy-timer-starts-now-analysing-the-dpdp-rules-and-its-18-month-countdown)
- Prior report: EU Cyber Resilience Act incident reporting starts Sept 2026 (relevant only if ATLAS is sold as a product in the EU) — see `LANDSCAPE_REPORT_2026-11.md` §6

### Inferences (enhancement ideas)
19. **Read-only OT posture by default** (S). Adapters never write to PLC/Modbus registers; document it, and enforce by not exposing write functions. Single biggest trust-builder with plant owners (inference).
20. **MQTT hardening** (S). TLS on 8883, per-device credentials (extend `scripts/generate_mqtt_passwords.py`), ACLs restricting each device to its own Sparkplug topic, no anonymous access.
21. **Role-based access + audit log** (M). Roles: owner, supervisor, technician, viewer; extend `server/auth.py`. Audit log already exists for operator decisions (landscape report) — extend to config changes.
22. **DPDP-minimal data design** (S). Store only phone number + display name for alert recipients; consent checkbox and purpose text when adding a recipient; deletion endpoint; retention policy for chat logs. Machine telemetry is non-personal.
23. **Deployment tiers** (M): (a) single-box on-prem (RPi/PC, no internet needed, local LLM optional), (b) edge + cloud dashboard (store-and-forward), (c) multi-tenant SaaS later (tenant_id on every table, per-tenant MQTT namespace). Start with (a)+(b); multi-tenancy is L effort and only needed once there are paying customers.
24. **Production model monitoring** (M). Per-machine feature drift (PSI/KS on RMS, kurtosis), alert precision tracked via work-order outcomes (true alert = WO found a defect), model/version registry with rollback. Weekly "model health" card in UI. Data-scarce review (Q1) warns failures are rare, so precision from WO closures is the only honest metric.
25. **Remote support channel** (S). WireGuard/Tailscale-style outbound-only tunnel for vendor support instead of opening inbound ports; aligns with zone/conduit thinking.

### Gaps
- No India-specific OT security guidance (CERT-In OT advisories) was retrieved.
- IEC 62443 primary text is paywalled; all claims above are via secondary sources.
- DPDP applicability to B2B employee data (operator phone numbers) should be confirmed with counsel; not legal advice.

## Q5. MSME adoption: schemes, competitors' pricing/ROI, barriers

### Takeaway
Government support is mostly non-financial (SAMARTH Udyog centres give awareness, demos, training; Digital MSME cloud subsidy is listed as "yet to be launched"), so ATLAS should partner with SAMARTH centres for pilots rather than count on subsidies. Commercial competitors price per asset per month (≈$40–120 estimated for Nanoprecise; Augury unpublished, vendor-sponsored 310% 3-yr ROI), leaving room for an open, self-hosted, ₹-priced alternative. Barriers are cost, skills and data scarcity more than algorithms.

### Cited Findings
- SAMARTH Udyog Bharat 4.0 (Ministry of Heavy Industries): four centres — C4i4 Lab Pune, IITD-AIA Foundation for Smart Manufacturing, I-4.0 India at IISc Bengaluru, SMDDC at CMTI Bengaluru; no financial assistance to industry for I4.0 adoption, only awareness/training/consulting — [Lok Sabha reply PDF](https://eparlib.nic.in/bitstream/123456789/2970836/1/AS129.pdf); [SAMARTH portal](https://samarthudyog-i40.in/about)
- MSME Champions bundles ZED, MSME Competitive (Lean), MSME Innovative (Incubation, IPR, Design) and Digital MSME; Digital MSME listed as "Yet to be launched"; NSIC named implementing agency Nov 2023; subsidy percentages in 2026 blogs unverified — [NI-MSME](https://nimsme.gov.in/about-scheme/msme-champions-scheme); [incorpx 2026 guide](https://www.incorpx.io/blog/government-schemes-msme-2026-updated)
- Department of Telecommunications launched a 60-day survey of Industry 4.0/IoT use across 10+ sectors for MSMEs; results not found — [Fibre2Fashion](https://fibre2fashion.com/news/textile-news/india-s-dot-launches-industry-4-0-initiative-to-boost-msmes-startups-295887-newsdetails.htm?amp=true)
- NASSCOM/Capgemini: 35–40% of Indian manufacturers at PoC stage; 50% of I4.0 spend on cloud and IoT foundations — [People Matters](https://www.peoplematters.in/?p=32982)
- Deloitte/CII: 30% of Indian manufacturers take a reactive approach to data analysis — [Deloitte PDF](https://www.deloitte.com/content/dam/assets-zone1/in/en/docs/solutions/2025/in-manufacturing-Industry-4.0-Learn-and-Propel-noexp.pdf)
- BITS Pilani survey of 73 Indian firms: I4.0 awareness and adoption remain challenges, especially for SMEs — [BITS DSpace](https://dspace.bits-pilani.ac.in/handle/123456789/18006)
- SME PdM literature: SMEs mostly use preventive/reactive maintenance — [Dolatabadi & Budinska, Machines 2021](https://mdpi.com/2075-1702/9/9/191); mapping study notes lack of SME adoption studies — [Khan et al., IEEE Access 2022](https://doaj.org/article/ca23140a35594f2ebedb85991dc70824)
- Prior report: only ~7% of Indian MSMEs exploring AI; resistance (36%) and cost (18%) top barriers (vendor-sourced) — [ecorpit](https://ecorpit.com/ai-predictive-maintenance-factory-floor-india-roi-2026/)
- Nanoprecise: no public price; third-party estimate $40–120/asset/month — [SoftwareFinder](https://softwarefinder.com/facility-management-software/nanoprecise)
- Augury: per-machine annual service, price unpublished; Forrester TEI (Augury-commissioned) composite: $1.5M savings over 3 years, 310% ROI — [Augury press release](https://www.augury.com/media-center/press/augurys-solutions-delivered-310-3-year-return-according-to-independent-research/); [Forrester TEI](https://tei.forrester.com/go/Augury/Machine-and-Process-Health/?lang=en-us)
- Pilot guidance: 4–8 week pilot on 2–3 assets clarifies ROI; typical ROI 6–18 months (third-party vendor guide) — [Guidewheel](https://www.guidewheel.com/compare/what-is-augury-guide-better-alternative)
- Infinite Uptime: enterprise, quote-based pricing; no public per-machine rate — [Infinite Uptime contact](https://www.infinite-uptime.com/contact/)

### Inferences (enhancement ideas)
26. **"Pilot in a box" kit and protocol** (M). 3 ESP32 nodes + RPi gateway + 6-week protocol (week 1 baseline, weeks 2–6 alerts) + a one-page ROI sheet (downtime hours avoided × ₹/hour, spares avoided). Mirrors the 4–8 week / 2–3 asset pilot pattern competitors use.
27. **ROI calculator in UI** (S). Inputs: machine count, downtime ₹/hour, current breakdowns/year; outputs payback months against kit cost. Converts technical output into the owner's language (cost was the #2 barrier).
28. **Pricing positioning** (decision). Open-source core + paid hardware kit/installation/support, or ~₹300–1,000/machine/month SaaS, well below the $40–120 (≈₹3,300–10,000) per-asset estimate for global players. Numbers are a hypothesis to test in pilots, not evidence.
29. **SAMARTH centre partnership** (S, outreach). Offer ATLAS as an open demo at C4i4 Pune / IISc I-4.0 India / CMTI SMDDC; they run MSME awareness programmes but fund no adoption, so a free, open tool fits their mandate (inference).
30. **ZED / Lean alignment** (S). Map ATLAS outputs to ZED certification maintenance-related parameters and Lean TPM metrics (MTBF, MTTR, availability) so MSMEs pursuing ZED get a reason to adopt. (ZED parameter list not retrieved; see Gaps.)
31. **Case-study instrumentation** (S). Log before/after MTBF, unplanned stoppages and alert precision during pilots; this produces the India-specific, non-vendor ROI evidence that both reports found missing — publishable.

### Gaps
- No rigorous India-specific MSME PdM adoption percentage was found; DoT survey results unpublished in sources found.
- No public pricing for Infinite Uptime, AssetSense, or other Indian startups; Nanoprecise/Augury figures are estimates or vendor-sponsored.
- ZED certification maintenance parameters and MSME TEAM/other 2025–26 schemes were not researched in this pass.
- No 2023–2026 SME-specific PdM barriers systematic review was found; best available are 2021–2022 reviews plus the IIETA data-scarce review (date metadata inconsistent).
