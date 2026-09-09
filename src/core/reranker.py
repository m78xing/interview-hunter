"""
搜索结果重排 - 基于用户偏好和学习历史的结果重排
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class RankedResult:
    card_id: str
    original_score: float
    rerank_score: float
    final_score: float
    metadata: Dict


class SearchResultReranker:
    def __init__(self, sqlite_client, user_memory_module):
        self.sqlite = sqlite_client
        self.user_memory = user_memory_module
        self.logger = logging.getLogger(__name__)
    
    def get_card_stats(self, card_id: str) -> Dict:
        try:
            stats = self.sqlite.get_card_stats(card_id)
            return stats or {}
        except Exception as e:
            self.logger.warning(f"Failed to get card stats for {card_id}: {e}")
            return {}
    
    def calculate_retrievability_score(self, card_id: str) -> float:
        stats = self.get_card_stats(card_id)
        
        if not stats:
            return 0.5
        
        interval = stats.get('interval', 1)
        ease_factor = stats.get('ease_factor', 2.5)
        
        retrievability = (1 - 0.5) * (2 ** (-interval / ease_factor)) + 0.5
        return max(0, min(1, retrievability))
    
    def calculate_weakness_score(self, card_id: str) -> float:
        stats = self.get_card_stats(card_id)
        
        if not stats:
            return 0.5
        
        total_reviews = stats.get('total_reviews', 0)
        correct_reviews = stats.get('correct_reviews', 0)
        
        if total_reviews == 0:
            return 0.5
        
        accuracy = correct_reviews / total_reviews
        weakness = 1 - accuracy
        return max(0, min(1, weakness))
    
    def calculate_preference_score(self, card_metadata: Dict) -> float:
        if not self.user_memory:
            return 0.5
        
        try:
            strategy = self.user_memory.get_crawl_strategy()
            
            company = card_metadata.get('company', '')
            tags = card_metadata.get('tags', '').split(',')
            difficulty = card_metadata.get('difficulty', '')
            
            score = 0.5
            
            if company in strategy.priority_companies:
                score += 0.2
            
            tag_overlap = len(set(tags) & set(strategy.priority_tags))
            if tag_overlap > 0:
                score += 0.15 * (tag_overlap / len(strategy.priority_tags))
            
            if strategy.difficulty_focus != 'all' and difficulty == strategy.difficulty_focus:
                score += 0.15
            
            return max(0, min(1, score))
        except Exception as e:
            self.logger.warning(f"Failed to calculate preference score: {e}")
            return 0.5
    
    def calculate_recency_score(self, card_metadata: Dict) -> float:
        created_at = card_metadata.get('created_at')
        
        if not created_at:
            return 0.5
        
        try:
            from datetime import datetime
            card_date = datetime.fromisoformat(created_at)
            now = datetime.now()
            days_old = (now - card_date).days
            
            recency = max(0, 1 - (days_old / 30))
            return max(0, min(1, recency))
        except Exception as e:
            self.logger.warning(f"Failed to calculate recency score: {e}")
            return 0.5
    
    def rerank_results(
        self,
        results: List[Dict],
        weights: Optional[Dict[str, float]] = None
    ) -> List[RankedResult]:
        if weights is None:
            weights = {
                'original': 0.3,
                'retrievability': 0.25,
                'weakness': 0.2,
                'preference': 0.15,
                'recency': 0.1
            }
        
        ranked_results = []
        
        for result in results:
            card_id = result.get('id')
            if card_id is None:
                continue
            original_score = result.get('score', 0.5)
            metadata = result.get('metadata', {})
            
            retrievability = self.calculate_retrievability_score(card_id)
            weakness = self.calculate_weakness_score(card_id)
            preference = self.calculate_preference_score(metadata)
            recency = self.calculate_recency_score(metadata)
            
            rerank_score = (
                retrievability * weights.get('retrievability', 0.25) +
                weakness * weights.get('weakness', 0.2) +
                preference * weights.get('preference', 0.15) +
                recency * weights.get('recency', 0.1)
            )
            
            final_score = (
                original_score * weights.get('original', 0.3) +
                rerank_score * (1 - weights.get('original', 0.3))
            )
            
            ranked_results.append(RankedResult(
                card_id=card_id,
                original_score=original_score,
                rerank_score=rerank_score,
                final_score=final_score,
                metadata=metadata
            ))
        
        ranked_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return ranked_results
