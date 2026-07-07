# AI Digital Twin Prototype - Demonstration Video Script

This document details the script and scene breakdown for the AI Digital Twin and Predictive Maintenance system demonstration video.

---

## Video Outline

* **Total Duration**: Approx. 5 - 6 minutes
* **Objective**: Show how the AI agent detects faults, predicts remaining useful life (RUL), and notifies operators to prevent downtime in MSME settings.
* **Target Audience**: Business owners, operators, and potential clients.

---

## Scene Breakdown

### Scene 1: Introduction (Duration: ~0:45)
* **Visual**: Screen recording of the system landing page. The browser transitions from the welcome screen, displaying the dashboard cards, with a cursor hovering over different components.
* **Narrator Script**:
  > *"Welcome to this walkthrough of the AI-Powered Digital Twin and Predictive Maintenance System. Built specifically for MSMEs, this prototype demonstrates how artificial intelligence and real-time sensor simulation combine to predict machinery failures before they occur, allowing operators to schedule maintenance proactively and eliminate unexpected downtime."*

### Scene 2: Dashboard Overview (Duration: ~1:15)
* **Visual**: Close-up of the dashboard. Show the 4 machine cards (Lathe Machine, Pump Motor, Drill Press, Furnace) starting in the green "Normal" state. Point out the live telemetry values (Vibration, Temperature, Current) updating every second.
* **Narrator Script**:
  > *"Here is the main operator dashboard. We are currently monitoring four key assets on our simulated shop floor. Each machine card acts as a 'digital twin,' mirroring the real-time physical telemetry of the asset. The cards are color-coded: green represents healthy, yellow is warning, and red demands immediate attention. Under normal operation, vibration, temperature, and current are stable and within safe thresholds."*

### Scene 3: Under the Hood - Machine Details & Trends (Duration: ~1:00)
* **Visual**: Click on one of the cards (e.g., Lathe Machine M001) to open its detailed view showing live charts of vibration RMS, temperature, and current trends.
* **Narrator Script**:
  > *"By clicking on any machine, operators can inspect its detailed telemetry trends. Recharts-powered graphs show running histories of vibration, temperature, and current. This detailed telemetry helps maintenance engineers understand exactly how the machine's behavior changes over time, facilitating precise diagnoses."*

### Scene 4: Anomaly Detection & Injected Fault Demo (Duration: ~1:00)
* **Visual**: The simulator fault mode for Machine M002 is set to `bearing_wear` (e.g., using the `demo_scenarios.py` runner or backend control). On screen, the Pump Motor card starts displaying rising vibration and temperature. The status changes to yellow "Warning" and then to red "Critical".
* **Narrator Script**:
  > *"Now, let's witness the predictive engine in action. We will simulate a bearing wear fault on the Pump Motor, Machine M002. As the bearing wear progresses, the vibration RMS and temperature rise. The AI agent immediately flags this deviation, changing the card's state to warning, and then critical as it exceeds safe parameters."*

### Scene 5: RUL Estimation & Recommendations (Duration: ~1:00)
* **Visual**: Focus on the RUL and recommendations section on the Pump Motor's details page. The estimated remaining useful life decreases from 30 days to under 3 days, and the text recommendation changes to "Stop machine, perform emergency maintenance".
* **Narrator Script**:
  > *"Unlike traditional threshold alert systems, our AI agent calculates the Remaining Useful Life, or RUL, of the asset. Notice how the RUL prediction drops as the fault degrades. The system provides clear recommendations: recommending routine service when RUL is high, and issuing an urgent alert to shut down the asset when RUL drops below 3 days. This prevents catastrophic damage to the machinery."*

### Scene 6: Real-time Alert panel (Duration: ~0:45)
* **Visual**: The side-panel or alert log showing the historical alerts table. Highlight critical alert messages with their exact timestamps and severity tags.
* **Narrator Script**:
  > *"Every anomaly detected by the AI agent is logged in our centralized Alert System. Alerts are prioritized by severity (Critical, High, Medium, and Low) and persisted in a SQLite database, providing a complete maintenance audit trail that helps administrators track machine reliability trends over time."*

### Scene 7: Conclusion & Admin Guide (Duration: ~0:45)
* **Visual**: Slide showing key benefits (Uptime increase, cost reduction, ease of deployment) and contact details, then switching back to the administrator CLI output showing the final verification checklist passing.
* **Narrator Script**:
  > *"The prototype is fully packaged with Docker and complete user and administrator documentation, making it easy to deploy in any local or cloud environment. This digital twin prototype brings enterprise-grade predictive maintenance directly to the shop floor. Thank you for watching."*
