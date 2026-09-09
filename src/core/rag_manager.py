"""
RAG Manager - 多路径检索与融合管理，支持语义、关键词、最近、公司、标签等路径
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from src.core.embedding_provider import EmbeddingProvider, EmbeddingConfig, EmbeddingProviderFactory


class RetrievalPath(Enum):
    """检索路径枚举"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    RECENT = "recent"
    COMPANY = "company"
    TAGS = "tags"


@dataclass
class RetrievalResult:
    """检索结果"""
    card_id: str
    score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    path_contributions: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            'card_id': self.card_id,
            'score': self.score,
            'source': self.source,
            'metadata': self.metadata,
            'rationale': self.rationale,
            'path_contributions': self.path_contributions
        }


class RagManager:
    """RAG 管理器 - 多路径检索与融合"""
    
    def __init__(self, chroma_client, sqlite_client, embedding_provider: Optional[EmbeddingProvider] = None):
        self.chroma = chroma_client
        self.sqlite = sqlite_client
        self.embedding_provider = embedding_provider
        self.logger = logging.getLogger(__name__)
        self.path_weights: Dict[str, float] = {
            RetrievalPath.SEMANTIC.value: 0.40,
            RetrievalPath.KEYWORD.value: 0.25,
            RetrievalPath.RECENT.value: 0.15,
            RetrievalPath.COMPANY.value: 0.12,
            RetrievalPath.TAGS.value: 0.08
        }
        self.embedding_cache: Dict[str, List[float]] = {}
    
    def _retrieve_semantic(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """语义检索"""
        try:
            if self.embedding_provider:
                query_embedding = self.embedding_provider.embed(query)
            else:
                query_embedding = self.chroma._create_embedding(query)
            
            results = self.chroma.search_similar(query, n_results=limit)
            return [(r['id'], r['score']) for r in results]
        except Exception as e:
            self.logger.error(f"Semantic retrieval failed: {e}")
            return []
    
    def _retrieve_keyword(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """关键词检索"""
        try:
            keywords = query.lower().split()
            all_cards = self.chroma.get_all_cards(limit=1000)
            
            scored_cards = []
            for card in all_cards:
                doc = card.get('document', '').lower()
                score = sum(1 for kw in keywords if kw in doc) / len(keywords) if keywords else 0
                if score > 0:
                    scored_cards.append((card['id'], score))
            
            scored_cards.sort(key=lambda x: x[1], reverse=True)
            return scored_cards[:limit]
        except Exception as e:
            self.logger.error(f"Keyword retrieval failed: {e}")
            return []
    
    def _retrieve_recent(self, limit: int = 10) -> List[Tuple[str, float]]:
        """最近检索"""
        try:
            cards = self.sqlite.get_recent_cards(limit=limit)
            return [(card['id'], 1.0 - (i / limit)) for i, card in enumerate(cards)]
        except Exception as e:
            self.logger.error(f"Recent retrieval failed: {e}")
            return []
    
    def _retrieve_by_company(self, company: str, limit: int = 10) -> List[Tuple[str, float]]:
        """按公司检索"""
        try:
            results = self.chroma.get_cards_by_tag(company, limit=limit)
            return [(r['id'], 1.0) for r in results]
        except Exception as e:
            self.logger.error(f"Company retrieval failed: {e}")
            return []
    
    def _retrieve_by_tags(self, tags: List[str], limit: int = 10) -> List[Tuple[str, float]]:
        """按标签检索"""
        try:
            all_cards = self.chroma.get_all_cards(limit=1000)
            
            scored_cards = []
            for card in all_cards:
                card_tags = card.get('metadata', {}).get('tags', '').split(',')
                overlap = len(set(tags) & set(card_tags))
                if overlap > 0:
                    score = overlap / len(tags) if tags else 0
                    scored_cards.append((card['id'], score))
            
            scored_cards.sort(key=lambda x: x[1], reverse=True)
            return scored_cards[:limit]
        except Exception as e:
            self.logger.error(f"Tags retrieval failed: {e}")
            return []
    
    def _rrf_fusion(self, path_results: Dict[str, List[Tuple[str, float]]], k: int = 60) -> Dict[str, float]:
        """RRF（倒数排名融合）融合多路径结果"""
        rrf_scores: Dict[str, float] = {}
        
        for path, results in path_results.items():
            weight = self.path_weights.get(path, 0.1)
            for rank, (card_id, score) in enumerate(results, 1):
                if card_id not in rrf_scores:
                    rrf_scores[card_id] = 0
                rrf_scores[card_id] += weight * (1 / (k + rank))
        
        return rrf_scores
    
    def search(self, query: str, session_id: str = "", limit: int = 10, 
              company: Optional[str] = None, tags: Optional[List[str]] = None) -> List[RetrievalResult]:
        """多路径搜索与融合"""
        path_results = {}
        
        path_results[RetrievalPath.SEMANTIC.value] = self._retrieve_semantic(query, limit)
        path_results[RetrievalPath.KEYWORD.value] = self._retrieve_keyword(query, limit)
        path_results[RetrievalPath.RECENT.value] = self._retrieve_recent(limit)
        
        if company:
            path_results[RetrievalPath.COMPANY.value] = self._retrieve_by_company(company, limit)
        
        if tags:
            path_results[RetrievalPath.TAGS.value] = self._retrieve_by_tags(tags, limit)
        
        fused_scores = self._rrf_fusion(path_results)
        
        results = []
        for card_id, score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            card = self.chroma.get_card(card_id)
            if card:
                path_contributions = {}
                for path, path_results_list in path_results.items():
                    for cid, pscore in path_results_list:
                        if cid == card_id:
                            path_contributions[path] = pscore
                            break
                
                result = RetrievalResult(
                    card_id=card_id,
                    score=score,
                    source="multi_path_rrf",
                    metadata=card.get('metadata', {}),
                    path_contributions=path_contributions
                )
                results.append(result)
        
        self.logger.info(f"Search completed: query={query}, results={len(results)}")
        return results
    
    def set_path_weights(self, weights: Dict[str, float]) -> None:
        """设置路径权重"""
        self.path_weights.update(weights)
        self.logger.info(f"Path weights updated: {self.path_weights}")
    
    def get_path_weights(self) -> Dict[str, float]:
        """获取路径权重"""
        return self.path_weights.copy()
    
    def refresh_embedding_cache(self, card_ids: List[str]) -> None:
        """刷新嵌入缓存"""
        if not self.embedding_provider:
            return
        
        try:
            for card_id in card_ids:
                card = self.chroma.get_card(card_id)
                if card:
                    text = card.get('document', '')
                    embedding = self.embedding_provider.embed(text)
                    self.embedding_cache[card_id] = embedding
            self.logger.info(f"Embedding cache refreshed for {len(card_ids)} cards")
        except Exception as e:
            self.logger.error(f"Failed to refresh embedding cache: {e}")
    
    def explain_result(self, result: RetrievalResult) -> str:
        """生成结果解释"""
        explanation = f"Card {result.card_id} (score: {result.score:.3f})\n"
        explanation += "Path contributions:\n"
        
        for path, contribution in result.path_contributions.items():
            weight = self.path_weights.get(path, 0)
            explanation += f"  - {path}: {contribution:.3f} (weight: {weight:.2f})\n"
        
        return explanation
