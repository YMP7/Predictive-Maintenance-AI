"""
Alert Handler - Manages alert delivery and notifications with thread safety,
cooldown suppression, error isolation, severity routing, and localizations.
"""

import os
import json
import queue
import logging
import threading
import smtplib
import ssl
from collections import deque
from datetime import datetime
from email.message import EmailMessage
from html import escape
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logger sharing configured DigitalTwin logger
logger = logging.getLogger("DigitalTwin")

class AlertChannel(Enum):
    """Alert delivery channels"""
    DASHBOARD = "dashboard"
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"
    LOG = "log"

# Multi-language translation templates for Telangana, Tamil Nadu, and regional MSME operators
TRANSLATIONS = {
    "hi": {
        "Critical Vibration Level": "गंभीर कंपन स्तर",
        "Elevated Vibration (Warning)": "बढ़ा हुआ कंपन (चेतावनी)",
        "Critical Temperature Level": "गंभीर तापमान स्तर",
        "Elevated Temperature (Warning)": "बढ़ा हुआ तापमान (चेतावनी)",
        "Critical Current Draw": "गंभीर करंट प्रवाह",
        "Elevated Current (Warning)": "बढ़ा हुआ करंट (चेतावनी)",
        "Low Remaining Useful Life": "कम शेष उपयोगी जीवन",
        "detected in": "में पाया गया",
        "days remaining": "दिन शेष"
    },
    "te": {
        "Critical Vibration Level": "తీవ్రమైన వైబ్రేషన్ స్థాయి",
        "Elevated Vibration (Warning)": "పెరిగిన వైబ్రేషన్ (హెచ్చరిక)",
        "Critical Temperature Level": "తీవ్రమైన ఉష్ణోగ్రత స్థాయి",
        "Elevated Temperature (Warning)": "పెరిగిన ఉష్ణోగ్రత (హెచ్చరిక)",
        "Critical Current Draw": "తీవ్రమైన విద్యుత్ ప్రవాహం",
        "Elevated Current (Warning)": "పెరిగిన విద్యుత్ ప్రవాహం (హెచ్చరిక)",
        "Low Remaining Useful Life": "తక్కువ ఉపయోగకరమైన జీవితకాలం",
        "detected in": "లో గుర్తించబడింది",
        "days remaining": "రోజులు మిగిలి ఉన్నాయి"
    },
    "ta": {
        "Critical Vibration Level": "தீவிர அதிர்வு நிலை",
        "Elevated Vibration (Warning)": "அதிகரித்த அதிர்வு (எச்சரிக்கை)",
        "Critical Temperature Level": "தீவிர வெப்பநிலை நிலை",
        "Elevated Temperature (Warning)": "அதிகரித்த வெப்பநிலை (எச்சரிக்கை)",
        "Critical Current Draw": "தீவிர மின்னோட்ட அளவு",
        "Elevated Current (Warning)": "அதிகரித்த மின்னோட்டம் (எச்சரிக்கை)",
        "Low Remaining Useful Life": "குறைந்த மீதமுள்ள பயனுள்ள ஆயுள்",
        "detected in": "இல் கண்டறியப்பட்டது",
        "days remaining": "நாட்கள் மீதமுள்ளன"
    },
    "mr": {
        "Critical Vibration Level": "गंभीर कंपन पातळी",
        "Elevated Vibration (Warning)": "वाढलेले कंपन (इशारा)",
        "Critical Temperature Level": "गंभीर तापमान पातळी",
        "Elevated Temperature (Warning)": "वाढलेले तापमान (इशारा)",
        "Critical Current Draw": "गंभीर विद्युत प्रवाह",
        "Elevated Current (Warning)": "वाढलेला विद्युत प्रवाह (इशारा)",
        "Low Remaining Useful Life": "कमी उर्वरित उपयुक्त आयुष्य",
        "detected in": "मध्ये आढळले",
        "days remaining": "दिवस शिल्लक"
    }
}

