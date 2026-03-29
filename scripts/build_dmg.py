#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能客服系统 macOS DMG 打包脚本
一键构建应用程序并打包成DMG安装包

使用方法:
  cd scripts && python build_dmg.py
  
或在项目根目录:
  python scripts/build_dmg.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


class Colors:
    """终端颜色输出"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_step(msg):
    print(f"\n{Colors.BLUE}▶ {msg}{Colors.END}")


def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def run_command(cmd, cwd=None, check=True):
    """执行shell命令"""
    print(f"  执行: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        output = result.stdout.strip()
        if output:
            print(f"  输出: {output[:500]}..." if len(output) > 500 else f"  输出: {output}")
    if result.stderr:
        stderr = result.stderr.strip()
        if stderr and "WARNING" not in stderr:
            print(f"  错误: {stderr[:500]}..." if len(stderr) > 500 else f"  错误: {stderr}")
    if check and result.returncode != 0:
        raise RuntimeError(f"命令执行失败: {cmd}")
    return result


def get_project_root():
    """获取项目根目录"""
    script_dir = Path(__file__).parent
    if script_dir.name == 'scripts':
        return script_dir.parent
    return script_dir


def clean_build():
    """清理构建目录"""
    print_step("清理构建目录...")
    
    root = get_project_root()
    
    # 使用 shell 命令清理，避免 Python 的权限问题
    subprocess.run(f"cd '{root}' && rm -rf build dist/__pycache__ 2>/dev/null", shell=True)
    subprocess.run(f"cd '{root}' && find . -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null", shell=True)
    subprocess.run(f"cd '{root}' && find . -type f -name '*.pyc' -delete 2>/dev/null", shell=True)
    
    # 保留 dist/智能客服.app 如果存在（用于 --skip-build）
    dist_dir = root / "dist"
    if dist_dir.exists():
        # 移动 .app 到临时位置
        app_path = dist_dir / "智能客服.app"
        if app_path.exists():
            subprocess.run(f"mv '{app_path}' /tmp/_backup_app 2>/dev/null", shell=True)
        subprocess.run(f"rm -rf '{dist_dir}'/* 2>/dev/null", shell=True)
        if os.path.exists("/tmp/_backup_app"):
            subprocess.run(f"mkdir -p '{dist_dir}' && mv /tmp/_backup_app '{app_path}' 2>/dev/null", shell=True)
    
    print_success("清理完成")


def build_app():
    """使用 PyInstaller 构建应用程序"""
    print_step("开始构建应用程序...")
    
    root = get_project_root()
    scripts_dir = root / "scripts"
    
    # 检查 pyinstaller
    result = run_command("pyinstaller --version", check=False)
    if result.returncode != 0:
        print_error("PyInstaller 未安装，请先运行: uv sync")
        sys.exit(1)
    
    # 使用 onedir 模式构建（更稳定）
    spec_file = scripts_dir / "app_onedir.spec"
    cmd = f"cd '{scripts_dir}' && pyinstaller '{spec_file}' --clean --noconfirm"
    run_command(cmd)
    
    # 验证构建结果
    app_path = root / "dist" / "智能客服.app"
    if not app_path.exists():
        print_error(f"构建失败: {app_path} 不存在")
        sys.exit(1)
    
    print_success(f"应用程序构建成功: {app_path}")
    
    # 显示应用信息
    app_size = get_folder_size(app_path)
    print(f"  应用大小: {app_size / 1024 / 1024:.2f} MB")
    
    return app_path


def get_folder_size(folder):
    """获取文件夹大小"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def create_dmg(app_path):
    """使用 hdiutil 创建 DMG 安装包"""
    print_step("创建 DMG 安装包...")
    
    root = get_project_root()
    dmg_name = "智能客服-1.0.0.dmg"
    dmg_path = root / "dist" / dmg_name
    volume_name = "智能客服安装"
    temp_dmg = root / "dist" / "temp.dmg"
    
    # 如果已存在，先删除
    if dmg_path.exists():
        os.remove(dmg_path)
        print_warning(f"已删除旧的 DMG: {dmg_path}")
    
    # 计算应用大小并设置 DMG 大小（应用大小 + 200MB 余量）
    app_size = get_folder_size(app_path)
    dmg_size_mb = int(app_size / 1024 / 1024) + 200
    print(f"  应用大小: {app_size / 1024 / 1024:.2f} MB")
    print(f"  DMG大小: {dmg_size_mb} MB")
    
    try:
        # 1. 创建临时 DMG
        print_step("创建临时 DMG...")
        run_command(f'hdiutil create -size {dmg_size_mb}m -fs HFS+ -volname "{volume_name}" -o "{temp_dmg}"')
        
        # 2. 挂载 DMG
        print_step("挂载 DMG...")
        result = run_command(f'hdiutil attach "{temp_dmg}"')
        mount_point = f"/Volumes/{volume_name}"
        
        # 3. 复制应用
        print_step("复制应用到 DMG...")
        run_command(f'cp -R "{app_path}" "{mount_point}/"')
        
        # 4. 创建 Applications 快捷方式
        print_step("创建 Applications 快捷方式...")
        run_command(f'ln -s /Applications "{mount_point}/Applications"', check=False)
        
        # 5. 设置 DMG 窗口样式（可选，失败不中断）
        print_step("设置窗口样式...")
        applescript = f'''
tell application "Finder"
    tell disk "{volume_name}"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {{100, 100, 740, 540}}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 100
        set position of item "智能客服.app" of container window to {{160, 240}}
        set position of item "Applications" of container window to {{480, 240}}
        close
    end tell
end tell
'''
        subprocess.run(['osascript', '-e', applescript], capture_output=True)
        
        # 6. 卸载 DMG
        print_step("卸载 DMG...")
        run_command(f'hdiutil detach "{mount_point}"')
        
        # 7. 压缩为最终 DMG
        print_step("压缩 DMG...")
        run_command(f'hdiutil convert "{temp_dmg}" -format UDZO -o "{dmg_path}"')
        
        # 8. 清理临时文件
        if temp_dmg.exists():
            os.remove(temp_dmg)
        
        print_success(f"DMG 创建成功: {dmg_path}")
        
    except Exception as e:
        # 清理
        if temp_dmg.exists():
            os.remove(temp_dmg)
        # 尝试卸载
        subprocess.run(f'hdiutil detach "/Volumes/{volume_name}" 2>/dev/null', shell=True)
        raise e
    
    if dmg_path.exists():
        dmg_size = os.path.getsize(dmg_path)
        print(f"  文件大小: {dmg_size / 1024 / 1024:.2f} MB")
        return dmg_path
    else:
        print_error("DMG 创建失败")
        sys.exit(1)


