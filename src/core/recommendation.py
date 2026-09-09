"""
推荐算法模块
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from collections import deque

from ..storage import SQLiteClient, Card


class RecommendationEngine:
    def __init__(
        self,
        sqlite_client: SQLiteClient,
        weights=None,
        diversity_penalty_coef: float = 0.5,
        recently_shown_tags_length: int = 3
    ):
        self.sqlite = sqlite_client
        
        if weights is None:
            self.weights = {
                'retrievability': 0.35,
                'weakness': 0.30,
                'hotness': 0.20,
                'dependency': 0.15
            }
        elif hasattr(weights, '__dataclass_fields__'):
            self.weights = {
                'retrievability': weights.retrievability,
                'weakness': weights.weakness,
                'hotness': weights.hotness,
                'dependency': weights.dependency
            }
        else:
            self.weights = weights
        
        self.diversity_penalty_coef = diversity_penalty_coef
        self.recently_shown_tags_length = recently_shown_tags_length
        
        self.recently_shown_tags: deque = deque(maxlen=recently_shown_tags_length)
        self.recently_shown_ids: List[str] = []
        
        self.tag_hierarchy = self._load_tag_hierarchy()
    
    def _load_tag_hierarchy(self) -> Dict:
        """加载标签层级"""
        return {
            "计算机网络": {
                "children": ["TCP", "UDP", "HTTP", "HTTPS", "DNS"],
                "is_prerequisite": True
            },
            "TCP": {
                "children": ["HTTP/3", "QUIC", "WebSocket"],
                "parents": ["计算机网络"]
            },
            "操作系统": {
                "children": ["进程线程", "内存管理", "文件系统", "IO模型"],
                "is_prerequisite": True
            },
            "数据结构": {
                "children": ["数组", "链表", "树", "图", "哈希"],
                "is_prerequisite": True
            },
            "算法": {
                "children": ["排序", "查找", "动态规划", "回溯", "贪心"],
                "parents": ["数据结构"]
            },
            "数据库": {
                "children": ["SQL", "NoSQL", "Redis", "MySQL", "MongoDB"],
                "is_prerequisite": False
            },
            "Redis": {
                "children": ["分布式锁", "缓存穿透", "缓存雪崩", "Redis集群"],
                "parents": ["数据库"]
            }
        }
    
    def calculate_retrievability(self, card_id: str) -> float:
        """计算遗忘曲线分数 (Retrievability)
        
        基于上次复习时间，越久远分数越高（越需要复习）
        """
        stats = self.sqlite.get_card_stats(card_id)
        if not stats or not stats.get('last_reviewed_at'):
            return 1.0
        
        last_review = datetime.fromisoformat(stats['last_reviewed_at'])
        days_since = (datetime.now() - last_review).days
        
        interval = stats.get('interval_days', 1)
        if interval < 1:
            interval = 1
        
        if days_since >= interval:
            return min(1.0, days_since / (interval * 2))
        return 0.0
    
    def calculate_weakness(self, card_id: str) -> float:
        """计算薄弱点分数
        
        基于错误率，错误率越高分数越高
        """
        stats = self.sqlite.get_card_stats(card_id)
        if not stats or stats['total_reviews'] == 0:
            return 0.5
        
        if stats['total_reviews'] >= 3:
            error_rate = stats['error_count'] / stats['total_reviews']
            return error_rate
        
        return 0.3
    
    def calculate_hotness(self, card: Card, target_company: str) -> float:
        """计算岗位热度分数
        
        如果卡片来自目标公司，分数更高
        如果卡片标签在最近采集中出现频率高，分数更高
        """
        score = 0.0
        
        if target_company and target_company in card.company:
            score += 0.6
        
        hot_tags = self._get_recent_hot_tags()
        for tag in card.tags:
            if tag in hot_tags:
                score += 0.2
                break
        
        return min(1.0, score)
    
    def calculate_dependency(self, card: Card) -> float:
        """计算知识依赖分数
        
        如果父级知识点掌握度低，降低当前卡片优先级
        """
        if not card.tags:
            return 0.5
        
        for tag in card.tags:
            if tag in self.tag_hierarchy:
                hierarchy = self.tag_hierarchy[tag]
                
                if 'parents' in hierarchy:
                    for parent in hierarchy['parents']:
                        parent_mastery = self._get_tag_mastery(parent)
                        if parent_mastery < 0.5:
                            return 0.2
        
        return 0.5
    
    def _get_tag_mastery(self, tag: str) -> float:
        """获取标签掌握度"""
        stats = self.sqlite.get_tag_stats()
        if tag in stats:
            return stats[tag].get('mastery_level', 0.0)
        return 0.0
    
    def _get_recent_hot_tags(self) -> List[str]:
        """获取最近的热门的标签"""
        tag_counts = {}
        
        cards = self.sqlite.get_all_cards()
        recent_cards = [c for c in cards if self._is_recent(c.created_at)]
        
        for card in recent_cards:
            for tag in card.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_tags[:5]]
    
    def _is_recent(self, created_at: str, days: int = 3) -> bool:
        """检查是否在最近N天内"""
        try:
            created = datetime.fromisoformat(created_at)
            return (datetime.now() - created).days <= days
        except:
            return False
    
    def calculate_diversity_penalty(self, card: Card) -> float:
        """计算多样性惩罚
        
        如果卡片标签在最近出现的标签中，分数降低
        """
        if not self.recently_shown_tags:
            return 0.0
        
        for tag in card.tags:
            if tag in self.recently_shown_tags:
                return self.diversity_penalty_coef
        
        return 0.0
    
    def score_card(self, card: Card, target_company: str) -> Tuple[float, Dict]:
        """计算卡片总分"""
        r = self.calculate_retrievability(card.id)
        w = self.calculate_weakness(card.id)
        h = self.calculate_hotness(card, target_company)
        d = self.calculate_dependency(card)
        s = self.calculate_diversity_penalty(card)
        
        score = (
            self.weights['retrievability'] * r +
            self.weights['weakness'] * w +
            self.weights['hotness'] * h +
            self.weights['dependency'] * d -
            s
        )
        
        breakdown = {
            'retrievability': r,
            'weakness': w,
            'hotness': h,
            'dependency': d,
            'diversity_penalty': s,
            'total': score
        }
        
        return max(0.0, score), breakdown
    
    def recommend(self, limit: int = 10, target_company: str = "") -> List[Dict]:
        """推荐卡片"""
        due_ids = self.sqlite.get_due_cards(limit * 2)
        
        scored_cards = []
        for card_id in due_ids:
            card = self.sqlite.get_card(card_id)
            if not card:
                continue
            
            score, breakdown = self.score_card(card, target_company)
            
            stats = self.sqlite.get_card_stats(card_id)
            
            scored_cards.append({
                'card': card,
                'score': score,
                'breakdown': breakdown,
                'total_reviews': stats['total_reviews'] if stats else 0,
                'last_reviewed': stats['last_reviewed_at'] if stats else None
            })
        
        scored_cards.sort(key=lambda x: (
            -x['score'],
            x['card'].created_at,
            x['card'].id
        ))
        
        selected = []
        for item in scored_cards:
            if len(selected) >= limit:
                break
            
            card = item['card']
            tags_new = [t for t in card.tags if t not in self.recently_shown_tags]
            
            if tags_new or len(self.recently_shown_tags) == 0:
                selected.append(item)
                
                for tag in card.tags:
                    if tag not in self.recently_shown_tags:
                        self.recently_shown_tags.append(tag)
        
        return selected
    
    def mark_shown(self, card_id: str):
        """标记卡片已展示"""
        self.recently_shown_ids.append(card_id)
        card = self.sqlite.get_card(card_id)
        if card:
            for tag in card.tags:
                if tag not in self.recently_shown_tags:
                    self.recently_shown_tags.append(tag)
    
    def reset_session(self):
        """重置会话"""
        self.recently_shown_tags.clear()
        self.recently_shown_ids.clear()
