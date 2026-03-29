# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('icon/', 'icon'), ('config.json', '.'), ('database/', 'database'), ('knowledge_base/', 'knowledge_base'), ('utils/', 'utils'), ('ui/', 'ui'), ('Message/', 'Message'), ('Channel/', 'Channel'), ('Agent/', 'Agent'), ('bridge/', 'bridge'), ('ai_learning/', 'ai_learning')],
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.sip', 'qfluentwidgets', 'sqlalchemy', 'sqlalchemy.dialects.sqlite', 'ai_learning.signal_collector', 'ai_learning.optimization_engine', 'ai_learning.similar_case_manager', 'utils.logger'],
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
    name='智能客服',
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
    icon=['icon/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='智能客服',
)
app = BUNDLE(
    coll,
    name='智能客服.app',
    icon='icon/icon.icns',
    bundle_identifier='com.smart-cs.app',
)
