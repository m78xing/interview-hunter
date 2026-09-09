"""
Embedding 提供者 - 支持多种 embedding 模型
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class EmbeddingConfig:
    """Embedding 配置"""
    provider: str  # "openai", "cohere", "local", "mock"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    dimension: int = 384


class EmbeddingProvider(ABC):
    """Embedding 提供者基类"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """生成单个文本的 embedding"""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding 提供者"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.api_key or os.getenv("OPENAI_API_KEY"),
                base_url=config.base_url
            )
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
    
    def embed(self, text: str) -> List[float]:
        """生成单个文本的 embedding"""
        try:
            response = self.client.embeddings.create(
                model=self.config.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            self.logger.error(f"OpenAI embedding failed: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        try:
            response = self.client.embeddings.create(
                model=self.config.model,
                input=texts
            )
            embeddings: List[Optional[List[float]]] = [None] * len(texts)
            for item in response.data:
                embeddings[item.index] = item.embedding
            return [e for e in embeddings if e is not None]
        except Exception as e:
            self.logger.error(f"OpenAI batch embedding failed: {e}")
            raise


class CohereEmbeddingProvider(EmbeddingProvider):
    """Cohere Embedding 提供者"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            import cohere  # type: ignore[reportMissingImports]
            self.client = cohere.Client(api_key=config.api_key or os.getenv("COHERE_API_KEY"))
        except ImportError:
            raise ImportError("cohere package not installed. Install with: pip install cohere")
    
    def embed(self, text: str) -> List[float]:
        """生成单个文本的 embedding"""
        try:
            response = self.client.embed(
                model=self.config.model,
                texts=[text],
                input_type="search_document"
            )
            return response.embeddings[0]
        except Exception as e:
            self.logger.error(f"Cohere embedding failed: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        try:
            response = self.client.embed(
                model=self.config.model,
                texts=texts,
                input_type="search_document"
            )
            return response.embeddings
        except Exception as e:
            self.logger.error(f"Cohere batch embedding failed: {e}")
            raise


class LocalEmbeddingProvider(EmbeddingProvider):
    """本地 Embedding 提供者 (使用 sentence-transformers)"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[reportMissingImports]
            self.model = SentenceTransformer(config.model)
        except ImportError:
            raise ImportError("sentence-transformers package not installed. Install with: pip install sentence-transformers")
    
    def embed(self, text: str) -> List[float]:
        """生成单个文本的 embedding"""
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"Local embedding failed: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            self.logger.error(f"Local batch embedding failed: {e}")
            raise


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock Embedding 提供者 (用于测试)"""
    
    def embed(self, text: str) -> List[float]:
        """生成单个文本的 embedding"""
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val >> (i % 32)) % 100 / 100.0 for i in range(self.config.dimension)]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding"""
        return [self.embed(text) for text in texts]


class EmbeddingProviderFactory:
    """Embedding 提供者工厂"""
    
    _providers = {
        "openai": OpenAIEmbeddingProvider,
        "cohere": CohereEmbeddingProvider,
        "local": LocalEmbeddingProvider,
        "mock": MockEmbeddingProvider,
    }
    
    @classmethod
    def create(cls, config: EmbeddingConfig) -> EmbeddingProvider:
        """创建 embedding 提供者"""
        provider_class = cls._providers.get(config.provider)
        if not provider_class:
            raise ValueError(f"Unknown embedding provider: {config.provider}")
        return provider_class(config)
    
    @classmethod
    def register(cls, name: str, provider_class):
        """注册自定义提供者"""
        cls._providers[name] = provider_class
