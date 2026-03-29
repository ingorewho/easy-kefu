"""
数据库模块初始化文件

此模块导出数据库管理器实例，确保整个应用程序使用同一个实例
"""

import os
import sys
from db.db_manager import DatabaseManager


def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# 导出数据库管理器实例（使用用户目录存储数据）
def get_db_path():
    """获取数据库文件路径（使用用户目录）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后，使用用户目录
        db_dir = os.path.expanduser("~/Library/Application Support/智能客服/database")
    else:
        # 开发环境，使用项目目录
        db_dir = get_resource_path('database')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'channel_shop.db')

db_path = get_db_path()
db_manager = DatabaseManager(db_path=db_path) 