from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import json
import os

import build_exe


def test_generate_license_bundle_creates_matching_license_and_secret_key(tmp_path):
    assert build_exe.generate_license_bundle(tmp_path)

    secret_key = (tmp_path / "secret_key.txt").read_text(encoding="ascii").strip()
    encrypted_license = (tmp_path / "license.dat").read_bytes()
    cipher = AES.new(
        secret_key.encode("ascii"),
        AES.MODE_CBC,
        iv=secret_key[:16].encode("ascii"),
    )
    license_data = json.loads(
        unpad(cipher.decrypt(encrypted_license), AES.block_size).decode("utf-8")
    )

    assert len(secret_key) == 32
    assert license_data["license_id"].startswith("BUILD-")
    assert license_data["valid_until"] == "9999-12-31"
    assert license_data["bound_fingerprint"] is None
    assert license_data["features"]


def test_no_key_runtime_hook_enables_no_key_mode(tmp_path, monkeypatch):
    hook_path = tmp_path / "no_key_runtime_hook.py"
    monkeypatch.setattr(build_exe, "NO_KEY_RUNTIME_HOOK", hook_path)
    monkeypatch.delenv("YOLO_NO_KEY_MODE", raising=False)

    created_hook = build_exe.create_no_key_runtime_hook()
    exec(created_hook.read_text(encoding="ascii"), {})

    assert os.environ["YOLO_NO_KEY_MODE"] == "1"
