# -*- mode: python ; coding: utf-8 -*-
import os

# Resolve paths relative to this spec file so the build works from any cwd.
spec_dir = os.path.dirname(os.path.abspath(SPEC))
icon_path = os.path.join(spec_dir, 'installer', 'assets', 'aoj_icon.ico')


a = Analysis(
    ['backend\\desktop_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend/dist', 'frontend/dist')],
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
    a.binaries,
    a.datas,
    [],
    name='AOJ_Command_OS_Desktop',
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
    icon=icon_path if os.path.exists(icon_path) else None,
    version_info={
        'FileVersion': (1, 0, 0, 0),
        'ProductVersion': (1, 0, 0, 0),
        'CompanyName': 'Airsoft Online Japan',
        'FileDescription': 'AOJ Command OS Desktop',
        'ProductName': 'AOJ Command OS',
        'LegalCopyright': 'Airsoft Online Japan — is Nineteen',
        'OriginalFilename': 'AOJ_Command_OS_Desktop.exe',
    },
)
