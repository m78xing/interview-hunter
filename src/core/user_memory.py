"""
User Long-term Memory Module
"""
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class UserPreference:
    companies: List[str] = field(default_factory=list)
    positions: List[str] = field(default_factory=list)
    difficulties: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class LearningStats:
    total_learned: int = 0
    total_correct: int = 0
    total_errors: int = 0
    streak_days: int = 0
    last_learned_at: str = ""
    weak_tags: List[str] = field(default_factory=list)


@dataclass
class CrawlStrategy:
    priority_companies: List[str] = field(default_factory=list)
    priority_tags: List[str] = field(default_factory=list)
    avoid_tags: List[str] = field(default_factory=list)
    difficulty_focus: str = "medium"
    max_per_keyword: int = 10
    days_range: int = 7


class UserMemoryModule:
    def __init__(self, memory_dir: str = "./memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.preference_file = self.memory_dir / "user_preference.json"
        self.stats_file = self.memory_dir / "learning_stats.json"
        self.strategy_file = self.memory_dir / "crawl_strategy.json"
        
        self.logger = logging.getLogger(__name__)
        
        self.preference = self._load_preference()
        self.stats = self._load_stats()
        self.strategy = self._load_strategy()
        
        self.logger.info(f"UserMemory initialized: companies={self.preference.companies}")
    
    def _load_preference(self) -> UserPreference:
        if self.preference_file.exists():
            with open(self.preference_file, 'r', encoding='utf-8') as f:
                return UserPreference(**json.load(f))
        return UserPreference()
    
    def _load_stats(self) -> LearningStats:
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return LearningStats(**json.load(f))
        return LearningStats()
    
    def _load_strategy(self) -> CrawlStrategy:
        if self.strategy_file.exists():
            with open(self.strategy_file, 'r', encoding='utf-8') as f:
                return CrawlStrategy(**json.load(f))
        return CrawlStrategy()
    
    def _save_preference(self):
        with open(self.preference_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.preference), f, ensure_ascii=False, indent=2)
    
    def _save_stats(self):
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.stats), f, ensure_ascii=False, indent=2)
    
    def _save_strategy(self):
        with open(self.strategy_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.strategy), f, ensure_ascii=False, indent=2)
    
    def update_preference(self, company: Optional[str] = None, position: Optional[str] = None, 
                      difficulty: Optional[str] = None, tag: Optional[str] = None):
        now = datetime.now().isoformat()
        
        if company and company not in self.preference.companies:
            self.preference.companies.insert(0, company)
            self.preference.companies = self.preference.companies[:10]
        
        if position and position not in self.preference.positions:
            self.preference.positions.insert(0, position)
            self.preference.positions = self.preference.positions[:10]
        
        if difficulty and difficulty not in self.preference.difficulties:
            self.preference.difficulties.insert(0, difficulty)
            self.preference.difficulties = self.preference.difficulties[:5]
        
        if tag and tag not in self.preference.tags:
            self.preference.tags.insert(0, tag)
            self.preference.tags = self.preference.tags[:20]
        
        self.preference.last_updated = now
        self._save_preference()
        self.logger.info(f"Updated preference: company={company}, position={position}, tag={tag}")
        
        self._auto_adjust_strategy()
    
    def add_keyword(self, keyword: str):
        if keyword and keyword not in self.preference.keywords:
            self.preference.keywords.append(keyword)
            self.preference.keywords = self.preference.keywords[:30]
            self.preference.last_updated = datetime.now().isoformat()
            self._save_preference()
            self.logger.info(f"Added keyword: {keyword}")
    
    def remove_keyword(self, keyword: str):
        if keyword in self.preference.keywords:
            self.preference.keywords.remove(keyword)
            self.preference.last_updated = datetime.now().isoformat()
            self._save_preference()
            self.logger.info(f"Removed keyword: {keyword}")
    
    def record_learning(self, card_id: str, company: str, tags: List[str], 
                      quality: int, difficulty: str):
        now = datetime.now().isoformat()
        
        self.stats.total_learned += 1
        if quality >= 3:
            self.stats.total_correct += 1
        else:
            self.stats.total_errors += 1
            for tag in tags:
                if tag not in self.stats.weak_tags:
                    self.stats.weak_tags.append(tag)
        self.stats.last_learned_at = now
        
        self.update_preference(company=company, difficulty=difficulty)
        
        self._save_stats()
        self.logger.info(f"Recorded learning: card={card_id}, quality={quality}")
    
    def get_weak_tags(self, limit: int = 10) -> List[str]:
        return self.stats.weak_tags[:limit]
    
    def _auto_adjust_strategy(self):
        self.strategy.priority_companies = self.preference.companies[:5]
        self.strategy.priority_tags = self.stats.weak_tags[:10]
        
        if self.preference.difficulties:
            self.strategy.difficulty_focus = self.preference.difficulties[0]
        
        self._save_strategy()
        self.logger.info(f"Auto-adjusted strategy: companies={self.strategy.priority_companies}")
    
    def get_crawl_strategy(self) -> CrawlStrategy:
        return self.strategy
    
    def generate_keywords(self) -> List[str]:
        keywords = []
        keywords.extend(self.preference.keywords)
        
        for company in self.strategy.priority_companies[:3]:
            keywords.append(f"{company} 面经")
            keywords.append(f"{company} 面试")
        
        for position in self.preference.positions[:3]:
            keywords.append(f"{position} 面经")
        
        for tag in self.strategy.priority_tags[:5]:
            keywords.append(f"{tag} 面试题")
        
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
        
        return result[:20]
    
    def get_suggestions(self) -> Dict:
        accuracy = self.stats.total_learned and (self.stats.total_correct / self.stats.total_learned) or 0.0
        
        suggestion_texts = []
        if self.stats.weak_tags:
            suggestion_texts.append(f"Focus on: {', '.join(self.stats.weak_tags[:3])}")
        if self.strategy.priority_companies:
            suggestion_texts.append(f"Target companies: {', '.join(self.strategy.priority_companies[:3])}")
        if self.stats.streak_days > 0:
            suggestion_texts.append(f"Day streak: {self.stats.streak_days}")
        
        return {
            "focus_companies": self.strategy.priority_companies[:3],
            "focus_tags": self.strategy.priority_tags[:5],
            "weak_tags": self.stats.weak_tags[:5],
            "daily_goal": min(20, max(5, self.stats.total_learned // 7 + 5)),
            "streak": self.stats.streak_days,
            "accuracy": accuracy,
            "texts": suggestion_texts
        }
    
    def export_preferences(self) -> Dict:
        return {
            "preference": asdict(self.preference),
            "stats": asdict(self.stats),
            "strategy": asdict(self.strategy),
            "generated_keywords": self.generate_keywords()
        }