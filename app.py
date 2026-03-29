import sys
import ctypes
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ui.main_ui import MainWindow
from utils.logger import get_logger
from config import config
from qfluentwidgets import setTheme, Theme

def main():
    """ 应用程序主函数 """
    logger = get_logger("App")
    logger.info("应用程序启动...")

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
    
    # 在Windows上设置AppUserModelID，以确保任务栏图标正确显示
    try:
        if sys.platform == "win32":
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("my.company.my.product.version")
    except Exception as e:
        logger.warning(f"设置AppUserModelID失败: {e}")

    # 初始化并显示主窗口
    window = MainWindow()

    # macOS: 确保窗口正确显示并激活
    if sys.platform == "darwin":
        # 先显示窗口
        window.show()
        # 确保窗口不被最小化
        window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
        window.setWindowState(window.windowState() | Qt.WindowState.WindowActive)
        # 提升到最前
        window.raise_()
        window.activateWindow()
        # 强制刷新事件
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
