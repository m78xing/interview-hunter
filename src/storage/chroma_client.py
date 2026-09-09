"""
Chroma 向量数据库客户端
"""
import chromadb
import logging
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
from ..core.embedding_provider import EmbeddingProvider, EmbeddingConfig, EmbeddingProviderFactory


class ChromaClient:
    COLLECTION_NAME = "interview_cards"
    
    def __init__(self, persist_directory: str, embedding_provider: Optional[EmbeddingProvider] = None):
        self.persist_directory = persist_directory
        self.logger = logging.getLogger(__name__)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        if embedding_provider is None:
            config = EmbeddingConfig(
                provider="mock",
                model="mock",
                dimension=384
            )
            embedding_provider = EmbeddingProviderFactory.create(config)
        
        self.embedding_provider = embedding_provider
        self._init_collection()
    
    def _init_collection(self):
        """初始化 collection"""
        try:
            self.collection = self.client.get_collection(name=self.COLLECTION_NAME)
        except Exception:
            self.collection = self.client.create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "Interview cards collection"}
            )
    
    def _create_embedding(self, text: str) -> List[float]:
        """创建文本向量"""
        return self.embedding_provider.embed(text)
    
    def add_card(self, card_id: str, text: str, metadata: dict) -> bool:
        """添加卡片"""
        try:
            embedding = self._create_embedding(text)
            
            self.collection.upsert(
                ids=[card_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            print(f"Error adding card: {e}")
            return False
    
    def search_similar(
        self,
        query_text: str,
        n_results: int = 5,
        threshold: float = 0.0,
        filter_metadata: Optional[dict] = None
    ) -> List[Dict]:
        """搜索相似卡片"""
        query_embedding = self._create_embedding(query_text)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        similar = []
        if results and results.get('ids') and len(results['ids']) > 0:
            ids = results['ids'][0]
            distances = results.get('distances')
            distances_list = distances[0] if distances else []
            documents = results.get('documents')
            documents_list = documents[0] if documents else []
            metadatas = results.get('metadatas')
            metadatas_list = metadatas[0] if metadatas else []
            for i, card_id in enumerate(ids):
                score = distances_list[i] if i < len(distances_list) else 0
                card_score = 1 - score
                if threshold > 0 and card_score < threshold:
                    continue
                similar.append({
                    'id': card_id,
                    'score': card_score,
                    'document': documents_list[i] if i < len(documents_list) else '',
                    'metadata': metadatas_list[i] if i < len(metadatas_list) else {}
                })
        
        return similar
    
    def check_duplicate(self, text: str, threshold: float = 0.92) -> Optional[Dict]:
        """检查是否重复"""
        query_embedding = self._create_embedding(text)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=1
        )
        
        if results and results.get('ids') and results['ids'] and len(results['ids'][0]) > 0:
            distances = results.get('distances')
            distance = distances[0][0] if distances else 0
            similarity = 1 - distance
            
            if similarity >= threshold:
                ids = results['ids'][0]
                documents = results.get('documents')
                documents_list = documents[0] if documents else []
                return {
                    'id': ids[0],
                    'similarity': similarity,
                    'document': documents_list[0] if documents_list else ''
                }
        
        return None
    
    def get_card(self, card_id: str) -> Optional[Dict]:
        """获取单个卡片"""
        try:
            result = self.collection.get(ids=[card_id])
            if result and result.get('ids'):
                ids = result['ids']
                documents = result.get('documents', [])
                metadatas = result.get('metadatas', [])
                return {
                    'id': ids[0],
                    'document': documents[0] if documents else '',
                    'metadata': metadatas[0] if metadatas else {}
                }
        except Exception:
            pass
        return None
    
    def get_all_cards(self, limit: int = 1000) -> List[Dict]:
        """获取所有卡片"""
        try:
            result = self.collection.get(limit=limit)
            cards = []
            if result and result.get('ids'):
                ids = result['ids']
                documents = result.get('documents')
                metadatas = result.get('metadatas')
                for i, card_id in enumerate(ids):
                    doc = documents[i] if documents and i < len(documents) else ''
                    meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                    cards.append({
                        'id': card_id,
                        'document': doc,
                        'metadata': meta
                    })
            return cards
        except Exception:
            return []
    
    def delete_card(self, card_id: str) -> bool:
        """删除卡片"""
        try:
            self.collection.delete(ids=[card_id])
            return True
        except Exception:
            return False
    
    def count_cards(self) -> int:
        """获取卡片数量"""
        return self.collection.count()
    
    def get_cards_by_tag(self, tag: str, limit: int = 20) -> List[Dict]:
        """按标签获取卡片"""
        results = self.collection.get(
            where={"tags": {"$contains": tag}},
            limit=limit
        )
        
        cards = []
        if results and results.get('ids'):
            ids = results['ids']
            documents = results.get('documents')
            metadatas = results.get('metadatas')
            for i, card_id in enumerate(ids):
                doc = documents[i] if documents and i < len(documents) else ''
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                cards.append({
                    'id': card_id,
                    'document': doc,
                    'metadata': meta
                })
        return cards
    
    def reset(self):
        """重置数据库"""
        self.client.delete_collection(name=self.COLLECTION_NAME)
        self._init_collection()

    def search_cards(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索卡片（search_similar 的别名）"""
        return self.search_similar(query, n_results=limit)