def translate_message(message: str, lang: str) -> str:
    if lang == "en":
        return message
        
    # Translate fault detection templates
    if "detected in" in message:
        parts = message.split(" detected in ")
        issues_part = parts[0]
        machine_id = parts[1]
        
        translated_issues = []
        lang_dict = TRANSLATIONS.get(lang, {})
        for issue in issues_part.split(", "):
            translated_issues.append(lang_dict.get(issue, issue))
        
        joined_issues = ", ".join(translated_issues)
        
        if lang == "hi":
            return f"{machine_id} में {joined_issues} पाया गया"
        elif lang == "te":
            return f"{machine_id} లో {joined_issues} గుర్తించబడింది"
        elif lang == "ta":
            return f"{machine_id} இல் {joined_issues} கண்டறியப்பட்டது"
        elif lang == "mr":
            return f"{machine_id} मध्ये {joined_issues} आढळले"
            
    # Translate RUL warnings: e.g. "Low Remaining Useful Life: 5 days remaining"
    if "Low Remaining Useful Life:" in message:
        try:
            days = message.split("Low Remaining Useful Life: ")[1].split(" days remaining")[0]
            if lang == "hi":
                return f"कम शेष उपयोगी जीवन: {days} दिन शेष"
            elif lang == "te":
                return f"తక్కువ ఉపయోగకరమైన జీవితకాలం: {days} రోజులు మిగిలి ఉన్నాయి"
            elif lang == "ta":
                return f"குறைந்த மீதமுள்ள பயனுள்ள ஆயுள்: {days} நாட்கள் மீதமுள்ளன"
            elif lang == "mr":
                return f"कमी उर्वरित उपयुक्त आयुष्य: {days} दिवस शिल्लक"
        except Exception:
            pass
            
    return message

