# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件列表 - 更新为新的 src/ 结构
datas = [
    ('../icon/', 'icon'),
    ('../config.json', '.'),
    ('../database/', 'database'),
    ('../src/', 'src'),
    ('../resources/', 'resources'),
]

hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    'qfluentwidgets',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'email',
    'email.parser',
    'email.message',
    'email.policy',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'openai',
    'dashscope',
    'cozepy',
    'chromadb',
    'chromadb.telemetry.product.posthog',
    'chromadb.config',
    'chromadb.api',
    'chromadb.api.rust',
    'chromadb.db',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.segment',
    'chromadb.segment.impl',
    'chromadb.segment.impl.manager',
    'chromadb.segment.impl.manager.local',
    'chromadb.utils',
    'chromadb.utils.embedding_functions',
    'chromadb.telemetry',
    'chromadb.ingest',
    'chromadb.execution',
    'sentence_transformers',
    'pypdf',
    'docx',
    'openpyxl',
    'requests',
    'urllib3',
    'certifi',
    'websockets',
    'flask',
    'flask_cors',
    'config',
    'config.config',
    'src.core.agents',
    'src.core.agents.CozeAgent',
    'src.core.agents.KimiAgent',
    'src.core.agents.QwenAgent',
    'src.core.channels',
    'src.core.channels.pinduoduo',
    'src.core.messages',
    'src.core.bridge',
    'src.services.knowledge',
    'src.services.learning',
    'src.ui',
    'src.ui.chat_history',
    'src.db',
    'src.utils',
    'posthog',
]

excludes = [
    'tkinter',
    'unittest',
    'doctest',
    'tests',
    'pytest',
    'nose',
]

a = Analysis(
    ['../main.py'],  # 使用新的 main.py 作为入口
    pathex=['..'],   # 添加父目录到路径，以便导入 src
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

# 使用 onedir 模式创建.app bundle (PyInstaller 6.x 格式)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir 模式需要这个
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
    icon='../icon/icon.icns',
)

# 收集所有二进制文件和数据文件
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='智能客服'
)

# 创建 macOS app bundle
app = BUNDLE(
    coll,
    name='智能客服.app',
    icon='../icon/icon.icns',
    bundle_identifier='com.smart-cs.app',
    info_plist={
        'CFBundleName': '智能客服',
        'CFBundleDisplayName': '智能客服',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleExecutable': '智能客服',
        'NSHumanReadableCopyright': 'Copyright © 2026',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.15',
        'NSPrincipalClass': 'NSApplication',
        'LSBackgroundOnly': False,
        'LSUIElement': False,
        'CFBundleSupportedPlatforms': ['MacOSX'],
    },
)
