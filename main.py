#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能客服系统 - 主入口文件
"""

import sys
import os

# 添加项目根目录和src目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# 导入配置
from config import config
from utils.logger import get_logger

# 延迟导入PyQt和其他大型库，避免启动过慢
def main():
    """应用程序主函数"""
    import ctypes
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from ui.main_ui import MainWindow
    from qfluentwidgets import setTheme, Theme
    
    logger = get_logger("App")
    logger.info("应用程序启动...")
    
    # 初始化 License 管理器
    from utils.license_manager import init_license_manager
    license_manager = init_license_manager()
    
    # 检查 License 状态
    if not license_manager.is_valid():
        logger.warning(f"License 无效: {license_manager.get_error_message()}")
        # 不阻止启动，但会在设置界面提示用户导入 License
    else:
        license_info = license_manager.get_license_info()
        logger.info(f"License 验证通过，客户: {license_info.customer_name}, 到期: {license_info.expire_date}")

    # 启用高分屏支持
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("智能客服")
    app.setOrganizationName("smart-cs")

    # 加载主题配置
    theme_mode = config.get("theme", "light")
    if theme_mode == "dark":
        setTheme(Theme.DARK)
    else:
        setTheme(Theme.LIGHT)
    
    # 在Windows上设置AppUserModelID
    try:
        if sys.platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.smart-cs.app")
    except Exception as e:
        logger.warning(f"设置AppUserModelID失败: {e}")

    # 初始化并显示主窗口
    window = MainWindow()

    # macOS: 确保窗口正确显示并激活
    if sys.platform == "darwin":
        window.show()
        window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
        window.setWindowState(window.windowState() | Qt.WindowState.WindowActive)
        window.raise_()
        window.activateWindow()
        QApplication.processEvents()
        logger.info("窗口已显示")
    else:
        window.show()
        window.raise_()
        window.activateWindow()

    # 运行事件循环
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
