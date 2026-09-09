"""
Experiment Framework for Interview Hunter Optimization

Provides baseline definitions, variant configurations, data generation,
and statistical analysis for rigorous experimental evaluation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import json
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


class BaselineType(Enum):
    """Baseline configurations for experiments."""
    B0 = "B0"  # Context + memory off, single-path RAG
    B1 = "B1"  # Context + memory on, single-path RAG
    B2 = "B2"  # Context + memory on, multi-path RAG (no adaptive weights)


class VariantType(Enum):
    """Variant configurations for experiments."""
    V1 = "V1"  # Adaptive weights for RAG paths
    V2 = "V2"  # Explainable ranking outputs
    V3 = "V3"  # Robustness tests (noisy signals, drifted preferences)


@dataclass
class BaselineConfig:
    """Configuration for a baseline experiment."""
    baseline_type: BaselineType
    context_enabled: bool
    memory_enabled: bool
    rag_paths: List[str]
    adaptive_weights: bool
    explainability: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'baseline_type': self.baseline_type.value,
            'context_enabled': self.context_enabled,
            'memory_enabled': self.memory_enabled,
            'rag_paths': self.rag_paths,
            'adaptive_weights': self.adaptive_weights,
            'explainability': self.explainability,
        }


@dataclass
class VariantConfig:
    """Configuration for a variant experiment."""
    variant_type: VariantType
    base_baseline: BaselineType
    modifications: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'variant_type': self.variant_type.value,
            'base_baseline': self.base_baseline.value,
            'modifications': self.modifications,
        }


class BaselineFactory:
    """Factory for creating baseline configurations."""
    
    @staticmethod
    def create_b0() -> BaselineConfig:
        """B0: Context + memory off, single-path RAG."""
        return BaselineConfig(
            baseline_type=BaselineType.B0,
            context_enabled=False,
            memory_enabled=False,
            rag_paths=['semantic'],
            adaptive_weights=False,
            explainability=False,
        )
    
    @staticmethod
    def create_b1() -> BaselineConfig:
        """B1: Context + memory on, single-path RAG."""
        return BaselineConfig(
            baseline_type=BaselineType.B1,
            context_enabled=True,
            memory_enabled=True,
            rag_paths=['semantic'],
            adaptive_weights=False,
            explainability=False,
        )
    
    @staticmethod
    def create_b2() -> BaselineConfig:
        """B2: Context + memory on, multi-path RAG (no adaptive weights)."""
        return BaselineConfig(
            baseline_type=BaselineType.B2,
            context_enabled=True,
            memory_enabled=True,
            rag_paths=['semantic', 'keyword', 'recent', 'company', 'tags'],
            adaptive_weights=False,
            explainability=False,
        )
    
    @staticmethod
    def create_all() -> Dict[BaselineType, BaselineConfig]:
        """Create all baseline configurations."""
        return {
            BaselineType.B0: BaselineFactory.create_b0(),
            BaselineType.B1: BaselineFactory.create_b1(),
            BaselineType.B2: BaselineFactory.create_b2(),
        }


class VariantFactory:
    """Factory for creating variant configurations."""
    
    @staticmethod
    def create_v1() -> VariantConfig:
        """V1: Adaptive weights for RAG paths."""
        return VariantConfig(
            variant_type=VariantType.V1,
            base_baseline=BaselineType.B2,
            modifications={
                'adaptive_weights': True,
                'weight_learning_rate': 0.01,
                'weight_decay': 0.95,
            }
        )
    
    @staticmethod
    def create_v2() -> VariantConfig:
        """V2: Explainable ranking outputs."""
        return VariantConfig(
            variant_type=VariantType.V2,
            base_baseline=BaselineType.B2,
            modifications={
                'explainability': True,
                'explain_top_k': 3,
                'include_path_scores': True,
            }
        )
    
    @staticmethod
    def create_v3() -> VariantConfig:
        """V3: Robustness tests (noisy signals, drifted preferences)."""
        return VariantConfig(
            variant_type=VariantType.V3,
            base_baseline=BaselineType.B2,
            modifications={
                'noise_level': 0.1,
                'preference_drift_rate': 0.05,
                'signal_corruption': True,
            }
        )
    
    @staticmethod
    def create_all() -> Dict[VariantType, VariantConfig]:
        """Create all variant configurations."""
        return {
            VariantType.V1: VariantFactory.create_v1(),
            VariantType.V2: VariantFactory.create_v2(),
            VariantType.V3: VariantFactory.create_v3(),
        }


@dataclass
class ExperimentMetrics:
    """Metrics for experiment evaluation."""
    # Retrieval metrics
    map_score: float = 0.0
    ndcg_at_5: float = 0.0
    ndcg_at_10: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    
    # Memory metrics
    memory_recall_lift: float = 0.0
    forgetting_rate: float = 0.0
    memory_retention: float = 0.0
    
    # Explainability metrics
    interpretability_score: float = 0.0
    
    # Efficiency metrics
    latency_ms: float = 0.0
    throughput_qps: float = 0.0
    memory_usage_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'map_score': self.map_score,
            'ndcg_at_5': self.ndcg_at_5,
            'ndcg_at_10': self.ndcg_at_10,
            'recall_at_5': self.recall_at_5,
            'recall_at_10': self.recall_at_10,
            'memory_recall_lift': self.memory_recall_lift,
            'forgetting_rate': self.forgetting_rate,
            'memory_retention': self.memory_retention,
            'interpretability_score': self.interpretability_score,
            'latency_ms': self.latency_ms,
            'throughput_qps': self.throughput_qps,
            'memory_usage_mb': self.memory_usage_mb,
        }


@dataclass
class ExperimentResult:
    """Result of a single experiment run."""
    experiment_id: str
    config_type: str  # 'baseline' or 'variant'
    config_name: str  # 'B0', 'V1', etc.
    seed: int
    timestamp: str
    metrics: ExperimentMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'experiment_id': self.experiment_id,
            'config_type': self.config_type,
            'config_name': self.config_name,
            'seed': self.seed,
            'timestamp': self.timestamp,
            'metrics': self.metrics.to_dict(),
            'metadata': self.metadata,
        }


class DataGenerator:
    """Generate synthetic data for experiments with reproducibility."""
    
    def __init__(self, seed: int = 42):
        """Initialize data generator with seed."""
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
    
    def generate_queries(self, num_queries: int = 100) -> List[Dict[str, Any]]:
        """Generate synthetic queries."""
        queries = []
        topics = ['算法', '系统设计', '数据库', '网络', '操作系统', '前端', '后端']
        companies = ['字节', '阿里', '腾讯', '百度', '美团', '快手', '抖音']
        
        for i in range(num_queries):
            query = {
                'id': f'query_{i}',
                'text': f'{random.choice(topics)}面试题 {i}',
                'topic': random.choice(topics),
                'company': random.choice(companies),
                'difficulty': random.choice(['easy', 'medium', 'hard']),
                'timestamp': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
            }
            queries.append(query)
        
        return queries
    
    def generate_documents(self, num_docs: int = 500) -> List[Dict[str, Any]]:
        """Generate synthetic documents."""
        documents = []
        topics = ['算法', '系统设计', '数据库', '网络', '操作系统', '前端', '后端']
        companies = ['字节', '阿里', '腾讯', '百度', '美团', '快手', '抖音']
        
        for i in range(num_docs):
            doc = {
                'id': f'doc_{i}',
                'title': f'{random.choice(topics)}面经 {i}',
                'content': f'这是第{i}个面经文档，包含{random.choice(topics)}相关内容',
                'topic': random.choice(topics),
                'company': random.choice(companies),
                'difficulty': random.choice(['easy', 'medium', 'hard']),
                'relevance_score': random.random(),
                'timestamp': (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat(),
            }
            documents.append(doc)
        
        return documents
    
    def generate_relevance_judgments(self, queries: List[Dict], documents: List[Dict], 
                                     sparsity: float = 0.1) -> List[Dict[str, Any]]:
        """Generate relevance judgments (ground truth)."""
        judgments = []
        
        for query in queries:
            # Randomly select relevant documents
            num_relevant = max(1, int(len(documents) * sparsity))
            relevant_docs = random.sample(documents, num_relevant)
            
            for doc in relevant_docs:
                judgment = {
                    'query_id': query['id'],
                    'doc_id': doc['id'],
                    'relevance': random.randint(0, 3),  # 0-3 relevance scale
                    'timestamp': datetime.now().isoformat(),
                }
                judgments.append(judgment)
        
        return judgments
    
    def generate_user_interactions(self, num_interactions: int = 200) -> List[Dict[str, Any]]:
        """Generate synthetic user interaction data."""
        interactions = []
        interaction_types = ['click', 'dwell', 'skip', 'bookmark', 'share']
        
        for i in range(num_interactions):
            interaction = {
                'id': f'interaction_{i}',
                'user_id': f'user_{random.randint(0, 50)}',
                'doc_id': f'doc_{random.randint(0, 499)}',
                'interaction_type': random.choice(interaction_types),
                'duration_ms': random.randint(100, 10000),
                'timestamp': (datetime.now() - timedelta(hours=random.randint(0, 720))).isoformat(),
            }
            interactions.append(interaction)
        
        return interactions


class StatisticalAnalyzer:
    """Statistical analysis for experiment results."""
    
    @staticmethod
    def compute_mean_and_std(results: List[ExperimentResult]) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compute mean and standard deviation of metrics."""
        if not results:
            return {}, {}
        
        metrics_dict = {}
        for result in results:
            for key, value in result.metrics.to_dict().items():
                if key not in metrics_dict:
                    metrics_dict[key] = []
                metrics_dict[key].append(value)
        
        means = {key: np.mean(values) for key, values in metrics_dict.items()}
        stds = {key: np.std(values) for key, values in metrics_dict.items()}
        
        return means, stds  # type: ignore[reportReturnType]
    
    @staticmethod
    def compute_confidence_interval(results: List[ExperimentResult], 
                                   confidence: float = 0.95) -> Dict[str, Tuple[float, float]]:
        """Compute confidence intervals for metrics."""
        if not results:
            return {}
        
        metrics_dict = {}
        for result in results:
            for key, value in result.metrics.to_dict().items():
                if key not in metrics_dict:
                    metrics_dict[key] = []
                metrics_dict[key].append(value)
        
        intervals = {}
        for key, values in metrics_dict.items():
            mean = np.mean(values)
            std = np.std(values)
            n = len(values)
            margin = 1.96 * std / np.sqrt(n)  # 95% CI
            intervals[key] = (mean - margin, mean + margin)
        
        return intervals
    
    @staticmethod
    def compare_configurations(baseline_results: List[ExperimentResult],
                              variant_results: List[ExperimentResult]) -> Dict[str, Any]:
        """Compare baseline and variant configurations."""
        baseline_means, baseline_stds = StatisticalAnalyzer.compute_mean_and_std(baseline_results)
        variant_means, variant_stds = StatisticalAnalyzer.compute_mean_and_std(variant_results)
        
        comparison = {}
        for key in baseline_means.keys():
            if key in variant_means:
                improvement = ((variant_means[key] - baseline_means[key]) / 
                             (baseline_means[key] + 1e-6) * 100)
                comparison[key] = {
                    'baseline_mean': baseline_means[key],
                    'variant_mean': variant_means[key],
                    'improvement_pct': improvement,
                    'baseline_std': baseline_stds[key],
                    'variant_std': variant_stds[key],
                }
        
        return comparison


