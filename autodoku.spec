# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AutoDoku portable one-file EXE
# Build with: pyinstaller autodoku.spec  (or run build.bat)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json',              '.'),
        ('ui/styles/dark_theme.qss', 'ui/styles'),
    ],
    hiddenimports=[
        # Windows / COM
        'wmi',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'win32api',
        'win32con',
        # pysnmp 6.x asyncio API
        'pysnmp',
        'pysnmp.hlapi',
        'pysnmp.hlapi.v3arch',
        'pysnmp.hlapi.v3arch.asyncio',
        'pysnmp.proto',
        'pysnmp.proto.api',
        'pysnmp.entity',
        'pysnmp.entity.rfc3413',
        'pysnmp.smi',
        'pysnmp.smi.mibs',
        'pysnmp.carrier',
        'pyasn1',
        'pyasn1.type',
        'pyasn1.codec',
        # SSH
        'paramiko',
        'cryptography',
        # Credential storage
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'keyring.backends.fail',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoDoku',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='autodoku.ico',
)
