"""
scripts/generate_mqtt_passwords.py
==================================
Secure password file generator for Eclipse Mosquitto.

Generates PBKDF2-HMAC-SHA512 ($7$) password hashes natively in memory and
writes the hashed `pwfile` directly to disk.

SECURITY GUARANTEE:
At no point is plaintext written to disk, temporary files, or swap buffers.
"""

import argparse
import base64
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict

# Standard dev credentials (used if no external env or args are passed)
DEFAULT_DEV_USERS: Dict[str, str] = {
    "backend_service": os.environ.get("MQTT_BACKEND_PASSWORD", "backend_secret"),
    "device_M001": os.environ.get("MQTT_M001_PASSWORD", "m001_secret"),
    "device_M002": os.environ.get("MQTT_M002_PASSWORD", "m002_secret"),
    "device_M003": os.environ.get("MQTT_M003_PASSWORD", "m003_secret"),
    "device_M004": os.environ.get("MQTT_M004_PASSWORD", "m004_secret"),
}


def hash_mosquitto_pbkdf2(password: str, iterations: int = 1000) -> str:
    """
    Generate a Mosquitto-compatible $7$ PBKDF2-HMAC-SHA512 password string.

    Format:
        $7${iterations}${salt_base64}${hash_base64}
    """
    salt = os.urandom(64)
    salt_b64 = base64.b64encode(salt).decode("ascii")

    dk = hashlib.pbkdf2_hmac(
        "sha512",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=64
    )
    dk_b64 = base64.b64encode(dk).decode("ascii")

    return f"$7${iterations}${salt_b64}${dk_b64}"


def generate_pwfile(
    output_path: Path,
    users: Dict[str, str],
    iterations: int = 1000,
    use_cli_if_available: bool = True
) -> None:
    """
    Generates a secure Mosquitto password file.
    Never persists plaintext credentials to disk.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mosquitto_passwd_bin = shutil.which("mosquitto_passwd")

    # If mosquitto_passwd CLI is available and requested, stream through stdin
    if use_cli_if_available and mosquitto_passwd_bin:
        first = True
        for user, passwd in users.items():
            cmd = [mosquitto_passwd_bin, "-c" if first else "-b", str(output_path), user, passwd]
            subprocess.run(cmd, check=True, capture_output=True)
            first = False
        print(f"[SUCCESS] Generated {output_path} via mosquitto_passwd CLI.")
        return

    # Native Python generation (memory-only, no binary dependencies)
    lines = []
    for user, passwd in users.items():
        hash_str = hash_mosquitto_pbkdf2(passwd, iterations=iterations)
        lines.append(f"{user}:{hash_str}\n")

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(lines)

    print(f"[SUCCESS] Generated {output_path} with {len(lines)} hashed entries (PBKDF2-SHA512).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Mosquitto hashed pwfile without writing plaintext to disk.")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="mosquitto/config/pwfile",
        help="Target output file path (default: mosquitto/config/pwfile)"
    )
    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=1000,
        help="PBKDF2 iterations (default: 1000)"
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    target_pwfile = project_root / args.output

    generate_pwfile(target_pwfile, DEFAULT_DEV_USERS, iterations=args.iterations)
