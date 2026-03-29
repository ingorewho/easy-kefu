"""
License 管理模块
用于验证和管理软件授权
"""

import json
import hashlib
import hmac
import base64
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from utils.logger import get_logger

# 密钥（实际使用时应更复杂，并考虑安全存储）
DEFAULT_SECRET_KEY = "EasyKeFu2024LicenseKey"


@dataclass
class LicenseInfo:
    """License 信息数据类"""
    license_id: str           # License ID
    customer_name: str        # 客户名称
    expire_date: str         # 到期日期 (YYYY-MM-DD)
    max_accounts: int        # 最大账号数
    features: list           # 功能列表
    issued_at: str           # 签发日期
    signature: str = ""      # 签名
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含签名）"""
        return {
            "license_id": self.license_id,
            "customer_name": self.customer_name,
            "expire_date": self.expire_date,
            "max_accounts": self.max_accounts,
            "features": self.features,
            "issued_at": self.issued_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseInfo':
        """从字典创建实例"""
        return cls(
            license_id=data.get("license_id", ""),
            customer_name=data.get("customer_name", ""),
            expire_date=data.get("expire_date", ""),
            max_accounts=data.get("max_accounts", 1),
            features=data.get("features", []),
            issued_at=data.get("issued_at", ""),
            signature=data.get("signature", "")
        )


class LicenseManager:
    """License 管理器"""
    
    # License 文件默认存储路径
    LICENSE_FILE_NAME = "license.key"
    
    def __init__(self, license_path: Optional[str] = None, secret_key: Optional[str] = None):
        """
        初始化 License 管理器
        
        Args:
            license_path: License 文件路径，默认为用户数据目录下的 license.key
            secret_key: 签名密钥，用于验证 License
        """
        self.logger = get_logger("LicenseManager")
        
        # 确定 License 文件路径
        if license_path is None:
            license_path = self._get_default_license_path()
        self.license_path = license_path
        
        # 设置密钥
        self.secret_key = secret_key or os.environ.get("EASYKEFU_LICENSE_KEY", DEFAULT_SECRET_KEY)
        
        # 当前 License 信息
        self._license_info: Optional[LicenseInfo] = None
        self._is_valid: bool = False
        self._error_message: str = ""
        
        # 启动时自动加载并验证
        self.load_and_verify()
    
    def _get_default_license_path(self) -> str:
        """获取默认 License 文件路径"""
        # 优先使用用户数据目录
        if hasattr(sys, '_MEIPASS'):
            # 打包后的应用使用用户目录
            base_dir = os.path.expanduser("~/Library/Application Support/智能客服")
        else:
            # 开发环境使用项目目录
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        return os.path.join(base_dir, self.LICENSE_FILE_NAME)
    
    def _generate_signature(self, license_data: Dict[str, Any]) -> str:
        """
        生成 License 签名
        
        Args:
            license_data: License 数据（不包含签名）
        
        Returns:
            签名字符串
        """
        # 将数据按key排序后序列化
        data_str = json.dumps(license_data, sort_keys=True, ensure_ascii=False)
        
        # 使用 HMAC-SHA256 生成签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            data_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # 使用 Base64 编码
        return base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    
    def _verify_signature(self, license_info: LicenseInfo) -> bool:
        """
        验证 License 签名
        
        Args:
            license_info: License 信息
        
        Returns:
            签名是否有效
        """
        data_dict = license_info.to_dict()
        expected_signature = self._generate_signature(data_dict)
        
        # 使用 constant-time 比较防止时序攻击
        return hmac.compare_digest(expected_signature, license_info.signature)
    
    def verify_license(self, license_info: LicenseInfo) -> tuple[bool, str]:
        """
        验证 License 是否有效
        
        Args:
            license_info: License 信息
        
        Returns:
            (是否有效, 错误信息)
        """
        # 1. 验证签名
        if not license_info.signature:
            return False, "License 签名缺失"
        
        if not self._verify_signature(license_info):
            return False, "License 签名无效，文件可能已被篡改"
        
        # 2. 验证到期日期
        try:
            expire_date = datetime.strptime(license_info.expire_date, "%Y-%m-%d")
        except ValueError:
            return False, "License 到期日期格式错误"
        
        # 设置到期时间为当天结束
        expire_date = expire_date.replace(hour=23, minute=59, second=59)
        
        if datetime.now() > expire_date:
            return False, f"License 已过期（有效期至：{license_info.expire_date}）"
        
        # 3. 验证其他字段
        if not license_info.license_id:
            return False, "License ID 无效"
        
        if license_info.max_accounts < 1:
            return False, "账号数限制无效"
        
        return True, "License 验证通过"
    
    def load_license_file(self, file_path: str) -> tuple[bool, str]:
        """
        从文件加载 License
        
        Args:
            file_path: License 文件路径
        
        Returns:
            (是否成功, 错误信息)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"License 文件不存在: {file_path}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 尝试解析 JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 可能进行了 Base64 编码
                try:
                    decoded = base64.urlsafe_b64decode(content + '=' * (4 - len(content) % 4))
                    data = json.loads(decoded.decode('utf-8'))
                except Exception:
                    return False, "License 文件格式错误"
            
            self._license_info = LicenseInfo.from_dict(data)
            return True, "License 文件加载成功"
            
        except Exception as e:
            return False, f"加载 License 文件失败: {str(e)}"
    
    def load_and_verify(self) -> bool:
        """
        加载并验证 License
        
        Returns:
            License 是否有效
        """
        success, message = self.load_license_file(self.license_path)
        
        if not success:
            self._is_valid = False
            self._error_message = message
            self.logger.warning(f"License 加载失败: {message}")
            return False
        
        # 验证 License
        is_valid, error_msg = self.verify_license(self._license_info)
        self._is_valid = is_valid
        self._error_message = error_msg
        
        if is_valid:
            self.logger.info(f"License 验证通过，有效期至: {self._license_info.expire_date}")
        else:
            self.logger.warning(f"License 验证失败: {error_msg}")
        
        return is_valid
    
    def import_license(self, source_path: str) -> tuple[bool, str]:
        """
        导入 License 文件
        
        Args:
            source_path: 源 License 文件路径
        
        Returns:
            (是否成功, 信息)
        """
        # 1. 加载源文件
        success, message = self.load_license_file(source_path)
        if not success:
            return False, message
        
        # 2. 验证 License
        is_valid, error_msg = self.verify_license(self._license_info)
        if not is_valid:
            return False, f"License 验证失败: {error_msg}"
        
        # 3. 确保目标目录存在
        target_dir = os.path.dirname(self.license_path)
        if target_dir and not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except Exception as e:
                return False, f"创建目录失败: {str(e)}"
        
        # 4. 复制 License 文件到目标位置
        try:
            import shutil
            shutil.copy2(source_path, self.license_path)
            self._is_valid = True
            self._error_message = ""
            
            # 计算剩余天数
            expire_date = datetime.strptime(self._license_info.expire_date, "%Y-%m-%d")
            days_left = (expire_date - datetime.now()).days + 1
            
            return True, f"License 导入成功！有效期至: {self._license_info.expire_date}（剩余 {days_left} 天）"
            
        except Exception as e:
            return False, f"复制 License 文件失败: {str(e)}"
    
    def is_valid(self) -> bool:
        """检查 License 是否有效"""
        return self._is_valid
    
    def get_error_message(self) -> str:
        """获取错误信息"""
        return self._error_message
    
    def get_license_info(self) -> Optional[LicenseInfo]:
        """获取当前 License 信息"""
        return self._license_info
    
    def get_status_text(self) -> str:
        """获取 License 状态文本"""
        if self._is_valid and self._license_info:
            expire_date = datetime.strptime(self._license_info.expire_date, "%Y-%m-%d")
            days_left = (expire_date - datetime.now()).days + 1
            return f"✅ 已授权 | 有效期至: {self._license_info.expire_date}（剩余 {days_left} 天）"
        else:
            return f"❌ 未授权 | {self._error_message}"
    
    def get_remaining_days(self) -> int:
        """获取剩余有效天数"""
        if not self._is_valid or not self._license_info:
            return 0
        
        try:
            expire_date = datetime.strptime(self._license_info.expire_date, "%Y-%m-%d")
            days_left = (expire_date - datetime.now()).days + 1
            return max(0, days_left)
        except ValueError:
            return 0
    
    def is_feature_enabled(self, feature: str) -> bool:
        """检查功能是否启用"""
        if not self._is_valid or not self._license_info:
            return False
        
        # "all" 表示启用所有功能
        if "all" in self._license_info.features:
            return True
        
        return feature in self._license_info.features
    
    def check_account_limit(self, current_count: int) -> tuple[bool, int]:
        """
        检查账号数量是否超出限制
        
        Args:
            current_count: 当前账号数量
        
        Returns:
            (是否允许, 最大允许数量)
        """
        if not self._is_valid or not self._license_info:
            return False, 0
        
        max_accounts = self._license_info.max_accounts
        return current_count < max_accounts, max_accounts


