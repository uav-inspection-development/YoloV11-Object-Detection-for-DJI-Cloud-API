import sys
import runpy
import types
from unittest.mock import MagicMock

# Mock external modules that may not be installed
# Modules that may be missing in the testing environment
MOCK_MODULES = [
    'QtFusion', 'QtFusion.path', 'QtFusion.utils', 'QtFusion.models',
    'ultralytics', 'ultralytics.utils', 'ultralytics.utils.torch_utils',
    'IMcore', 'efficientnet_pytorch', 'pandas', 'PIL', 'docx', 'docx.shared',
    'matplotlib', 'matplotlib.colors', 'scipy', 'scipy.optimize', 'requests',
    'Crypto', 'Crypto.Cipher', 'Crypto.Util', 'Crypto.Util.Padding', 'psutil',
    'cv2', 'torch', 'streamlit', 'streamlit.web', 'streamlit.web.cli', 'numpy',
    'cryptography', '_cffi_backend'
]


def ensure_module(name: str) -> types.ModuleType:
    """Create a dummy module and its parents if they do not exist."""
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name.rsplit('.', 1)[-1])
    sys.modules[name] = module
    if '.' in name:
        parent_name, child = name.rsplit('.', 1)
        parent = ensure_module(parent_name)
        setattr(parent, child, module)
    return module


for mod in MOCK_MODULES:
    ensure_module(mod)

# Provide simple stub attributes used during import
sys.modules['QtFusion.utils'].drawRectBox = lambda *a, **k: None
sys.modules['PIL'].Image = MagicMock()
sys.modules['PIL'].ImageFont = MagicMock()
sys.modules['PIL'].ImageDraw = MagicMock()
sys.modules['docx'].Document = MagicMock()
sys.modules['docx.shared'].Inches = MagicMock()
sys.modules['QtFusion.models'].Detector = MagicMock()
sys.modules['QtFusion.models'].HeatmapGenerator = MagicMock()
sys.modules['ultralytics'].YOLO = MagicMock()

sys.modules['Crypto.Cipher'].AES = MagicMock()
sys.modules['Crypto.Util.Padding'].pad = MagicMock()
sys.modules['Crypto.Util.Padding'].unpad = MagicMock()
sys.modules['ultralytics.utils.torch_utils'].select_device = MagicMock()
sys.modules['matplotlib.colors'].LinearSegmentedColormap = MagicMock()
sys.modules['streamlit.web.cli'].main = MagicMock()
sys.modules['torch'].cuda = MagicMock(is_available=lambda: False)
sys.modules['scipy.optimize'].minimize = MagicMock()
# Provide abs_path function used in main.py
sys.modules['QtFusion.path'].abs_path = lambda x: x

import main


def test_run_streamlit(monkeypatch):
    captured = {}

    def fake_main():
        captured['argv'] = sys.argv.copy()

    monkeypatch.setattr(main.stcli, 'main', fake_main)
    main.run_streamlit('app.py', ['--foo', 'bar'])
    assert captured['argv'] == [
        'streamlit',
        'run',
        'app.py',
        '--global.developmentMode=false',
        '--',
        '--foo',
        'bar',
    ]


def test_run_api(monkeypatch):
    called = {}

    def fake_run(cmd, check=True):
        called['cmd'] = cmd
        called['check'] = check

    monkeypatch.setattr(main.subprocess, 'run', fake_run)
    main.run_api('api.py', ['--x', '1'])
    assert called['cmd'] == ['python', 'api.py', '--x', '1']
    assert called['check'] is True


def test_main_block_streamlit(monkeypatch):
    cli_module = sys.modules['streamlit.web.cli']
    cli_module.main = MagicMock()
    monkeypatch.setattr(sys, 'argv', ['main.py'])
    runpy.run_path('main.py', run_name='__main__')
    cli_module.main.assert_called_once()


def test_main_block_api(monkeypatch):
    run_stub = MagicMock()
    monkeypatch.setattr(sys, 'argv', [
        'main.py', '--secret-key', 'k', '--license-file', 'l',
        '--bind-info-file', 'b', '--run-mode=api'
    ])
    monkeypatch.setattr('subprocess.run', run_stub)
    runpy.run_path('main.py', run_name='__main__')
    assert run_stub.call_args[0][0][:2] == ['python', 'src/ui.py']

