# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件列表
datas = [
    ('icon/', 'icon'),
    ('config.json', '.'),
    ('database/', 'database'),
    ('knowledge_base/', 'knowledge_base'),
    ('utils/', 'utils'),
    ('ui/', 'ui'),
    ('Message/', 'Message'),
    ('Channel/', 'Channel'),
    ('Agent/', 'Agent'),
    ('bridge/', 'bridge'),
    ('ai_learning/', 'ai_learning'),
]

hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'qfluentwidgets',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'openai',
    'dashscope',
    'cozepy',
    'chromadb',
    'sentence_transformers',
    'pypdf',
    'docx',
    'openpyxl',
    'requests',
    'websockets',
    'flask',
    'flask_cors',
    'ai_learning.signal_collector',
    'ai_learning.optimization_engine',
    'ai_learning.similar_case_manager',
    'utils.logger',
    'utils.emotion_analyzer',
    'utils.telegram_notifier',
    'Cocoa',
]

excludes = [
    'tkinter',
    'unittest',
    'email',
    'http',
    'doctest',
    'tests',
    'pytest',
    'nose',
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='智能客服',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon/icon.icns',
)

# 移除 BUNDLE，只使用 onedir 模式
# onefile 模式与 macOS .app bundle 不兼容
