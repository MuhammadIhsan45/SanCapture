# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/FIle Project Mandiri Ihsan/Screenshot App/app/main.py'],
    pathex=['D:/FIle Project Mandiri Ihsan/Screenshot App'],
    binaries=[],
    datas=[('D:/FIle Project Mandiri Ihsan/Screenshot App/assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/FIle Project Mandiri Ihsan/Screenshot App/assets/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SanCapture',
)