class LicenseGenerator:
    """License 生成器（用于生成新的 License）"""
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        初始化 License 生成器
        
        Args:
            secret_key: 签名密钥
        """
        self.secret_key = secret_key or DEFAULT_SECRET_KEY
    
    def generate_license(
        self,
        license_id: str,
        customer_name: str,
        expire_date: str,
        max_accounts: int = 999,
        features: Optional[list] = None
    ) -> LicenseInfo:
        """
        生成新的 License
        
        Args:
            license_id: License ID（建议格式：CUST-YYYYMMDD-XXXX）
            customer_name: 客户名称
            expire_date: 到期日期 (YYYY-MM-DD)
            max_accounts: 最大账号数
            features: 功能列表，默认启用所有功能
        
        Returns:
            LicenseInfo 对象
        """
        if features is None:
            features = ["all"]  # 默认启用所有功能
        
        # 创建 License 信息
        license_info = LicenseInfo(
            license_id=license_id,
            customer_name=customer_name,
            expire_date=expire_date,
            max_accounts=max_accounts,
            features=features,
            issued_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 生成签名
        data_dict = license_info.to_dict()
        signature = self._generate_signature(data_dict)
        license_info.signature = signature
        
        return license_info
    
    def _generate_signature(self, license_data: Dict[str, Any]) -> str:
        """生成签名"""
        data_str = json.dumps(license_data, sort_keys=True, ensure_ascii=False)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            data_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    
    def save_license_file(self, license_info: LicenseInfo, output_path: str, encode_base64: bool = True):
        """
        保存 License 到文件
        
        Args:
            license_info: License 信息
            output_path: 输出文件路径
            encode_base64: 是否使用 Base64 编码
        """
        # 创建目录
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 准备数据
        data = license_info.to_dict()
        data["signature"] = license_info.signature
        
        # 序列化
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        if encode_base64:
            # Base64 编码
            content = base64.urlsafe_b64encode(json_str.encode('utf-8')).decode('utf-8')
        else:
            # 纯 JSON
            content = json_str
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path


# 全局 License 管理器实例
_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """获取全局 License 管理器实例"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


def init_license_manager(license_path: Optional[str] = None, secret_key: Optional[str] = None) -> LicenseManager:
    """初始化 License 管理器"""
    global _license_manager
    _license_manager = LicenseManager(license_path, secret_key)
    return _license_manager
