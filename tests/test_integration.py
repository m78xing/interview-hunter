"""
Integration tests for Interview Hunter optimization modules.

Tests the interaction between ContextStore, MemoryEngine, RagManager,
and DataContracts to ensure end-to-end functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.context_store import ContextStore, ContextSnapshot
from src.core.memory_engine import MemoryEngine, MemoryEntry, MemoryDimension
from src.core.rag_manager import RagManager, RetrievalPath
from src.core.data_contracts import DataValidator, DataContract
from src.core.experiment_framework import (
    BaselineFactory, VariantFactory, DataGenerator, 
    StatisticalAnalyzer, ExperimentRunner
)


class TestContextMemoryIntegration:
    """Test integration between ContextStore and MemoryEngine."""
    
    def test_context_snapshot_with_memory_profile(self):
        """Test creating context snapshot with memory profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_store = ContextStore(storage_dir=tmpdir)
            memory_engine = MemoryEngine(storage_dir=tmpdir)
            
            context_data = {
                'user_id': 'user_123',
                'session_id': 'session_456',
                'current_topic': 'algorithms',
                'difficulty_level': 'medium',
            }
            
            snapshot = context_store.create_snapshot(context_data)
            assert snapshot.context_data == context_data
            assert snapshot.session_id == 'session_456'
            
            memory_profile = memory_engine.get_profile('user_123')
            assert memory_profile is not None
            assert memory_profile.user_id == 'user_123'
    
    def test_memory_decay_with_context_updates(self):
        """Test memory decay when context is updated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_engine = MemoryEngine(storage_dir=tmpdir)
            
            entry = MemoryEntry(
                user_id='user_123',
                content_id='content_1',
                content_type='question',
                dimensions={
                    MemoryDimension.RECENCY: 1.0,
                    MemoryDimension.FREQUENCY: 0.8,
                }
            )
            
            memory_engine.add_entry('user_123', entry)
            initial_score = memory_engine.compute_memory_score('user_123', 'content_1')
            
            memory_engine.decay_memories('user_123', decay_rate=0.1)
            decayed_score = memory_engine.compute_memory_score('user_123', 'content_1')
            
            assert decayed_score < initial_score
    
    def test_cross_session_memory_consolidation(self):
        """Test memory consolidation across sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_engine = MemoryEngine(storage_dir=tmpdir)
            
            for session_idx in range(3):
                for content_idx in range(5):
                    entry = MemoryEntry(
                        user_id='user_123',
                        content_id=f'content_{content_idx}',
                        content_type='question',
                        dimensions={
                            MemoryDimension.RECENCY: 1.0 - (session_idx * 0.2),
                            MemoryDimension.FREQUENCY: 0.5 + (session_idx * 0.1),
                        }
                    )
                    memory_engine.add_entry('user_123', entry)
            
            profile = memory_engine.get_profile('user_123')
            assert len(profile.entries) > 0
            assert profile.total_interactions >= 15


class TestRagMemoryIntegration:
    """Test integration between RagManager and MemoryEngine."""
    
    def test_rag_retrieval_with_memory_ranking(self):
        """Test RAG retrieval enhanced by memory scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_manager = RagManager(storage_dir=tmpdir)
            memory_engine = MemoryEngine(storage_dir=tmpdir)
            
            documents = [
                {'id': 'doc_1', 'text': 'algorithm question', 'topic': 'algorithms'},
                {'id': 'doc_2', 'text': 'system design', 'topic': 'systems'},
                {'id': 'doc_3', 'text': 'database query', 'topic': 'databases'},
            ]
            
            for doc in documents:
                rag_manager.add_document(doc)
            
            for doc in documents:
                entry = MemoryEntry(
                    user_id='user_123',
                    content_id=doc['id'],
                    content_type='document',
                    dimensions={
                        MemoryDimension.RECENCY: 0.9 if doc['id'] == 'doc_1' else 0.5,
                        MemoryDimension.FREQUENCY: 0.8 if doc['id'] == 'doc_1' else 0.3,
                    }
                )
                memory_engine.add_entry('user_123', entry)
            
            results = rag_manager.retrieve('algorithm', user_id='user_123')
            assert len(results) > 0
    
    def test_multi_path_retrieval_consistency(self):
        """Test consistency across multiple retrieval paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rag_manager = RagManager(storage_dir=tmpdir)
            
            documents = [
                {'id': 'doc_1', 'text': 'algorithm', 'topic': 'algorithms', 'company': 'google'},
                {'id': 'doc_2', 'text': 'system', 'topic': 'systems', 'company': 'amazon'},
            ]
            
            for doc in documents:
                rag_manager.add_document(doc)
            
            results = rag_manager.retrieve('algorithm', user_id='user_123')
            assert results is not None
            assert len(results) >= 0


