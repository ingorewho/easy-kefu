#!/usr/bin/env python3
"""
License 生成脚本

用法：
    python scripts/generate_license.py [选项]

示例：
    # 生成 30 天试用 License
    python scripts/generate_license.py --customer "测试客户" --days 30

    # 生成指定到期日期的 License
    python scripts/generate_license.py --customer "正式客户" --expire "2025-12-31"

    # 生成限制账号数的 License
    python scripts/generate_license.py --customer "小型企业" --days 365 --max-accounts 5

    # 生成指定功能的 License
    python scripts/generate_license.py --customer "高级客户" --days 365 --features auto_reply,knowledge_base
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# 添加项目根目录和 src 目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from utils.license_manager import LicenseGenerator


def generate_license_id(customer_name: str) -> str:
    """生成 License ID"""
    date_str = datetime.now().strftime("%Y%m%d")
    # 基于客户名称和时间生成简单哈希
    hash_input = f"{customer_name}-{date_str}-{datetime.now().timestamp()}"
    hash_val = hash(hash_input) % 10000
    return f"LIC-{date_str}-{hash_val:04d}"


def main():
    parser = argparse.ArgumentParser(
        description="生成 Easy KeFu 软件 License",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s --customer "测试客户" --days 30
  %(prog)s --customer "正式客户" --expire "2025-12-31"
  %(prog)s --customer "企业版" --days 365 --max-accounts 50
        """
    )
    
    parser.add_argument(
        "--customer", "-c",
        required=True,
        help="客户名称"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="有效期天数（默认：30）"
    )
    
    parser.add_argument(
        "--expire", "-e",
        help="到期日期（格式：YYYY-MM-DD），覆盖 --days 选项"
    )
    
    parser.add_argument(
        "--max-accounts", "-m",
        type=int,
        default=999,
        help="最大账号数（默认：999，表示无限制）"
    )
    
    parser.add_argument(
        "--features", "-f",
        default="all",
        help="启用的功能列表，逗号分隔（默认：all）\n可选：auto_reply, knowledge_base, ai_learning, emotion_alert"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（默认：licenses/<customer_name>_<date>.key）"
    )
    
    parser.add_argument(
        "--plain",
        action="store_true",
        help="输出纯 JSON 格式（不 Base64 编码）"
    )
    
    parser.add_argument(
        "--key",
        help="签名密钥（高级选项）"
    )
    
    args = parser.parse_args()
    
    # 确定到期日期
    if args.expire:
        try:
            expire_date = datetime.strptime(args.expire, "%Y-%m-%d")
            expire_date_str = args.expire
        except ValueError:
            print("❌ 错误：到期日期格式错误，请使用 YYYY-MM-DD 格式")
            sys.exit(1)
    else:
        expire_date = datetime.now() + timedelta(days=args.days)
        expire_date_str = expire_date.strftime("%Y-%m-%d")
    
    # 检查日期是否已过期
    if expire_date < datetime.now():
        print("❌ 错误：到期日期不能早于今天")
        sys.exit(1)
    
    # 解析功能列表
    features = [f.strip() for f in args.features.split(",")]
    
    # 生成 License ID
    license_id = generate_license_id(args.customer)
    
    # 创建生成器
    generator = LicenseGenerator(secret_key=args.key)
    
    # 生成 License
    license_info = generator.generate_license(
        license_id=license_id,
        customer_name=args.customer,
        expire_date=expire_date_str,
        max_accounts=args.max_accounts,
        features=features
    )
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        # 创建 licenses 目录
        licenses_dir = os.path.join(project_root, "licenses")
        if not os.path.exists(licenses_dir):
            os.makedirs(licenses_dir)
        
        # 生成文件名
        safe_customer = "".join(c if c.isalnum() else "_" for c in args.customer)
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = os.path.join(licenses_dir, f"{safe_customer}_{date_str}.key")
    
    # 保存文件
    generator.save_license_file(license_info, output_path, encode_base64=not args.plain)
    
    # 计算剩余天数
    days_left = (expire_date - datetime.now()).days + 1
    
    # 打印结果
    print("\n" + "=" * 50)
    print("✅ License 生成成功！")
    print("=" * 50)
    print(f"\n📋 License 信息：")
    print(f"  • License ID: {license_info.license_id}")
    print(f"  • 客户名称: {license_info.customer_name}")
    print(f"  • 到期日期: {license_info.expire_date}")
    print(f"  • 剩余天数: {days_left} 天")
    print(f"  • 最大账号数: {license_info.max_accounts}")
    print(f"  • 功能列表: {', '.join(license_info.features)}")
    print(f"  • 签发时间: {license_info.issued_at}")
    print(f"\n📁 文件路径: {output_path}")
    print("=" * 50)
    
    # 提示使用方式
    print("\n💡 使用方式：")
    print(f"  1. 将生成的 License 文件导入系统")
    print(f"  2. 或在系统设置 > License 管理中导入")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