def verify_app(app_path):
    """验证应用程序"""
    print_step("验证应用程序...")
    
    # 检查 bundle 结构
    required_paths = [
        app_path / "Contents" / "Info.plist",
        app_path / "Contents" / "MacOS" / "智能客服",
    ]
    
    for path in required_paths:
        if not path.exists():
            print_error(f"缺少必要文件: {path}")
            return False
    
    print_success("应用结构验证通过")
    return True


def main():
    """主函数"""
    print(f"{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}  智能客服系统 - macOS DMG 打包工具{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}")
    
    root = get_project_root()
    
    # 检查是否在正确的目录（检查 main.py 是否存在）
    if not (root / "main.py").exists():
        print_error("请在项目根目录或 scripts 目录运行此脚本")
        sys.exit(1)
    
    print(f"项目根目录: {root}")
    
    # 检查虚拟环境
    if not (root / ".venv").exists():
        print_warning("未检测到虚拟环境，请先运行: uv venv && uv sync")
        sys.exit(1)
    
    # 解析命令行参数
    skip_clean = "--skip-clean" in sys.argv
    skip_build = "--skip-build" in sys.argv
    
    try:
        # 1. 清理构建目录
        if not skip_clean:
            clean_build()
        else:
            print_warning("跳过清理步骤")
        
        # 2. 构建应用程序
        if not skip_build:
            app_path = build_app()
        else:
            app_path = root / "dist" / "智能客服.app"
            if not app_path.exists():
                print_error(f"应用不存在: {app_path}")
                sys.exit(1)
            print_warning("跳过构建步骤，使用现有应用")
        
        # 3. 验证应用
        if not verify_app(app_path):
            print_error("应用验证失败")
            sys.exit(1)
        
        # 4. 创建 DMG
        dmg_path = create_dmg(app_path)
        
        # 完成
        print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}  打包完成！{Colors.END}")
        print(f"{Colors.GREEN}{'='*60}{Colors.END}")
        print(f"\n输出文件:")
        print(f"  应用程序: {app_path}")
        print(f"  DMG 安装包: {dmg_path}")
        print(f"\n使用说明:")
        print(f"  1. 双击 DMG 文件挂载")
        print(f"  2. 将 '智能客服' 拖到 'Applications' 文件夹")
        print(f"  3. 从启动台或应用程序文件夹启动")
        print(f"\n注意事项:")
        print(f"  - 首次启动可能需要右键点击 -> 打开")
        print(f"  - 如果提示来自未知开发者，请前往 系统设置 > 隐私与安全性 允许")
        
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print_error(f"打包失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
