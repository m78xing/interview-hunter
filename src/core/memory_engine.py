"""
Memory Engine - 多维记忆模型，支持维度权重、衰减、跨会话记忆
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum


class MemoryDimension(Enum):
    """记忆维度枚举"""
    RECENCY = "recency"
    FREQUENCY = "frequency"
    DIFFICULTY = "difficulty"
    FATIGUE = "fatigue"
    MOOD = "mood"
    TIME_OF_DAY = "time_of_day"
    TOPIC_IMPORTANCE = "topic_importance"
    WEAK_TAGS = "weak_tags"


@dataclass
class MemoryEntry:
    """单条记忆条目"""
    id: str
    session_id: str
    card_id: str
    dimension: str
    value: Any
    timestamp: str
    decay: float = 1.0
    source: str = "user"
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryEntry':
        return cls(**data)


@dataclass
class MemoryProfile:
    """记忆配置文件 - 管理维度权重与衰减策略"""
    session_id: str
    weights: Dict[str, float] = field(default_factory=lambda: {
        MemoryDimension.RECENCY.value: 0.25,
        MemoryDimension.FREQUENCY.value: 0.20,
        MemoryDimension.DIFFICULTY.value: 0.20,
        MemoryDimension.FATIGUE.value: 0.15,
        MemoryDimension.MOOD.value: 0.10,
        MemoryDimension.TIME_OF_DAY.value: 0.05,
        MemoryDimension.TOPIC_IMPORTANCE.value: 0.03,
        MemoryDimension.WEAK_TAGS.value: 0.02
    })
    decay_rate: float = 0.95
    decay_interval_days: int = 1
    sharing_policy: str = "session_only"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryProfile':
        return cls(**data)


class MemoryEngine:
    """记忆引擎 - 管理多维记忆、衰减、跨会话记忆"""
    
    def __init__(self, storage_dir: str = "./memory/engine"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.entries: Dict[str, List[MemoryEntry]] = {}
        self.profiles: Dict[str, MemoryProfile] = {}
        self._load_all_data()
    
    def _load_all_data(self) -> None:
        """从磁盘加载所有记忆数据"""
        entries_dir = self.storage_dir / "entries"
        profiles_dir = self.storage_dir / "profiles"
        
        if entries_dir.exists():
            for entry_file in entries_dir.glob("*.json"):
                try:
                    with open(entry_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        session_id = data.get('session_id')
                        if session_id not in self.entries:
                            self.entries[session_id] = []
                        self.entries[session_id].append(MemoryEntry.from_dict(data))
                except Exception as e:
                    self.logger.warning(f"Failed to load entry {entry_file}: {e}")
        
        if profiles_dir.exists():
            for profile_file in profiles_dir.glob("*.json"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        session_id = data.get('session_id')
                        self.profiles[session_id] = MemoryProfile.from_dict(data)
                except Exception as e:
                    self.logger.warning(f"Failed to load profile {profile_file}: {e}")
    
    def _save_entry(self, entry: MemoryEntry) -> None:
        """保存单条记忆条目"""
        entries_dir = self.storage_dir / "entries"
        entries_dir.mkdir(parents=True, exist_ok=True)
        
        entry_file = entries_dir / f"{entry.id}.json"
        try:
            with open(entry_file, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save entry {entry_file}: {e}")
    
    def _save_profile(self, profile: MemoryProfile) -> None:
        """保存记忆配置"""
        profiles_dir = self.storage_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        
        profile_file = profiles_dir / f"{profile.session_id}.json"
        try:
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save profile {profile_file}: {e}")
    
    def _get_or_create_profile(self, session_id: str) -> MemoryProfile:
        """获取或创建记忆配置"""
        if session_id not in self.profiles:
            self.profiles[session_id] = MemoryProfile(session_id=session_id)
            self._save_profile(self.profiles[session_id])
        return self.profiles[session_id]
    
    def _apply_decay(self, entry: MemoryEntry, profile: MemoryProfile) -> float:
        """应用衰减函数，返回衰减后的值"""
        entry_time = datetime.fromisoformat(entry.timestamp)
        now = datetime.now()
        days_elapsed = (now - entry_time).days
        
        decay_factor = profile.decay_rate ** (days_elapsed / profile.decay_interval_days)
        return entry.value * decay_factor if isinstance(entry.value, (int, float)) else entry.value
    
    def update_memory(self, session_id: str, card_id: str, dimension: str, 
                     value: Any, weight: float = 1.0, source: str = "user") -> None:
        """更新记忆条目"""
        profile = self._get_or_create_profile(session_id)
        
        entry_id = f"{session_id}_{card_id}_{dimension}_{datetime.now().timestamp()}"
        entry = MemoryEntry(
            id=entry_id,
            session_id=session_id,
            card_id=card_id,
            dimension=dimension,
            value=value,
            timestamp=datetime.now().isoformat(),
            decay=1.0,
            source=source,
            confidence=weight
        )
        
        if session_id not in self.entries:
            self.entries[session_id] = []
        
        self.entries[session_id].append(entry)
        self._save_entry(entry)
        self.logger.info(f"Memory updated: session={session_id}, card={card_id}, dimension={dimension}")
    
    def get_memory(self, session_id: str, card_id: Optional[str] = None) -> List[MemoryEntry]:
        """获取记忆条目"""
        if session_id not in self.entries:
            return []
        
        entries = self.entries[session_id]
        if card_id:
            entries = [e for e in entries if e.card_id == card_id]
        
        return entries
    
    def get_memory_by_dimension(self, session_id: str, dimension: str) -> List[MemoryEntry]:
        """按维度获取记忆"""
        if session_id not in self.entries:
            return []
        
        return [e for e in self.entries[session_id] if e.dimension == dimension]
    
    def summarize_memory(self, session_id: str) -> dict:
        """生成记忆摘要"""
        profile = self._get_or_create_profile(session_id)
        entries = self.get_memory(session_id)
        
        summary = {
            'session_id': session_id,
            'total_entries': len(entries),
            'dimensions': {},
            'profile': profile.to_dict()
        }
        
        for dimension in MemoryDimension:
            dim_entries = [e for e in entries if e.dimension == dimension.value]
            if dim_entries:
                summary['dimensions'][dimension.value] = {
                    'count': len(dim_entries),
                    'latest': dim_entries[-1].to_dict(),
                    'weight': profile.weights.get(dimension.value, 0)
                }
        
        return summary
    
    def export_memory(self, session_id: str) -> dict:
        """导出记忆数据"""
        entries = self.get_memory(session_id)
        profile = self.profiles.get(session_id)
        
        return {
            'session_id': session_id,
            'entries': [e.to_dict() for e in entries],
            'profile': profile.to_dict() if profile else None,
            'exported_at': datetime.now().isoformat()
        }
    
    def import_memory(self, session_id: str, data: dict) -> None:
        """导入记忆数据"""
        if session_id not in self.entries:
            self.entries[session_id] = []
        
        for entry_data in data.get('entries', []):
            entry = MemoryEntry.from_dict(entry_data)
            self.entries[session_id].append(entry)
            self._save_entry(entry)
        
        if data.get('profile'):
            profile = MemoryProfile.from_dict(data['profile'])
            self.profiles[session_id] = profile
            self._save_profile(profile)
        
        self.logger.info(f"Memory imported for session {session_id}")
    
    def consolidate_memory(self, session_id: str, keep_latest_n: int = 100) -> None:
        """合并记忆 - 保留最近的 N 条记忆，删除旧的"""
        if session_id not in self.entries:
            return
        
        entries = self.entries[session_id]
        if len(entries) > keep_latest_n:
            self.entries[session_id] = entries[-keep_latest_n:]
            self.logger.info(f"Memory consolidated for session {session_id}, kept {keep_latest_n}")
    
    def get_memory_weights(self, session_id: str) -> Dict[str, float]:
        """获取记忆维度权重"""
        profile = self._get_or_create_profile(session_id)
        return profile.weights
    
    def set_memory_weights(self, session_id: str, weights: Dict[str, float]) -> None:
        """设置记忆维度权重"""
        profile = self._get_or_create_profile(session_id)
        profile.weights.update(weights)
        self._save_profile(profile)
        self.logger.info(f"Memory weights updated for session {session_id}")
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return list(self.entries.keys())
    
    def delete_session(self, session_id: str) -> None:
        """删除会话的所有记忆"""
        if session_id in self.entries:
            del self.entries[session_id]
        if session_id in self.profiles:
            del self.profiles[session_id]
        self.logger.info(f"Session deleted: {session_id}")
