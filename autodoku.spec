# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AutoDoku portable EXE
# Build with: pyinstaller autodoku.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json',              '.'),
        ('ui/styles/dark_theme.qss', 'ui/styles'),
    ],
    hiddenimports=[
        # Windows-specific
        'wmi',
        'win32com',
        'win32com.client',
        'win32com.server',
        'pywintypes',
        'win32api',
        # Scapy
        'scapy',
        'scapy.layers',
        'scapy.layers.l2',
        'scapy.layers.inet',
        'scapy.sendrecv',
        'scapy.arch.windows',
        # pysnmp
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
        # paramiko
        'paramiko',
        'cryptography',
        # keyring
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'keyring.backends.fail',
        # nmap
        'nmap',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,          # windowed — no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='autodoku.ico',  # uncomment and provide an .ico file to set EXE icon
)
