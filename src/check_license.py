import sys
import os
import json
import uuid
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from src.license_features import DEFAULT_FEATURES


def get_device_fingerprint():
    """Generate a unique device fingerprint based on the MAC address."""
    mac = uuid.getnode()
    mac_str = ':'.join(['{:02x}'.format((mac >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
    return hashlib.sha256(mac_str.encode()).hexdigest()

def decrypt_license(encrypted_data: bytes, key: bytes) -> dict:
    """Decrypt the license data using AES encryption."""
    cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
    decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return json.loads(decrypted.decode())

def encrypt_license(data: dict, key: bytes) -> bytes:
    """Encrypt the license data using AES encryption."""
    raw = json.dumps(data).encode()
    cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
    return cipher.encrypt(pad(raw, AES.block_size))

def read_license(license_file: str, secret_key: bytes) -> dict:
    """Read and decrypt the license file."""
    with open(license_file, 'rb') as f:
        encrypted = f.read()
    return decrypt_license(encrypted, secret_key)

def write_license(data: dict, license_file: str, secret_key: bytes):
    """Encrypt and write the license data to a file."""
    with open(license_file, 'wb') as f:
        f.write(encrypt_license(data, secret_key))

def write_bind_info(fingerprint: str, bind_info_file: str):
    """Write the device fingerprint to a bind info file."""
    with open(bind_info_file, 'w') as f:
        json.dump({"fingerprint": fingerprint}, f)

def read_bind_info(bind_info_file: str) -> str:
    """Read the device fingerprint from a bind info file."""
    with open(bind_info_file, 'r') as f:
        return json.load(f)["fingerprint"]

def check_license(secret_key: bytes, license_file: str, bind_info_file: str):
    """
    Check the license file and bind it to the current device.
    If the license is not bound, bind it to the current device's fingerprint.

    Args:
        secret_key (bytes): The secret key for license encryption/decryption.
        license_file (str): Path to the license file.
        bind_info_file (str): Path to the bind info file.

    Returns:
        tuple[int, str, dict]: (status_code, message, license data)
    """
    if not os.path.exists(license_file):
        print(f"Error: {license_file} not found.")
        return -1, "License file not found", {}
    try:
        license_data = read_license(license_file, secret_key)
    except Exception as e:
        print(f"Error reading {license_file}:", str(e))
        return -1, "License file is corrupted or invalid", {}
    fingerprint = get_device_fingerprint()
    if license_data.get("bound_fingerprint") is None:
        license_data["bound_fingerprint"] = fingerprint
        write_license(license_data, license_file, secret_key)
        write_bind_info(fingerprint, bind_info_file)
        print("License successfully bound to this device.")
        license_data.setdefault("features", DEFAULT_FEATURES)
        return 0, "License successfully bound to this device", license_data
    elif license_data["bound_fingerprint"] != fingerprint:
        print("Error: License is bound to another device!")
        return -1, "License is bound to another device", {}
    elif os.path.exists(bind_info_file):
        if read_bind_info(bind_info_file) != fingerprint:
            print("Error: Device fingerprint mismatch!")
            return -1, "Device fingerprint mismatch", {}
        else:
            print("License is already bound to this device.")
            license_data.setdefault("features", DEFAULT_FEATURES)
            return 0, "License checked successfully, already bound to this device", license_data
    else:
        write_bind_info(fingerprint, bind_info_file)
        license_data.setdefault("features", DEFAULT_FEATURES)
        return 0, "License successfully bound to this device", license_data
