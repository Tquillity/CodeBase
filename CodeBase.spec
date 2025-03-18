# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],  # Entry point
    pathex=['/home/digislinger/Founder/CodeBase'],  # Absolute path to your project directory
    binaries=[],
    datas=[('icon.png', '.')],  # Include icon.png if it exists
    hiddenimports=['pyperclip', 'appdirs'],  # External libraries not auto-detected
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
    a.binaries,
    a.datas,
    [],
    name='CodeBase',  # Output executable name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console (GUI mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.png'],  # Set app icon (optional, ensure icon.png exists)
)