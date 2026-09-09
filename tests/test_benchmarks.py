"""
Performance benchmarks for Interview Hunter optimization modules.

Measures latency, throughput, memory usage, and scalability.
"""

import time
import psutil
import tempfile
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.context_store import ContextStore
from src.core.memory_engine import MemoryEngine, MemoryEntry, MemoryDimension
from src.core.rag_manager import RagManager
from src.core.experiment_framework import DataGenerator


class BenchmarkResult:
    """Store benchmark results."""
    
    def __init__(self, name: str):
        self.name = name
        self.latency_ms = 0.0
        self.throughput_ops_per_sec = 0.0
        self.memory_mb = 0.0
        self.peak_memory_mb = 0.0
    
    def __str__(self):
        return (f"{self.name}: "
                f"latency={self.latency_ms:.2f}ms, "
                f"throughput={self.throughput_ops_per_sec:.0f} ops/sec, "
                f"memory={self.memory_mb:.2f}MB, "
                f"peak={self.peak_memory_mb:.2f}MB")


class PerformanceBenchmark:
    """Run performance benchmarks."""
    
    @staticmethod
    def measure_context_store_performance():
        """Benchmark ContextStore operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ContextStore(storage_dir=tmpdir)
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            start_time = time.time()
            num_operations = 1000
            
            for i in range(num_operations):
                context_data = {
                    'user_id': f'user_{i % 100}',
                    'session_id': f'session_{i}',
                    'topic': f'topic_{i % 10}',
                }
                store.create_snapshot(context_data)
            
            elapsed_time = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024
            
            result = BenchmarkResult("ContextStore.create_snapshot")
            result.latency_ms = (elapsed_time / num_operations) * 1000
            result.throughput_ops_per_sec = num_operations / elapsed_time
            result.memory_mb = final_memory - initial_memory
            result.peak_memory_mb = final_memory
            
            return result
    
    @staticmethod
    def measure_memory_engine_performance():
        """Benchmark MemoryEngine operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = MemoryEngine(storage_dir=tmpdir)
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            start_time = time.time()
            num_operations = 1000
            
            for i in range(num_operations):
                entry = MemoryEntry(
                    user_id=f'user_{i % 100}',
                    content_id=f'content_{i}',
                    content_type='question',
                    dimensions={
                        MemoryDimension.RECENCY: 0.9,
                        MemoryDimension.FREQUENCY: 0.7,
                    }
                )
                engine.add_entry(f'user_{i % 100}', entry)
            
            elapsed_time = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024
            
            result = BenchmarkResult("MemoryEngine.add_entry")
            result.latency_ms = (elapsed_time / num_operations) * 1000
            result.throughput_ops_per_sec = num_operations / elapsed_time
            result.memory_mb = final_memory - initial_memory
            result.peak_memory_mb = final_memory
            
            return result
    
    @staticmethod
    def measure_rag_manager_performance():
        """Benchmark RagManager operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RagManager(storage_dir=tmpdir)
            
            gen = DataGenerator(seed=42)
            documents = gen.generate_documents(num_docs=500)
            
            for doc in documents:
                manager.add_document(doc)
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            start_time = time.time()
            num_queries = 100
            
            for i in range(num_queries):
                manager.retrieve(f'query_{i}', user_id=f'user_{i % 10}')
            
            elapsed_time = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024
            
            result = BenchmarkResult("RagManager.retrieve")
            result.latency_ms = (elapsed_time / num_queries) * 1000
            result.throughput_ops_per_sec = num_queries / elapsed_time
            result.memory_mb = final_memory - initial_memory
            result.peak_memory_mb = final_memory
            
            return result
    
    @staticmethod
    def measure_data_generator_performance():
        """Benchmark DataGenerator operations."""
        gen = DataGenerator(seed=42)
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        start_time = time.time()
        queries = gen.generate_queries(num_queries=1000)
        documents = gen.generate_documents(num_docs=1000)
        judgments = gen.generate_relevance_judgments(queries, documents)
        interactions = gen.generate_user_interactions(num_interactions=1000)
        elapsed_time = time.time() - start_time
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        result = BenchmarkResult("DataGenerator.generate_all")
        result.latency_ms = elapsed_time * 1000
        result.throughput_ops_per_sec = (len(queries) + len(documents) + 
                                        len(judgments) + len(interactions)) / elapsed_time
        result.memory_mb = final_memory - initial_memory
        result.peak_memory_mb = final_memory
        
        return result
    
    @staticmethod
    def measure_memory_decay_performance():
        """Benchmark memory decay operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = MemoryEngine(storage_dir=tmpdir)
            
            for i in range(100):
                for j in range(50):
                    entry = MemoryEntry(
                        user_id=f'user_{i}',
                        content_id=f'content_{j}',
                        content_type='question',
                        dimensions={
                            MemoryDimension.RECENCY: 0.9,
                            MemoryDimension.FREQUENCY: 0.7,
                        }
                    )
                    engine.add_entry(f'user_{i}', entry)
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            start_time = time.time()
            num_users = 100
            
            for i in range(num_users):
                engine.decay_memories(f'user_{i}', decay_rate=0.1)
            
            elapsed_time = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024
            
            result = BenchmarkResult("MemoryEngine.decay_memories")
            result.latency_ms = (elapsed_time / num_users) * 1000
            result.throughput_ops_per_sec = num_users / elapsed_time
            result.memory_mb = final_memory - initial_memory
            result.peak_memory_mb = final_memory
            
            return result


