# Mobile Device Reversion & Cleanup Guide

This document records all settings, permissions, and files introduced for mobile telemetry streaming, and details how to revert them 100% to their original state once this project is complete.

---

## 1. Automated Reversion (Recommended)

When the project is finished, connect your phone via USB and run the automated cleanup script:

```powershell
scripts\cleanup_mobile_device.bat
```

This single command executes:
1. **Removes all port forwarding rules** (`adb forward --remove tcp:8088`).
2. **Revokes Termux storage permissions** (`pm revoke com.termux android.permission.READ_EXTERNAL_STORAGE` and `WRITE_EXTERNAL_STORAGE`).
3. **Deletes all staged bridge files** from phone storage (`/data/local/tmp/termux_bridge.py` and `/sdcard/termux_bridge.py`).
4. **Shuts down the ADB daemon** on your laptop (`adb kill-server`).

---

## 2. Manual Reversion Checklist

If you prefer to revert things manually, follow these quick steps:

### A. On the Android Phone
1. **Disable USB Debugging**:
   - Open Android **Settings** $\rightarrow$ **System** (or **Additional Settings**) $\rightarrow$ **Developer Options**.
   - Toggle **USB Debugging** to **OFF** (or toggle **Use developer options** to **OFF**).
2. **Revoke Termux Storage Permissions**:
   - Long press the **Termux** app icon $\rightarrow$ Tap **App Info** (ℹ️).
   - Tap **Permissions** $\rightarrow$ **Files and Media** (or **Storage**) $\rightarrow$ Select **Don't Allow**.
3. **Uninstall Termux & Termux:API (Optional)**:
   - If you do not need Termux for anything else, you can uninstall both **Termux** and **Termux:API** from your phone like any regular app.

### B. On the Laptop
1. **Kill ADB Server**:
   ```powershell
   adb kill-server
   ```
2. **Remove Google Platform-Tools (Optional)**:
   - If you don't use ADB for anything else:
     ```powershell
     winget uninstall --id Google.PlatformTools
     ```

---

## 3. Reminder Protocol
Antigravity maintains a project completion checklist. At the end of the project walkthrough and final wrap-up, you will be prompted to run `scripts\cleanup_mobile_device.bat` to ensure no lingering background processes or permissions remain.
