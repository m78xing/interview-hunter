"""
配置管理模块
"""
import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# 默认公司列表（可配置）
DEFAULT_COMPANIES = [
    "字节跳动", "腾讯", "阿里巴巴", "百度", "小米", "美团", "京东",
    "拼多多", "快手", "网易", "蚂蚁", "华为", "滴滴", "小红书", "哔哩哔哩"
]

# 默认岗位列表（可配置）
DEFAULT_POSITIONS = [
    "算法工程师", "后端开发", "前端开发", "全栈", "测试开发",
    "运维开发", "数据工程师", "机器学习", "深度学习"
]


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    api_key: str = ""  # 从环境变量 DEEPSEEK_API_KEY 读取
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"


@dataclass
class StorageConfig:
    db_path: str = "./memory/interview_hunter.db"
    chroma_path: str = "./memory/chroma_db"
    user_profile_path: str = "./memory/user_profile.json"
    learning_history_path: str = "./memory/learning_history.json"


@dataclass
class CrawlerConfig:
    skills_dir: str = "./skills"  # 使用相对于项目根目录的绝对路径
    keywords: List[str] = field(default_factory=lambda: ["大模型 面经", "LLM 面经"])
    max_per_keyword: int = 5
    days_range: int = 7


@dataclass
class HeartbeatConfig:
    scheduled_times: List[str] = field(default_factory=lambda: ["08:00"])
    cooldown_on_error: int = 60


@dataclass
class RecommendationWeights:
    retrievability: float = 0.35
    weakness: float = 0.30
    hotness: float = 0.20
    dependency: float = 0.15


@dataclass
class RecommendationConfig:
    weights: RecommendationWeights = field(default_factory=RecommendationWeights)
    diversity_penalty_coef: float = 0.5
    recently_shown_tags_length: int = 3
    tiebreaker: List[str] = field(default_factory=lambda: ["created_at ASC", "mastery_level ASC"])


@dataclass
class AuditConfig:
    consecutive_errors: int = 5
    error_rate: float = 0.6
    daily_batch: bool = True


@dataclass
class UserConfig:
    target_company: str = "字节跳动"
    target_position: str = "算法岗"
    daily_goal: int = 20


@dataclass
class AnalyzerConfig:
    """分析器配置"""
    companies: List[str] = field(default_factory=lambda: DEFAULT_COMPANIES)
    positions: List[str] = field(default_factory=lambda: DEFAULT_POSITIONS)
    duplicate_threshold: float = 0.92
    similar_threshold: float = 0.75


@dataclass
class EmbeddingConfig:
    provider: str = "mock"
    model: str = "mock"
    api_key: str = ""
    base_url: str = ""
    dimension: int = 384


@dataclass
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_name: str = "InterviewHunter"
    to: str = ""


@dataclass
class Settings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    recommendation: RecommendationConfig = field(default_factory=RecommendationConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    user: UserConfig = field(default_factory=UserConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    email: EmailConfig = field(default_factory=EmailConfig)


def _get_project_root() -> Path:
    """获取项目根目录"""
    # 假设 config.yaml 在项目根目录
    return Path(__file__).parent.parent.parent


def _resolve_path(path: str) -> str:
    """解析路径，转换为绝对路径"""
    path_obj = Path(path)
    if path_obj.is_absolute():
        return str(path_obj)
    # 相对于项目根目录
    return str(_get_project_root() / path_obj)


def _load_env_file(env_path: Optional[Path] = None) -> Dict[str, str]:
    """加载 .env 文件"""
    if env_path is None:
        env_path = _get_project_root() / ".env"
    
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def load_settings(config_path: Optional[str | Path] = None, use_env: bool = True) -> Settings:
    """加载配置
    
    优先级：环境变量 > .env 文件 > config.yaml > 默认值
    
    Args:
        config_path: 配置文件路径，默认使用项目根目录的 config.yaml
        use_env: 是否使用环境变量覆盖配置
    """
    if config_path is None:
        config_path_obj = _get_project_root() / "config.yaml"
    else:
        config_path_obj = Path(config_path)

    settings = Settings()

    # 1. 加载 .env 文件
    env_vars = {}
    if use_env:
        env_vars = _load_env_file()

    # 2. 从环境变量覆盖
    env_api_key = os.getenv('DEEPSEEK_API_KEY') or env_vars.get('DEEPSEEK_API_KEY', '')
    if env_api_key:
        settings.llm.api_key = env_api_key

    # 3. 加载 config.yaml
    if config_path_obj.exists():
        with open(config_path_obj, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f) or {}

        # 递归解析嵌套配置
        def parse_config(data, cls):
            if isinstance(data, dict):
                kwargs = {}
                for key, value in data.items():
                    if hasattr(cls, '__dataclass_fields__') and key in cls.__dataclass_fields__:
                        field_type = cls.__dataclass_fields__[key].type
                        if hasattr(field_type, '__dataclass_fields__'):
                            kwargs[key] = parse_config(value, field_type)
                        else:
                            kwargs[key] = value
                return cls(**kwargs)
            return data

        # 解析各个配置块
        if 'llm' in config_dict:
            llm_cfg = parse_config(config_dict['llm'], LLMConfig)
            # 保留之前通过环境变量设置的 api_key
            saved_api_key = settings.llm.api_key
            settings.llm = llm_cfg
            if saved_api_key:
                settings.llm.api_key = saved_api_key
        
        if 'storage' in config_dict:
            settings.storage = parse_config(config_dict['storage'], StorageConfig)
        if 'crawler' in config_dict:
            crawler_cfg = parse_config(config_dict['crawler'], CrawlerConfig)
            # 解析 skills_dir 为绝对路径
            crawler_cfg.skills_dir = _resolve_path(crawler_cfg.skills_dir)
            settings.crawler = crawler_cfg
        if 'heartbeat' in config_dict:
            settings.heartbeat = parse_config(config_dict['heartbeat'], HeartbeatConfig)
        if 'recommendation' in config_dict:
            rec = config_dict['recommendation']
            if 'weights' in rec:
                settings.recommendation.weights = parse_config(rec['weights'], RecommendationWeights)
            settings.recommendation.diversity_penalty_coef = rec.get('diversity_penalty_coef', 0.5)
            settings.recommendation.recently_shown_tags_length = rec.get('recently_shown_tags_length', 3)
            settings.recommendation.tiebreaker = rec.get('tiebreaker', ["created_at ASC", "mastery_level ASC"])
        if 'audit' in config_dict:
            settings.audit = parse_config(config_dict['audit'], AuditConfig)
        if 'user' in config_dict:
            settings.user = parse_config(config_dict['user'], UserConfig)
        if 'analyzer' in config_dict:
            analyzer_cfg = parse_config(config_dict['analyzer'], AnalyzerConfig)
            settings.analyzer = analyzer_cfg
        if 'embedding' in config_dict:
            settings.embedding = parse_config(config_dict['embedding'], EmbeddingConfig)
        if 'email' in config_dict:
            settings.email = parse_config(config_dict['email'], EmailConfig)

    return settings


# 向后兼容：保留全局单例，但标记为废弃
import warnings

def __getattr__(name: str):
    if name == 'settings':
        warnings.warn(
            "直接访问 settings 全局单例已废弃，请在应用中显式调用 load_settings()",
            DeprecationWarning,
            stacklevel=2
        )
        return _lazy_settings

_lazy_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """获取全局设置实例（延迟加载，向后兼容）"""
    global _lazy_settings
    if _lazy_settings is None:
        _lazy_settings = load_settings()
    return _lazy_settings
