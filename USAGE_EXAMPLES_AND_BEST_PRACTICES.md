# Interview Hunter Optimization - Usage Examples & Best Practices

## Table of Contents
1. [Quick Start](#quick-start)
2. [Common Use Cases](#common-use-cases)
3. [Best Practices](#best-practices)
4. [Performance Optimization](#performance-optimization)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Basic Setup
```python
from src.core import ContextStore, MemoryEngine, RagManager

store = ContextStore(storage_dir='./context_storage')
memory = MemoryEngine(storage_dir='./memory_storage')
rag = RagManager(storage_dir='./rag_storage')
```

---

## Common Use Cases

### Use Case 1: Track User Learning Progress

```python
from src.core import ContextStore, MemoryEngine, MemoryEntry, MemoryDimension
from datetime import datetime

user_id = 'user_123'
store = ContextStore()
memory = MemoryEngine()

context_data = {
    'user_id': user_id,
    'session_id': f'session_{datetime.now().timestamp()}',
    'current_topic': 'algorithms',
    'difficulty_level': 'medium',
    'session_duration_minutes': 45,
}

snapshot = store.create_snapshot(context_data)

for problem_id in ['problem_1', 'problem_2', 'problem_3']:
    entry = MemoryEntry(
        user_id=user_id,
        content_id=problem_id,
        content_type='problem',
        dimensions={
            MemoryDimension.RECENCY: 1.0,
            MemoryDimension.FREQUENCY: 0.5,
            MemoryDimension.DIFFICULTY: 0.7,
        }
    )
    memory.add_entry(user_id, entry)

profile = memory.get_profile(user_id)
print(f"Total problems solved: {profile.total_interactions}")
print(f"Average memory score: {profile.average_memory_score:.2f}")
```

### Use Case 2: Intelligent Document Retrieval

```python
from src.core import RagManager

rag = RagManager()

documents = [
    {
        'id': 'doc_1',
        'text': 'Binary search is a search algorithm...',
        'topic': 'algorithms',
        'company': 'google',
        'difficulty': 'medium',
    },
    {
        'id': 'doc_2',
        'text': 'Two pointer technique for array problems...',
        'topic': 'algorithms',
        'company': 'amazon',
        'difficulty': 'medium',
    },
]

for doc in documents:
    rag.add_document(doc)

results = rag.retrieve('binary search algorithm', user_id='user_123', top_k=5)

for rank, result in enumerate(results, 1):
    print(f"{rank}. {result['id']}: {result['score']:.2f}")

explanation = rag.explain_ranking('binary search algorithm', 'doc_1')
print(f"Ranking breakdown: {explanation}")
```

### Use Case 3: Cross-Session Memory Consolidation

```python
from src.core import MemoryEngine, MemoryEntry, MemoryDimension

memory = MemoryEngine()
user_id = 'user_123'

for session_idx in range(3):
    for problem_idx in range(5):
        entry = MemoryEntry(
            user_id=user_id,
            content_id=f'problem_{problem_idx}',
            content_type='problem',
            dimensions={
                MemoryDimension.RECENCY: 1.0 - (session_idx * 0.2),
                MemoryDimension.FREQUENCY: 0.5 + (session_idx * 0.1),
            }
        )
        memory.add_entry(user_id, entry)

consolidated = memory.consolidate_memories(user_id)
print(f"Consolidated entries: {len(consolidated.entries)}")
print(f"Total interactions: {consolidated.total_interactions}")

exported = memory.export_memory(user_id)
print(f"Exported memory size: {len(exported)} bytes")
```

### Use Case 4: Running Experiments

```python
from src.core import (
    ExperimentRunner, DataGenerator, StatisticalAnalyzer,
    BaselineType, VariantType
)

runner = ExperimentRunner(output_dir='./experiment_results')

print("Running baseline experiments...")
b0_results = runner.run_baseline_experiment(BaselineType.B0, num_runs=5)
b1_results = runner.run_baseline_experiment(BaselineType.B1, num_runs=5)
b2_results = runner.run_baseline_experiment(BaselineType.B2, num_runs=5)

print("Running variant experiments...")
v1_results = runner.run_variant_experiment(VariantType.V1, num_runs=5)
v2_results = runner.run_variant_experiment(VariantType.V2, num_runs=5)
v3_results = runner.run_variant_experiment(VariantType.V3, num_runs=5)

print("Analyzing results...")
comparison_v1 = StatisticalAnalyzer.compare_configurations(b2_results, v1_results)
comparison_v2 = StatisticalAnalyzer.compare_configurations(b2_results, v2_results)

for metric, stats in comparison_v1.items():
    improvement = stats['improvement_pct']
    print(f"V1 vs B2 - {metric}: {improvement:+.2f}%")

report = runner.generate_report()
runner.save_results('experiment_results.json')
```

### Use Case 5: Data Validation Pipeline

```python
from src.core import DataValidator

validator = DataValidator()

user_interactions = [
    {
        'user_id': 'user_123',
        'content_id': 'content_456',
        'content_type': 'question',
        'dimensions': {'recency': 0.9, 'frequency': 0.7},
        'timestamp': '2024-01-15T10:30:00',
    },
    {
        'user_id': 'user_123',
        'content_id': 'content_789',
        'content_type': 'question',
        'dimensions': {'recency': 0.8, 'frequency': 0.6},
        'timestamp': '2024-01-15T11:00:00',
    },
]

for interaction in user_interactions:
    is_valid, errors = validator.validate_with_errors(interaction, 'MemoryEntry')
    if is_valid:
        print(f"✓ Valid: {interaction['content_id']}")
    else:
        print(f"✗ Invalid: {interaction['content_id']}")
        for error in errors:
            print(f"  - {error}")
```

---

## Best Practices

### 1. Session Management
```python
from src.core import ContextStore
from datetime import datetime

store = ContextStore()

context_data = {
    'user_id': 'user_123',
    'session_id': f'session_{datetime.now().isoformat()}',
    'start_time': datetime.now().isoformat(),
    'device': 'mobile',
    'location': 'home',
}

snapshot = store.create_snapshot(context_data)

print(f"Session started: {snapshot.snapshot_id}")
```

### 2. Memory Maintenance
```python
from src.core import MemoryEngine

memory = MemoryEngine()

user_id = 'user_123'

memory.decay_memories(user_id, decay_rate=0.1)

profile = memory.get_profile(user_id)
if profile.total_interactions > 1000:
    consolidated = memory.consolidate_memories(user_id)
    print(f"Consolidated {len(consolidated.entries)} entries")
```

### 3. Retrieval Optimization
```python
from src.core import RagManager

rag = RagManager()

rag.set_path_weight('semantic', 0.4)
rag.set_path_weight('keyword', 0.3)
rag.set_path_weight('recent', 0.15)
rag.set_path_weight('company', 0.1)
rag.set_path_weight('tags', 0.05)

results = rag.retrieve('query', user_id='user_123', top_k=10)
```

### 4. Error Handling
```python
from src.core import ContextStore, DataValidator

store = ContextStore()
validator = DataValidator()

try:
    context_data = {'user_id': 'user_123', 'session_id': 'session_456'}
    is_valid, errors = validator.validate_with_errors(context_data, 'ContextSnapshot')
    
    if not is_valid:
        print(f"Validation errors: {errors}")
        return
    
    snapshot = store.create_snapshot(context_data)
except Exception as e:
    print(f"Error: {e}")
```

### 5. Reproducibility
```python
from src.core import DataGenerator

gen = DataGenerator(seed=42)

queries = gen.generate_queries(num_queries=100)
documents = gen.generate_documents(num_docs=500)
judgments = gen.generate_relevance_judgments(queries, documents)

gen2 = DataGenerator(seed=42)
queries2 = gen2.generate_queries(num_queries=100)

assert len(queries) == len(queries2)
assert queries[0]['id'] == queries2[0]['id']
```

---

## Performance Optimization

### 1. Batch Operations
```python
from src.core import MemoryEngine, MemoryEntry, MemoryDimension

memory = MemoryEngine()

entries = []
for i in range(1000):
    entry = MemoryEntry(
        user_id='user_123',
        content_id=f'content_{i}',
        content_type='question',
        dimensions={MemoryDimension.RECENCY: 0.9}
    )
    entries.append(entry)

for entry in entries:
    memory.add_entry('user_123', entry)
```

### 2. Caching
```python
from src.core import RagManager

rag = RagManager()

query = 'binary search'
results = rag.retrieve(query, user_id='user_123')

results_cached = rag.retrieve(query, user_id='user_123')
```

### 3. Memory Decay Scheduling
```python
from src.core import MemoryEngine
import schedule
import time

memory = MemoryEngine()

def decay_all_users():
    for user_id in ['user_1', 'user_2', 'user_3']:
        memory.decay_memories(user_id, decay_rate=0.05)

schedule.every().day.at("02:00").do(decay_all_users)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 4. Lazy Loading
```python
from src.core import MemoryEngine

memory = MemoryEngine()

profile = memory.get_profile('user_123')

if profile and profile.total_interactions > 100:
    consolidated = memory.consolidate_memories('user_123')
```

---

## Troubleshooting

### Problem: Low Retrieval Quality
**Symptoms**: Retrieved documents don't match query intent

**Solutions**:
1. Check RAG path weights are balanced
2. Verify documents are properly indexed
3. Review memory scores for ranking bias
4. Increase top_k to see more results

```python
from src.core import RagManager

rag = RagManager()

results = rag.retrieve('query', user_id='user_123', top_k=20)

for result in results:
    explanation = rag.explain_ranking('query', result['id'])
    print(f"{result['id']}: {explanation}")
```

### Problem: Memory Bloat
**Symptoms**: Slow memory operations, high memory usage

**Solutions**:
1. Increase decay rate for older entries
2. Consolidate memories regularly
3. Archive old sessions
4. Reduce memory dimensions

```python
from src.core import MemoryEngine

memory = MemoryEngine()

memory.decay_memories('user_123', decay_rate=0.2)

consolidated = memory.consolidate_memories('user_123')

exported = memory.export_memory('user_123')
```

### Problem: Validation Failures
**Symptoms**: Data validation errors when storing entries

**Solutions**:
1. Check data schema matches contract version
2. Verify required fields are present
3. Review field value ranges
4. Use validate_with_errors for detailed feedback

```python
from src.core import DataValidator

validator = DataValidator()

data = {'user_id': 'user_123', 'content_id': 'content_456'}
is_valid, errors = validator.validate_with_errors(data, 'MemoryEntry')

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### Problem: Slow Retrieval
**Symptoms**: Retrieval operations take >500ms

**Solutions**:
1. Reduce top_k parameter
2. Disable unused retrieval paths
3. Use embedding cache
4. Batch queries

```python
from src.core import RagManager

rag = RagManager()

rag.set_path_weight('semantic', 0.5)
rag.set_path_weight('keyword', 0.5)
rag.set_path_weight('recent', 0.0)
rag.set_path_weight('company', 0.0)
rag.set_path_weight('tags', 0.0)

results = rag.retrieve('query', user_id='user_123', top_k=5)
```

---

## Advanced Topics

### Custom Memory Dimensions
```python
from src.core import MemoryEngine, MemoryEntry, MemoryDimension

memory = MemoryEngine()

entry = MemoryEntry(
    user_id='user_123',
    content_id='content_456',
    content_type='question',
    dimensions={
        MemoryDimension.RECENCY: 0.9,
        MemoryDimension.FREQUENCY: 0.7,
        MemoryDimension.DIFFICULTY: 0.8,
        MemoryDimension.FATIGUE: 0.3,
        MemoryDimension.MOOD: 0.6,
        MemoryDimension.TIME_OF_DAY: 0.5,
        MemoryDimension.TOPIC_IMPORTANCE: 0.9,
        MemoryDimension.WEAK_TAGS: 0.4,
    }
)

memory.add_entry('user_123', entry)
```

### Experiment Reproducibility
```python
from src.core import DataGenerator, ExperimentRunner, BaselineType

gen = DataGenerator(seed=42)
runner = ExperimentRunner()

queries = gen.generate_queries(num_queries=100)
documents = gen.generate_documents(num_docs=500)

results = runner.run_baseline_experiment(BaselineType.B0, num_runs=3, seed_base=42)

runner.save_results('experiment_results.json')
```

---

## Summary

The Interview Hunter Optimization System provides:
- **ContextStore**: Session-level context management
- **MemoryEngine**: Multi-dimensional memory with adaptive decay
- **RagManager**: Multi-path retrieval with RRF fusion
- **DataContracts**: Data governance and validation
- **ExperimentFramework**: Rigorous experimental evaluation

Follow these best practices for optimal results:
1. Always validate data before storing
2. Regularly decay memories to maintain relevance
3. Use multiple retrieval paths for comprehensive results
4. Run experiments with multiple seeds for statistical significance
5. Monitor performance with benchmarks
6. Implement proper error handling
