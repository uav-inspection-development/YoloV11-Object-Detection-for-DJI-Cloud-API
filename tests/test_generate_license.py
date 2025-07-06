import json
import sys
import types
from unittest.mock import MagicMock


def ensure_module(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name.rsplit('.', 1)[-1])
    sys.modules[name] = module
    if '.' in name:
        parent, child = name.rsplit('.', 1)
        parent_mod = ensure_module(parent)
        setattr(parent_mod, child, module)
    return module


for mod in [
    'Crypto',
    'Crypto.Cipher',
    'Crypto.Util',
    'Crypto.Util.Padding',
]:
    ensure_module(mod)

sys.modules['Crypto.Cipher'].AES = MagicMock()
sys.modules['Crypto.Util.Padding'].pad = lambda d, b: d

import src.generate_license as gl

class DummyCipher:
    def __init__(self):
        self.data = None
    def encrypt(self, data):
        self.data = data
        return b'encrypted'

def test_generate_license_features(tmp_path, monkeypatch):
    cipher = DummyCipher()
    monkeypatch.setattr(gl.AES, 'new', lambda *a, **k: cipher)
    monkeypatch.setattr(gl, 'pad', lambda data, bs: data)
    output = tmp_path / 'license.dat'
    gl.generate_license(
        b'0123456789abcdef',
        'user@example.com',
        'LIC-1',
        '2026-01-01',
        str(output),
        ['检测任务', '红外'],
    )
    license_json = cipher.data.decode()
    data = json.loads(license_json)
    assert data['features'] == ['检测任务', '红外']

