# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file pro WageSlave System
# Použití: pyinstaller wageslave.spec

import os
block_cipher = None

a = Analysis(
    ['wageslave.pyw'],
    pathex=[],
    binaries=[],
    datas=[
        ('img/icon', 'img/icon'),       # .ico varianty log
        ('img/svg',  'img/svg'),        # .svg varianty log
        ('tray.py',  '.'),
        ('config.py', '.'),
        ('database.py', '.'),
        ('calculator.py', '.'),
        ('utils.py', '.'),
        ('eventlog.py', '.'),
    ],
    hiddenimports=[
        'pystray',
        'pystray._win32',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageTk',
        'PIL._tkinter_finder',
        'win32evtlog',
        'win32api',
        'win32con',
        'resvg_py',
        'resvg_py.resvg_py',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'cairosvg',
        'cairocffi',
        'svglib',
        'reportlab',
    ],
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
    name='WageSlave',
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
    icon='img/icon/money.ico',          # ikona .exe souboru = money varianta
    version_file=None,
)
