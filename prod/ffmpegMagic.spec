# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\amirl\\OneDrive\\Documents\\GitHub\\Video-Editor\\src\\web_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\amirl\\OneDrive\\Documents\\GitHub\\Video-Editor\\src\\web', 'web'), ('C:\\Users\\amirl\\OneDrive\\Documents\\GitHub\\Video-Editor\\assets', 'assets'), ('C:\\Users\\amirl\\OneDrive\\Documents\\GitHub\\Video-Editor\\vendor\\ffmpeg\\win64', 'vendor/ffmpeg/win64'), ('C:\\Users\\amirl\\OneDrive\\Documents\\GitHub\\Video-Editor\\vendor\\ffmpeg\\NOTICE.txt', 'vendor/ffmpeg')],
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
    name='ffmpegMagic',
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
    icon=['C:\\Users\\amirl\\OneDrive\\Documents\\GitHub\\Video-Editor\\assets\\ffmpegMagic.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ffmpegMagic',
)
