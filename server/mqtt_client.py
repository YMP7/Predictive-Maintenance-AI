import os
import json
import logging
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field, ValidationError
import paho.mqtt.client as mqtt

logger = logging.getLogger("DigitalTwin")

class VibrationPayload(BaseModel):
    x: float
    y: float
    z: float
    rms: float = Field(ge=0)

class TelemetryPayload(BaseModel):
    timestamp: str
    vibration: VibrationPayload
    temperature: float = Field(ge=-100) # Basic sane lower bound
    current: float = Field(ge=0)

class MQTTClientManager:
    def __init__(self, ingest_callback: Callable[[str, Dict[str, Any]], None]):
        """
        ingest_callback takes (machine_id, reading) and integrates it into the DataService.
        """
        self.ingest_callback = ingest_callback
        self.broker = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self.port = int(os.environ.get("MQTT_BROKER_PORT", 1883))
        self.username = os.environ.get("MQTT_USERNAME")
        self.password = os.environ.get("MQTT_PASSWORD")
        
        self.tls_enabled = os.environ.get("MQTT_TLS_ENABLED", "false").lower() == "true"
        cors_origins = os.environ.get("CORS_ORIGINS", "")
        
        # Security enforcement: TLS must be true if running outside localhost
        if not self.tls_enabled and "localhost" not in cors_origins and cors_origins != "*":
            logger.error("INSECURE CONFIGURATION: MQTT_TLS_ENABLED is false but CORS_ORIGINS implies production.")
            raise ValueError("TLS must be enabled (MQTT_TLS_ENABLED=true) for non-local production MQTT ingestion.")
        
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
        if self.tls_enabled:
            import ssl
            # In a real production environment, you would provide the path to your CA certs
            # e.g., self.client.tls_set(ca_certs="path/to/ca.crt", cert_reqs=ssl.CERT_REQUIRED)
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
            
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        else:
            logger.warning("MQTT_USERNAME or MQTT_PASSWORD not set. Failing loudly as per security policy.")
            raise ValueError("MQTT credentials are required when MQTT is enabled.")
            
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        
    def start(self):
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
            
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info(f"Successfully connected to MQTT broker at {self.broker}")
            # Subscribe to all telemetry topics
            self.client.subscribe("factory/+/telemetry")
        else:
            logger.error(f"Failed to connect to MQTT broker with reason code {reason_code}")
            
    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        logger.warning(f"Disconnected from MQTT broker with reason code {reason_code}")
        
    def on_message(self, client, userdata, msg):
        try:
            # Topic format: factory/{machine_id}/telemetry
            parts = msg.topic.split('/')
            if len(parts) != 3 or parts[0] != "factory" or parts[2] != "telemetry":
                logger.warning(f"Received message on unexpected topic: {msg.topic}")
                return
                
            machine_id = parts[1]
            
            # Parse JSON
            payload_str = msg.payload.decode('utf-8')
            raw_dict = json.loads(payload_str)
            
            # Validate with Pydantic
            telemetry = TelemetryPayload(**raw_dict)
            
            # Form final reading dictionary matching expected format
            reading = {
                "machine_id": machine_id,
                "timestamp": telemetry.timestamp,
                "vibration": {
                    "x": telemetry.vibration.x,
                    "y": telemetry.vibration.y,
                    "z": telemetry.vibration.z,
                    "rms": telemetry.vibration.rms
                },
                "temperature": telemetry.temperature,
                "current": telemetry.current,
            }
            
            # Push to ingest callback
            self.ingest_callback(machine_id, reading)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Dropped MQTT message on {msg.topic} due to malformed JSON: {e}")
        except ValidationError as e:
            logger.warning(f"Dropped MQTT message on {msg.topic} due to validation failure: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing MQTT message on {msg.topic}: {e}")