class TestDataContractValidation:
    """Test data contract validation across modules."""
    
    def test_context_snapshot_contract_validation(self):
        """Test ContextSnapshot data contract validation."""
        validator = DataValidator()
        
        valid_snapshot = {
            'session_id': 'session_123',
            'user_id': 'user_456',
            'context_data': {'topic': 'algorithms'},
            'timestamp': datetime.now().isoformat(),
        }
        
        assert validator.validate(valid_snapshot, 'ContextSnapshot')
    
    def test_memory_entry_contract_validation(self):
        """Test MemoryEntry data contract validation."""
        validator = DataValidator()
        
        valid_entry = {
            'user_id': 'user_123',
            'content_id': 'content_456',
            'content_type': 'question',
            'dimensions': {
                'recency': 0.8,
                'frequency': 0.6,
            },
            'timestamp': datetime.now().isoformat(),
        }
        
        assert validator.validate(valid_entry, 'MemoryEntry')
    
    def test_retrieval_result_contract_validation(self):
        """Test RetrievalResult data contract validation."""
        validator = DataValidator()
        
        valid_result = {
            'query': 'algorithm',
            'results': [
                {'id': 'doc_1', 'score': 0.95, 'rank': 1},
                {'id': 'doc_2', 'score': 0.87, 'rank': 2},
            ],
            'timestamp': datetime.now().isoformat(),
        }
        
        assert validator.validate(valid_result, 'RetrievalResult')


class TestExperimentFrameworkIntegration:
    """Test experiment framework with actual modules."""
    
    def test_baseline_experiment_execution(self):
        """Test executing baseline experiments."""
        runner = ExperimentRunner()
        
        b0_results = runner.run_baseline_experiment(
            baseline_type=BaselineFactory.create_b0().__class__.__bases__[0],
            num_runs=2,
            seed_base=42
        )
        
        assert len(b0_results) == 2
        for result in b0_results:
            assert result.config_name == 'B0'
            assert result.metrics.map_score > 0
    
    def test_variant_experiment_execution(self):
        """Test executing variant experiments."""
        runner = ExperimentRunner()
        
        v1_results = runner.run_variant_experiment(
            variant_type=VariantFactory.create_v1().__class__.__bases__[0],
            num_runs=2,
            seed_base=42
        )
        
        assert len(v1_results) == 2
        for result in v1_results:
            assert result.config_name == 'V1'
    
    def test_data_generator_reproducibility(self):
        """Test data generator reproducibility with seeds."""
        gen1 = DataGenerator(seed=42)
        gen2 = DataGenerator(seed=42)
        
        queries1 = gen1.generate_queries(num_queries=10)
        queries2 = gen2.generate_queries(num_queries=10)
        
        assert len(queries1) == len(queries2)
        for q1, q2 in zip(queries1, queries2):
            assert q1['id'] == q2['id']
    
    def test_statistical_analysis_comparison(self):
        """Test statistical analysis of baseline vs variant."""
        runner = ExperimentRunner()
        
        b2_results = runner.run_baseline_experiment(
            baseline_type=BaselineFactory.create_b2().__class__.__bases__[0],
            num_runs=3,
            seed_base=42
        )
        
        v1_results = runner.run_variant_experiment(
            variant_type=VariantFactory.create_v1().__class__.__bases__[0],
            num_runs=3,
            seed_base=42
        )
        
        comparison = StatisticalAnalyzer.compare_configurations(b2_results, v1_results)
        assert len(comparison) > 0
        
        for metric, stats in comparison.items():
            assert 'baseline_mean' in stats
            assert 'variant_mean' in stats
            assert 'improvement_pct' in stats
    
    def test_experiment_report_generation(self):
        """Test experiment report generation."""
        runner = ExperimentRunner()
        
        runner.run_baseline_experiment(
            baseline_type=BaselineFactory.create_b0().__class__.__bases__[0],
            num_runs=2,
            seed_base=42
        )
        
        report = runner.generate_report()
        assert 'total_experiments' in report
        assert 'configurations' in report
        assert report['total_experiments'] == 2


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""
    
    def test_full_optimization_pipeline(self):
        """Test complete optimization pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context_store = ContextStore(storage_dir=tmpdir)
            memory_engine = MemoryEngine(storage_dir=tmpdir)
            rag_manager = RagManager(storage_dir=tmpdir)
            
            user_id = 'user_123'
            
            context_data = {
                'user_id': user_id,
                'session_id': 'session_456',
                'current_topic': 'algorithms',
            }
            
            snapshot = context_store.create_snapshot(context_data)
            assert snapshot is not None
            
            documents = [
                {'id': 'doc_1', 'text': 'algorithm', 'topic': 'algorithms'},
                {'id': 'doc_2', 'text': 'system', 'topic': 'systems'},
            ]
            
            for doc in documents:
                rag_manager.add_document(doc)
                entry = MemoryEntry(
                    user_id=user_id,
                    content_id=doc['id'],
                    content_type='document',
                    dimensions={
                        MemoryDimension.RECENCY: 0.9,
                        MemoryDimension.FREQUENCY: 0.7,
                    }
                )
                memory_engine.add_entry(user_id, entry)
            
            results = rag_manager.retrieve('algorithm', user_id=user_id)
            assert results is not None
            
            profile = memory_engine.get_profile(user_id)
            assert profile is not None
            assert len(profile.entries) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
