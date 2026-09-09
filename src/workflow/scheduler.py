"""
调度工作流 - 基于遗忘曲线推荐卡片和调度复习
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional

from ..core import RecommendationEngine, LLMAuditor, RagManager, SearchResultReranker
from ..storage import SQLiteClient, ChromaClient, Card


class SchedulerWorkflow:
    """调度工作流 - 负责推荐卡片和调度复习"""
    
    def __init__(
        self,
        sqlite_client: SQLiteClient,
        chroma_client: ChromaClient,
        recommendation_engine: RecommendationEngine,
        llm_auditor: Optional[LLMAuditor] = None,
        keywords: Optional[List[str]] = None,
        user_memory = None
    ):
        self.sqlite = sqlite_client
        self.chroma = chroma_client
        self.recommender = recommendation_engine
        self.auditor = llm_auditor
        self.keywords = keywords or []
        self.user_memory = user_memory
        
        self.session_started = False
        self.session_cards: List[Dict] = []
        
        self.multi_retrieval = RagManager(chroma_client, sqlite_client)
        self.reranker = SearchResultReranker(sqlite_client, user_memory) if user_memory else None
        
        self.logger = logging.getLogger(__name__)
    
    async def start_session(self, target_company: str = "", limit: int = 20) -> List[Dict]:
        """开始学习会话 - 按时间顺序推荐"""
        self.logger.info(f"开始学习会话，目标公司: {target_company}")
        
        self.recommender.reset_session()
        
        all_cards = self.sqlite.get_all_cards()
        
        if target_company:
            all_cards = [c for c in all_cards if target_company in c.company]
        
        all_cards.sort(key=lambda c: c.created_at, reverse=True)
        
        self.session_cards = []
        for card in all_cards[:limit]:
            self.session_cards.append({
                'card': card,
                'score': 0.0,
                'breakdown': {}
            })
        
        self.session_started = True
        
        self.logger.info(f"推荐 {len(self.session_cards)} 张卡片")
        
        return self.session_cards
    
    def get_next_card(self) -> Optional[Dict]:
        """获取下一张卡片"""
        if not self.session_started or not self.session_cards:
            return None
        
        if self.session_cards:
            card_info = self.session_cards.pop(0)
            self.recommender.mark_shown(card_info['card'].id)
            return card_info
        
        return None
    
    async def record_review(
        self,
        card_id: str,
        quality: int,
        time_taken: int = 0
    ):
        """记录复习结果"""
        self.sqlite.add_review_log(card_id, quality, time_taken)
        self.sqlite.update_ease_factor(card_id, quality)
        
        self.logger.info(f"记录复习: card_id={card_id}, quality={quality}")
        
        await self._check_threshold_trigger(card_id, quality)
    
    async def _check_threshold_trigger(self, card_id: str, quality: int):
        """检查是否触发阈值审计"""
        if not self.auditor:
            return
        
        card = self.sqlite.get_card(card_id)
        if not card:
            return
        
        for tag in card.tags:
            consecutive = self.sqlite.get_consecutive_errors(tag, limit=5)
            error_rate = self.sqlite.get_tag_error_rate(tag)
            
            if self.auditor.should_trigger_threshold_audit(tag, consecutive, error_rate):
                self.logger.warning(f"触发阈值审计: tag={tag}, consecutive={consecutive}, error_rate={error_rate}")
                
                recent_logs = self.sqlite.get_review_logs(card_id, limit=10)
                suggestion = self.auditor.analyze_threshold_trigger(
                    tag, consecutive, [log.to_dict() for log in recent_logs]
                )
                
                if suggestion:
                    self.logger.info(f"阈值审计建议: {suggestion}")
    
    async def trigger_daily_audit(self) -> Optional[Dict]:
        """触发每日审计"""
        if not self.auditor:
            return None
        
        if not self.auditor.should_trigger_daily_audit():
            return None
        
        self.logger.info("触发每日审计")
        
        review_stats = self._get_review_stats()
        tag_error_rates = self._get_tag_error_rates()
        mastery_matrix = self._get_mastery_matrix()
        
        weak_tags = self._get_weak_tags()
        
        result = self.auditor.audit(
            review_stats=review_stats,
            tag_error_rates=tag_error_rates,
            current_keywords=self.keywords,
            weak_tags=weak_tags,
            mastery_matrix=mastery_matrix
        )
        
        if result:
            await self._apply_audit_result(result)
        
        return result
    
    async def _apply_audit_result(self, result: Dict):
        """应用审计结果"""
        if 'keyword_adjustments' in result:
            for adjustment in result['keyword_adjustments']:
                keyword = adjustment.get('keyword', '')
                action = adjustment.get('action', '')
                
                if action == 'add' and keyword:
                    if keyword not in self.keywords:
                        self.keywords.append(keyword)
                        self.logger.info(f"审计建议添加关键字: {keyword}")
                
                elif action == 'remove' and keyword:
                    if keyword in self.keywords:
                        self.keywords.remove(keyword)
                        self.logger.info(f"审计建议移除关键字: {keyword}")
        
        self.logger.info(f"审计结果已应用")
    
    def _get_review_stats(self) -> Dict:
        """获取复习统计"""
        today_count = self.sqlite.get_today_review_count()
        total_cards = self.sqlite.get_total_cards()
        
        recent_logs = self.sqlite.get_recent_review_logs(days=7)
        total_reviews = len(recent_logs)
        correct = len([log for log in recent_logs if log.quality >= 3])
        
        return {
            "today_reviews": today_count,
            "total_cards": total_cards,
            "week_reviews": total_reviews,
            "week_correct_rate": correct / total_reviews if total_reviews > 0 else 0
        }
    
    def _get_tag_error_rates(self) -> Dict[str, float]:
        """获取标签错误率"""
        tag_stats = self.sqlite.get_tag_stats()
        return {
            tag: stats.get('error_count', 0) / max(1, stats.get('total_reviews', 1))
            for tag, stats in tag_stats.items()
        }
    
    def _get_mastery_matrix(self) -> Dict[str, float]:
        """获取掌握度矩阵"""
        tag_stats = self.sqlite.get_tag_stats()
        return {
            tag: stats.get('mastery_level', 0.0)
            for tag, stats in tag_stats.items()
        }
    
    def _get_weak_tags(self, threshold: float = 0.5) -> List[str]:
        """获取薄弱标签"""
        mastery_matrix = self._get_mastery_matrix()
        return [tag for tag, level in mastery_matrix.items() if level < threshold]
    
    def end_session(self):
        """结束学习会话"""
        self.logger.info("结束学习会话")
        self.session_started = False
        self.session_cards = []
    
    def get_session_progress(self) -> Dict:
        """获取会话进度"""
        return {
            "started": self.session_started,
            "total": len(self.session_cards) if self.session_started else 0,
            "remaining": len(self.session_cards) if self.session_started else 0
        }
    
    def get_recommendations(self, card_id: str, limit: int = 3) -> List[Dict]:
        """获取卡片推荐"""
        card = self.sqlite.get_card(card_id)
        if not card:
            return []
        
        text = f"{card.question} {card.answer}"
        
        if self.multi_retrieval:
            try:
                tags = card.tags if hasattr(card, 'tags') else []
                company = card.company if hasattr(card, 'company') else None
                
                results = self.multi_retrieval.search(
                    query=text,
                    company=company,
                    tags=tags,
                    limit=limit + 1
                )
                
                if self.reranker:
                    result_dicts = [
                        {
                            'id': r.card_id,
                            'score': r.score,
                            'metadata': r.metadata
                        }
                        for r in results
                    ]
                    ranked = self.reranker.rerank_results(result_dicts)
                    recommendations = [
                        {
                            'id': r.card_id,
                            'score': r.final_score,
                            'metadata': r.metadata
                        }
                        for r in ranked
                        if r.card_id != card_id
                    ]
                else:
                    recommendations = [
                        {
                            'id': r.card_id,
                            'score': r.score,
                            'metadata': r.metadata
                        }
                        for r in results
                        if r.card_id != card_id
                    ]
                
                return recommendations[:limit]
            except Exception as e:
                self.logger.warning(f"Multi-path retrieval failed, falling back to semantic search: {e}")
        
        results = self.chroma.search_similar(text, n_results=limit + 1)
        
        recommendations = []
        for result in results:
            if result['id'] != card_id:
                recommendations.append(result)
        
        return recommendations[:limit]