class AlertHandler:
    """Handles alert delivery with thread safety, memory capping, and cooldowns."""
    
    def __init__(self):
        # Thread-safe queue for incoming alerts
        self.alert_queue = queue.Queue()
        
        # Thread-safe bounded deque for history
        self.delivered_alerts = deque(maxlen=1000)
        self._lock = threading.Lock()
        
        # Cooldown management: tracks (machine_id, alert_type) -> timestamp
        self.last_alert_time: Dict[Tuple[str, str], float] = {}
        self.cooldown_seconds = int(os.environ.get("ALERT_COOLDOWN", 300))
        self.alert_languages = [
            lang.strip()
            for lang in os.environ.get("ALERT_LANGUAGES", "en").split(",")
            if lang.strip()
        ] or ["en"]
        
        logger.info(f"AlertHandler initialized with Cooldown={self.cooldown_seconds}s")

    def get_channels_by_severity(self, severity: str) -> List[AlertChannel]:
        """Automatically route alerts based on their severity level."""
        sev = severity.capitalize()
        if sev == "Critical":
            return [AlertChannel.DASHBOARD, AlertChannel.LOG, AlertChannel.SMS, AlertChannel.EMAIL, AlertChannel.VOICE]
        elif sev == "High":
            return [AlertChannel.DASHBOARD, AlertChannel.LOG, AlertChannel.SMS, AlertChannel.EMAIL]
        elif sev == "Medium":
            return [AlertChannel.DASHBOARD, AlertChannel.LOG, AlertChannel.EMAIL]
        else:  # Low / Info
            return [AlertChannel.DASHBOARD, AlertChannel.LOG]

    def queue_alert(self, alert: Dict, channels: List[AlertChannel] = None) -> bool:
        """Queue alert for processing, implementing deduplication cooldown."""
        machine_id = alert.get("machine_id", "Unknown")
        alert_type = alert.get("type", "General")
        fault_type = alert.get("fault_type") or alert_type
        severity = alert.get("severity", "Medium")
        
        # Cooldown check
        cooldown_key = (machine_id, fault_type)
        now = datetime.now().timestamp()
        
        with self._lock:
            if cooldown_key in self.last_alert_time:
                time_passed = now - self.last_alert_time[cooldown_key]
                if time_passed < self.cooldown_seconds:
                    logger.debug(f"Alert suppressed due to cooldown: {machine_id} {alert_type} (time remaining: {self.cooldown_seconds - time_passed:.1f}s)")
                    return False
            self.last_alert_time[cooldown_key] = now

        # Add localized translations
        localizations = {}
        message = alert.get("message", "")
        for lang in self.alert_languages:
            localizations[lang] = translate_message(message, lang)

        # Route by severity if no custom channels supplied
        if channels is None:
            channels = self.get_channels_by_severity(severity)

        alert_with_metadata = {
            **alert,
            "channels": [c.value for c in channels],
            "localizations": localizations,
            "queued_at": datetime.now().isoformat()
        }

        self.alert_queue.put(alert_with_metadata)
        logger.info(f"Alert queued: {message} [Channels: {[c.value for c in channels]}]")
        
        # Process asynchronously or synchronously as required
        self.process_alerts()
        return True

    def process_alerts(self):
        """Process and deliver all queued alerts."""
        while not self.alert_queue.empty():
            try:
                alert = self.alert_queue.get_nowait()
                self._deliver_alert(alert)
                self.alert_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing alert: {e}")

    def _deliver_alert(self, alert: Dict):
        """Deliver alert through configured channels with robust error isolation."""
        for channel in alert.get("channels", []):
            try:
                if channel == "dashboard":
                    self._deliver_dashboard(alert)
                elif channel == "sms":
                    self._deliver_sms(alert)
                elif channel == "email":
                    self._deliver_email(alert)
                elif channel == "voice":
                    self._deliver_voice(alert)
                elif channel == "log":
                    self._deliver_log(alert)
            except Exception as e:
                logger.error(f"Failed to deliver alert to channel '{channel}': {e}")
        
        with self._lock:
            self.delivered_alerts.append(alert)

    def _deliver_dashboard(self, alert: Dict):
        """Deliver to dashboard logs."""
        logger.debug(f"[DASHBOARD DELIVERY] {alert['message']}")

    def _deliver_sms(self, alert: Dict):
        """Deliver SMS through Twilio when configured; otherwise log simulation."""
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_num = os.environ.get("TWILIO_FROM_NUMBER")
        to_num = os.environ.get("TWILIO_TO_NUMBER")

        if not all([account_sid, auth_token, from_num, to_num]):
            logger.warning("[SMS STUB] Missing Twilio credentials. Logging simulation instead.")
            logger.info(f"[SMS SIMULATION] To: {to_num or 'N/A'}, Msg: {alert['message']}")
            return

        try:
            from twilio.rest import Client
        except ImportError:
            logger.warning("[SMS SIMULATION] Twilio SDK is not installed. Install twilio to send real SMS.")
            return

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=alert["message"],
            from_=from_num,
            to=to_num,
        )
        logger.info("[SMS DELIVERED] Twilio message SID: %s", message.sid)

    def _deliver_email(self, alert: Dict):
        """Deliver email through SMTP when configured; otherwise log simulation."""
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        smtp_from = os.environ.get("SMTP_FROM") or smtp_user
        to_email = os.environ.get("ALERT_EMAIL_TO")

        if not all([smtp_host, smtp_port, smtp_from, to_email]):
            logger.warning("[EMAIL STUB] Missing SMTP credentials. Logging simulation instead.")
            logger.info(f"[EMAIL SIMULATION] To: {to_email or 'N/A'}, Msg: {alert['message']}")
            return

        msg = EmailMessage()
        msg["Subject"] = f"AI Digital Twin Alert: {alert.get('severity', 'Alert')}"
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg.set_content(alert["message"])

        context = ssl.create_default_context()
        use_ssl = os.environ.get("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
        use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}

        if use_ssl or smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10) as server:
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if use_tls:
                    server.starttls(context=context)
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)

        logger.info("[EMAIL DELIVERED] Alert email sent to %s", to_email)

    def _deliver_voice(self, alert: Dict):
        """Deliver a voice call through Twilio when configured; otherwise log simulation."""
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_num = os.environ.get("TWILIO_FROM_NUMBER")
        to_num = os.environ.get("TWILIO_TO_NUMBER")

        if not all([account_sid, auth_token, from_num, to_num]):
            logger.warning("[VOICE STUB] Missing Twilio credentials. Logging simulation instead.")
            logger.info(f"[VOICE SIMULATION] Dialing: {to_num or 'N/A'}, Announcement: {alert['message']}")
            return

        try:
            from twilio.rest import Client
        except ImportError:
            logger.warning("[VOICE SIMULATION] Twilio SDK is not installed. Install twilio to send real calls.")
            return

        twiml = f"<Response><Say>{escape(alert['message'])}</Say></Response>"
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            twiml=twiml,
            from_=from_num,
            to=to_num,
        )
        logger.info("[VOICE DELIVERED] Twilio call SID: %s", call.sid)

    def _deliver_log(self, alert: Dict):
        """Log alert securely."""
        logger.info(f"[ALERT LOGGED] {json.dumps(alert, indent=2)}")

# Global alert handler singleton
_alert_handler = None

def get_alert_handler():
    global _alert_handler
    if _alert_handler is None:
        _alert_handler = AlertHandler()
    return _alert_handler