class FailureRecoveryTest:
    """Test failure recovery mechanisms."""
    
    @staticmethod
    def test_context_store_recovery():
        """Test ContextStore recovery from failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ContextStore(storage_dir=tmpdir)
            
            context_data = {
                'user_id': 'user_123',
                'session_id': 'session_456',
                'topic': 'algorithms',
            }
            
            snapshot = store.create_snapshot(context_data)
            snapshot_id = snapshot.snapshot_id
            
            retrieved = store.get_snapshot(snapshot_id)
            assert retrieved is not None
            assert retrieved.context_data == context_data
            
            return True
    
    @staticmethod
    def test_memory_engine_recovery():
        """Test MemoryEngine recovery from failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = MemoryEngine(storage_dir=tmpdir)
            
            entry = MemoryEntry(
                user_id='user_123',
                content_id='content_456',
                content_type='question',
                dimensions={
                    MemoryDimension.RECENCY: 0.9,
                    MemoryDimension.FREQUENCY: 0.7,
                }
            )
            
            engine.add_entry('user_123', entry)
            
            profile = engine.get_profile('user_123')
            assert profile is not None
            assert len(profile.entries) > 0
            
            return True
    
    @staticmethod
    def test_rag_manager_recovery():
        """Test RagManager recovery from failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RagManager(storage_dir=tmpdir)
            
            doc = {
                'id': 'doc_123',
                'text': 'test document',
                'topic': 'algorithms',
            }
            
            manager.add_document(doc)
            
            results = manager.retrieve('test', user_id='user_123')
            assert results is not None
            
            return True


def run_all_benchmarks():
    """Run all benchmarks and print results."""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARKS")
    print("="*60 + "\n")
    
    benchmarks = [
        ("ContextStore", PerformanceBenchmark.measure_context_store_performance),
        ("MemoryEngine", PerformanceBenchmark.measure_memory_engine_performance),
        ("RagManager", PerformanceBenchmark.measure_rag_manager_performance),
        ("DataGenerator", PerformanceBenchmark.measure_data_generator_performance),
        ("MemoryDecay", PerformanceBenchmark.measure_memory_decay_performance),
    ]
    
    results = []
    for name, benchmark_func in benchmarks:
        try:
            result = benchmark_func()
            results.append(result)
            print(f"✓ {result}")
        except Exception as e:
            print(f"✗ {name}: {str(e)}")
    
    print("\n" + "="*60)
    print("FAILURE RECOVERY TESTS")
    print("="*60 + "\n")
    
    recovery_tests = [
        ("ContextStore Recovery", FailureRecoveryTest.test_context_store_recovery),
        ("MemoryEngine Recovery", FailureRecoveryTest.test_memory_engine_recovery),
        ("RagManager Recovery", FailureRecoveryTest.test_rag_manager_recovery),
    ]
    
    for name, test_func in recovery_tests:
        try:
            success = test_func()
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status}: {name}")
        except Exception as e:
            print(f"✗ FAIL: {name} - {str(e)}")
    
    print("\n" + "="*60 + "\n")
    
    return results


if __name__ == '__main__':
    run_all_benchmarks()
