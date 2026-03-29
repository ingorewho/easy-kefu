#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目结构迁移脚本
将旧版目录结构迁移到新版结构
"""

import os
import shutil
import sys

def backup_old_directories():
    """备份旧目录到 backup/"""
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)
    
    old_dirs = ['Agent', 'Channel', 'Message', 'bridge', 'database', 
                'knowledge_base', 'ai_learning', 'utils', 'ui']
    
    for dir_name in old_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            backup_path = os.path.join(backup_dir, dir_name)
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.move(dir_name, backup_path)
            print(f"✅ 已备份: {dir_name} -> backup/{dir_name}")
    
    # 备份旧文件
    old_files = ['app.py', 'config.py', 'config.json']
    for file_name in old_files:
        if os.path.exists(file_name) and os.path.isfile(file_name):
            backup_path = os.path.join(backup_dir, file_name)
            if os.path.exists(backup_path):
                os.remove(backup_path)
            shutil.move(file_name, backup_path)
            print(f"✅ 已备份: {file_name} -> backup/{file_name}")

def clean_pycache():
    """清理所有 __pycache__ 目录"""
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f"🗑️  已清理: {pycache_path}")

def main():
    print("=" * 60)
    print("智能客服系统 - 项目结构迁移工具")
    print("=" * 60)
    print()
    
    # 确认
    response = input("此操作将备份旧目录到 backup/，是否继续? (y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    print()
    print("步骤 1: 备份旧目录...")
    backup_old_directories()
    
    print()
    print("步骤 2: 清理缓存...")
    clean_pycache()
    
    print()
    print("=" * 60)
    print("✅ 迁移完成!")
    print("=" * 60)
    print()
    print("新版入口: python main.py")
    print("项目结构说明: PROJECT_STRUCTURE.md")
    print()
    print("如果出现问题，可以从 backup/ 目录恢复")

if __name__ == '__main__':
    main()
