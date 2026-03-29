# DMG 构建配置 - dmgbuild 使用
# 使用：python build_dmg.py 或 dmgbuild -s dmg_config.py "智能客服" dist/智能客服.dmg

from __future__ import unicode_literals
import os

# ========== 基本配置 ==========

# 卷名（挂载后显示的名称）
volume_name = '智能客服安装'

# 应用路径
app_path = 'dist/智能客服.app'

# 输出 DMG 文件名
output_name = '智能客服-1.0.0.dmg'

# ========== 窗口外观 ==========

# 窗口大小 (宽, 高)
window_rect = ((100, 100), (640, 480))

# 图标大小
icon_size = 100

# 文字大小
text_size = 12

# 图标排列方式
show_icon_preview = True
show_statusbar = False

# 网格间距
grid_spacing = 100

# ========== 文件位置 ==========

# 应用图标位置
app_position = (160, 240)

# Applications 文件夹快捷方式位置
applications_position = (480, 240)

positions = {
    '智能客服.app': app_position,
    'Applications': applications_position,
}

# ========== 背景设置 ==========

# 使用内置箭头背景（也可以指定图片路径）
# background = 'builtin-arrow'

# 或者使用自定义背景图片（推荐尺寸 640x480）
# background = 'docs/dmg_background.png'

# 使用纯色背景 + 内置箭头
background = 'builtin-arrow'

# ========== 图标设置 ==========

# 应用图标（已包含在 app bundle 中，这里不需要重复设置）
# icon = 'icon/icon.icns'

# ========== DMG 格式 ==========

# 文件系统格式
format = 'UDZO'  # 压缩格式，减小体积

# 压缩级别 (0-9)
compression_level = 9

# ========== 权限设置 ==========

# 挂载时的权限
permissions = 'staff'

# ========== 高级选项 ==========

# 是否显示许可证协议
show_license = False

# 代码签名（可选）
# codesign_identity = 'Developer ID Application: Your Name'

# ========== 自定义设置 ==========

def on_finished_dmg(dmg_path):
    """DMG 创建完成后的回调函数"""
    print(f"DMG 已创建: {dmg_path}")
    
    # 获取文件大小
    size = os.path.getsize(dmg_path)
    print(f"文件大小: {size / 1024 / 1024:.2f} MB")


# 额外的文件/文件夹（会被复制到 DMG 根目录）
# files = [
#     ('README.md', 'README.txt'),
# ]

# 创建符号链接
# symlinks = {
#     'Applications': '/Applications',
# }

# ========== 窗口视图设置 ==========

# Finder 窗口视图模式: 'icon-view', 'list-view', 'column-view', 'cover-flow'
view = 'icon-view'

# 图标视图设置
arrange_by = None  # 'name', 'date-modified', etc.
label_pos = 'bottom'  # 'bottom' 或 'right'