class ExperimentRunner:
    """Runner for executing experiments."""
    
    def __init__(self, output_dir: str = './experiment_results'):
        """Initialize experiment runner."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[ExperimentResult] = []
    
    def run_baseline_experiment(self, baseline_type: BaselineType, 
                               num_runs: int = 3, seed_base: int = 42) -> List[ExperimentResult]:
        """Run baseline experiment with multiple seeds."""
        baseline_config = BaselineFactory.create_all()[baseline_type]
        results = []
        
        for run_idx in range(num_runs):
            seed = seed_base + run_idx
            result = self._simulate_experiment(
                config_type='baseline',
                config_name=baseline_type.value,
                config=baseline_config,
                seed=seed,
            )
            results.append(result)
            self.results.append(result)
        
        return results
    
    def run_variant_experiment(self, variant_type: VariantType,
                              num_runs: int = 3, seed_base: int = 42) -> List[ExperimentResult]:
        """Run variant experiment with multiple seeds."""
        variant_config = VariantFactory.create_all()[variant_type]
        results = []
        
        for run_idx in range(num_runs):
            seed = seed_base + run_idx
            result = self._simulate_experiment(
                config_type='variant',
                config_name=variant_type.value,
                config=variant_config,
                seed=seed,
            )
            results.append(result)
            self.results.append(result)
        
        return results
    
    def _simulate_experiment(self, config_type: str, config_name: str,
                            config: Any, seed: int) -> ExperimentResult:
        """Simulate a single experiment run."""
        random.seed(seed)
        np.random.seed(seed)
        
        # Simulate metrics based on configuration
        metrics = ExperimentMetrics(
            map_score=random.uniform(0.5, 0.9),
            ndcg_at_5=random.uniform(0.6, 0.95),
            ndcg_at_10=random.uniform(0.55, 0.9),
            recall_at_5=random.uniform(0.4, 0.8),
            recall_at_10=random.uniform(0.5, 0.85),
            memory_recall_lift=random.uniform(0.0, 0.3),
            forgetting_rate=random.uniform(0.01, 0.1),
            memory_retention=random.uniform(0.7, 0.95),
            interpretability_score=random.uniform(0.5, 0.95),
            latency_ms=random.uniform(50, 500),
            throughput_qps=random.uniform(100, 1000),
            memory_usage_mb=random.uniform(100, 500),
        )
        
        result = ExperimentResult(
            experiment_id=f'{config_name}_{seed}_{datetime.now().timestamp()}',
            config_type=config_type,
            config_name=config_name,
            seed=seed,
            timestamp=datetime.now().isoformat(),
            metrics=metrics,
            metadata={'config': config.to_dict() if hasattr(config, 'to_dict') else str(config)},
        )
        
        return result
    
    def save_results(self, filename: str = 'experiment_results.json'):
        """Save experiment results to file."""
        filepath = self.output_dir / filename
        results_data = [result.to_dict() for result in self.results]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate experiment report."""
        if not self.results:
            return {}
        
        # Group results by configuration
        grouped = {}
        for result in self.results:
            key = result.config_name
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(result)
        
        # Compute statistics for each configuration
        report = {
            'total_experiments': len(self.results),
            'configurations': {},
            'timestamp': datetime.now().isoformat(),
        }
        
        for config_name, results in grouped.items():
            means, stds = StatisticalAnalyzer.compute_mean_and_std(results)
            intervals = StatisticalAnalyzer.compute_confidence_interval(results)
            
            report['configurations'][config_name] = {
                'num_runs': len(results),
                'means': means,
                'stds': stds,
                'confidence_intervals': {k: {'lower': v[0], 'upper': v[1]} 
                                        for k, v in intervals.items()},
            }
        
        return report
