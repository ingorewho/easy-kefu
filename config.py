"""
配置文件管理模块
获取config.json中的配置，提供配置访问接口
"""

import json
import os
import sys


def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


config_base = {
    # 原有配置
    "coze_api_base": "https://api.coze.cn",
    "coze_token": "",
    "coze_bot_id": "",
    "bot_type": "coze",  # coze | kimi | qwen
    "theme": "dark",  # light | dark
    "businessHours": {
        "start": "08:00",
        "end": "23:00"
    },

    # Kimi 配置
    "kimi_api_base": "https://api.moonshot.cn/v1",
    "kimi_api_key": "",
    "kimi_model": "kimi-k2.5",  # 可选: kimi-k2.5/k2.5-long, moonshot-v1-8k/32k/128k/auto

    # Qwen 配置
    "qwen_api_base": "https://dashscope.aliyuncs.com/api/v1",
    "qwen_api_key": "",
    "qwen_model": "qwen-turbo",  # 可选: qwen-turbo/plus/max

    # RAG 知识库配置
    "enable_rag": False,  # 是否启用知识库
    "rag_top_k": 5,  # 检索文档数量（增加到5，确保能找到产品信息）
    "rag_score_threshold": 0.5,  # 相似度阈值 (<=1: cosine相似度, >1: L2距离)

    # Web 搜索配置
    "enable_web_search_fallback": True,  # 本地无结果时是否启用 Web 搜索
    "web_search_provider": "serpapi",  # 搜索提供商: serpapi
    "serpapi_key": "",  # SerpAPI Key
    "web_search_min_confidence": 0.6,  # 知识沉淀最小置信度
    "web_search_auto_sink": True,  # 是否自动沉淀网络知识到本地

    # AI 回复风格配置
    "ai_system_prompt": "你是电商客服，回复要简短口语化，不超过20字",
    "ai_reply_max_length": 20,
    "ai_reply_style": "casual",  # casual(口语化) | formal(正式)
    "ai_reply_no_punctuation": True,
    "ai_reply_delay_min": 2,     # 最小延迟（秒）
    "ai_reply_delay_max": 10,    # 最大延迟（秒）

    # 知识库文档拆分配置
    "kb_split_mode": "ai",           # ai | simple | none
    "kb_ai_split_max_chunk_size": 800,  # AI 拆分后每块最大长度
    "kb_simple_chunk_size": 500,        # 简单拆分每块长度

    # 情绪告警配置
    "enable_telegram_alert": False,     # 是否启用 Telegram 告警
    "emotion_alert_threshold": -0.6,    # 情绪告警阈值 (-1.0 ~ 0)
    "telegram_bot_token": "",           # Telegram Bot Token
    "telegram_chat_id": "",             # 接收告警的 Chat ID
    "emotion_alert_cooldown": 300,      # 告警冷却时间 (秒)，避免刷屏
    "enable_ai_emotion_analysis": True, # 是否启用 AI 深度情绪分析
}

class Config:
    def __init__(self, config_path=None):
        """初始化配置类"""
        if config_path is None:
            # 使用用户目录存储配置文件（避免只读文件系统问题）
            if hasattr(sys, '_MEIPASS'):
                config_dir = os.path.expanduser("~/Library/Application Support/智能客服")
                os.makedirs(config_dir, exist_ok=True)
                user_config_path = os.path.join(config_dir, 'config.json')
                # 如果用户目录没有配置文件，从应用包复制默认配置
                if not os.path.exists(user_config_path):
                    default_config = get_resource_path('config.json')
                    if os.path.exists(default_config):
                        import shutil
                        shutil.copy2(default_config, user_config_path)
                config_path = user_config_path
            else:
                config_path = get_resource_path('config.json')
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"配置文件 {self.config_path} 不存在，正在创建默认配置文件")
            # 使用config_base创建配置文件
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_base, f, ensure_ascii=False, indent=4)
                print(f"已创建默认配置文件：{self.config_path}")
                return config_base.copy()
            except Exception as e:
                print(f"创建配置文件失败: {e}")
                return config_base.copy()
        except json.JSONDecodeError:
            print(f"错误: 配置文件 {self.config_path} 格式不正确")
            return config_base.copy()
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def __getitem__(self, key):
        """支持使用字典方式访问配置"""
        return self.config[key]
    
    def __contains__(self, key):
        """支持使用 in 操作符检查配置项"""
        return key in self.config
    
    def reload(self):
        """重新加载配置文件"""
        self.config = self._load_config()
        return self.config
    
    def set(self, key, value, save=False):
        """
        设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项值
            save: 是否立即保存到文件，默认为False
        """
        self.config[key] = value
        if save:
            self.save()
        return value
    
    def save(self):
        """将当前配置保存到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def update(self, config_dict, save=False):
        """
        批量更新配置
        
        Args:
            config_dict: 包含多个配置项的字典
            save: 是否立即保存到文件，默认为False
        """
        self.config.update(config_dict)
        if save:
            self.save()
        return self.config

# 创建全局配置实例
config = Config()
