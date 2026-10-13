# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

base_dir = Path.cwd().resolve()
entrypoint = base_dir / 'app' / 'main.py'
assets_dir = base_dir / 'assets'
icon_file = assets_dir / 'app_icon.icns'

a = Analysis(
    [str(entrypoint)],
    pathex=[str(base_dir)],
    binaries=[],
    datas=[(str(assets_dir), 'assets')],
    hiddenimports=[
        'pynput',
        'pynput.keyboard',
        'pynput.keyboard._darwin',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'win32gui',
        'win32con',
        'win32api',
        'win32process',
        'winsound',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SanCapture',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SanCapture',
)

app = BUNDLE(
    coll,
    name='SanCapture.app',
    icon=str(icon_file) if icon_file.exists() else None,
    bundle_identifier='com.sancapture.app',
    info_plist={
        'CFBundleName': 'SanCapture',
        'CFBundleDisplayName': 'SanCapture',
        'CFBundleIdentifier': 'com.sancapture.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 SanCapture',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSScreenCaptureUsageDescription': 'SanCapture requires screen recording permission to take screenshots of your desktop and open windows.',
        'NSDesktopFolderUsageDescription': 'SanCapture requires permission to save captured screenshots to your folders.',
        'NSAppleEventsUsageDescription': 'SanCapture uses AppleEvents to interact with capture tools.',
    },
)
