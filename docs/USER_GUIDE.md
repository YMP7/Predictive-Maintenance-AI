# AI Digital Twin - User Guide

Welcome to the AI Digital Twin Predictive Maintenance System. This guide helps machine operators and shop floor managers monitor machinery health, interpret alerts, and act on maintenance recommendations.

---

## 1. Quick Start

### Accessing the Dashboard
1. Open your web browser and navigate to `http://localhost:3000`.
2. You will be greeted by the **Home Page**, which provides a high-level system overview.
3. Click the **"Launch Dashboard"** button in the navigation bar or home screen to access the real-time monitoring interface.

---

## 2. Understanding the Dashboard

The dashboard is designed to give you a real-time status of all connected shop floor machines.

### Machine Status Cards
Each machine is represented by a card that dynamically changes color based on its current operational health:
* 🟢 **Normal (Green)**: The machine is running within safe operating limits. No action is required.
* 🟡 **Warning (Yellow)**: Anomalous behavior has been detected (e.g., elevated vibration or temperature). Schedule maintenance during the next convenient window.
* 🔴 **Critical (Red)**: Severe operating threshold breached. Immediate action is required to prevent catastrophic failure or operator injury. Stop the machine.

### Key Telemetry Metrics
Each card displays live values for the following key physical parameters:
1. **RUL (Remaining Useful Life)**: The estimated number of days the machine can safely run before predicted failure.
2. **Vibration**: Root Mean Square (RMS) vibration level in mm/s. High vibration indicates misalignment, imbalance, or bearing wear.
3. **Temperature**: Internal operating temperature in °C. Elevated temperatures indicate friction, overloading, or cooling failure.
4. **Current**: Electrical current draw in Amperes. Abnormal current indicates motor strain or electrical issues.

---

## 3. Interpreting Alerts

The system automatically generates alerts when anomalous telemetry is processed by the AI agent.

### Alert Severity Levels
* 🚨 **Critical**: Represents immediate danger of machine failure. Stop the machine and perform emergency inspection.
* ⚠️ **High**: Significant degradation detected. Schedule maintenance within the next 24-48 hours.
* ⚡ **Medium**: Early signs of anomaly. Increase monitoring frequency and order spare parts if necessary.
* ℹ️ **Low**: Minor deviations from normal behavior. Safe to continue operation under monitoring.

### Sample Alerts and Meaning
* `[Critical] Machine M002 - Vibration RMS is critically high (3.24 mm/s). Severe bearing wear suspected.` -> Action: Shut down pump motor immediately.
* `[Warning] Machine M004 - Temperature is elevated (84.5°C). Check ventilation and load.` -> Action: Verify furnace cooling fans and reduce load if necessary.

---

## 4. Maintenance Recommendations

The AI agent provides automated recommendations based on estimated Remaining Useful Life (RUL):

| RUL Estimate | Priority | Recommended Action |
| :--- | :--- | :--- |
| **< 3 Days** | **Emergency** | Shut down the machine immediately and perform repairs. |
| **3 - 7 Days** | **High** | Schedule maintenance within the week. Prepare parts and technician. |
| **7 - 14 Days** | **Medium** | Plan maintenance in the next scheduled downtime cycle. |
| **> 14 Days** | **Routine** | Continue normal monitoring; check lubrication and filters during standard maintenance. |

---

## 5. Operator Troubleshooting

### Dashboard Not Loading
* **Verify Service Status**: Ensure that both backend API and frontend servers are running (ask your system administrator).
* **Browser Cache**: Try clearing your browser cache or opening the dashboard in an Incognito/Private window.
* **Network Connection**: Verify you are on the same local network as the server hosting the prototype.

### Telemetry / Alerts Not Updating
* Ensure the simulator or physical sensors are running.
* Check if there are error logs in the browser console (press `F12` -> Console).

---

## 6. Support
For technical support, sensor installation requests, or system integration issues, contact your designated System Administrator or the Development Team.
