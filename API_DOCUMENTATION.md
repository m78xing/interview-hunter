# Interview Hunter Optimization System - API Documentation

## Overview

The Interview Hunter Optimization System provides four core modules for intelligent interview preparation:

1. **ContextStore** - Session-level context management with versioning
2. **MemoryEngine** - Multi-dimensional memory model with adaptive decay
3. **RagManager** - Multi-path retrieval with RRF fusion
4. **DataContracts** - Data governance and validation framework
5. **ExperimentFramework** - Rigorous experimental evaluation

---

## ContextStore API

### Purpose
Manages session-level context snapshots with persistent storage and version control.

### Key Classes

#### ContextSnapshot
```python
@dataclass
class ContextSnapshot:
    snapshot_id: str
    session_id: str
    user_id: str
    context_data: Dict[str, Any]
    timestamp: str
    version: int
```

#### ContextStore
```python
class ContextStore:
    def __init__(self, storage_dir: str = './context_storage')
    def create_snapshot(self, context_data: Dict[str, Any]) -> ContextSnapshot
    def get_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]
    def list_snapshots(self, session_id: str) -> List[ContextSnapshot]
    def get_manifest(self, session_id: str) -> Optional[ContextManifest]
    def inject_context(self, snapshot_id: str, prompt: str) -> str
```

### Usage Example
```python
from src.core import ContextStore

store = ContextStore(storage_dir='./context_storage')

context_data = {
    'user_id': 'user_123',
    'session_id': 'session_456',
    'current_topic': 'algorithms',
    'difficulty_level': 'medium',
    'recent_mistakes': ['binary search', 'dynamic programming'],
}

snapshot = store.create_snapshot(context_data)
print(f"Created snapshot: {snapshot.snapshot_id}")

retrieved = store.get_snapshot(snapshot.snapshot_id)
print(f"Context: {retrieved.context_data}")

injected_prompt = store.inject_context(snapshot.snapshot_id, "Help me with this problem")
print(f"Injected prompt: {injected_prompt}")
```

### Key Features
- Persistent storage with SQLite backend
- Version control for context snapshots
- Manifest management for session tracking
- Dynamic prompt injection with context awareness

---

## MemoryEngine API

### Purpose
Implements an 8-dimensional memory model with adaptive decay and cross-session consolidation.

### Memory Dimensions
```python
class MemoryDimension(Enum):
    RECENCY = 'recency'              # How recently accessed
    FREQUENCY = 'frequency'          # How often accessed
    DIFFICULTY = 'difficulty'        # Problem difficulty
    FATIGUE = 'fatigue'              # User fatigue level
    MOOD = 'mood'                    # User mood/motivation
    TIME_OF_DAY = 'time_of_day'      # Time of day accessed
    TOPIC_IMPORTANCE = 'topic_importance'  # Topic importance
    WEAK_TAGS = 'weak_tags'          # Weak knowledge areas
```

### Key Classes

#### MemoryEntry
```python
@dataclass
class MemoryEntry:
    user_id: str
    content_id: str
    content_type: str
    dimensions: Dict[MemoryDimension, float]
    timestamp: str
    metadata: Dict[str, Any]
```

#### MemoryEngine
```python
class MemoryEngine:
    def __init__(self, storage_dir: str = './memory_storage')
    def add_entry(self, user_id: str, entry: MemoryEntry) -> None
    def get_profile(self, user_id: str) -> Optional[MemoryProfile]
    def compute_memory_score(self, user_id: str, content_id: str) -> float
    def decay_memories(self, user_id: str, decay_rate: float = 0.1) -> None
    def consolidate_memories(self, user_id: str) -> MemoryProfile
    def export_memory(self, user_id: str) -> Dict[str, Any]
    def import_memory(self, user_id: str, data: Dict[str, Any]) -> None
```

### Usage Example
```python
from src.core import MemoryEngine, MemoryEntry, MemoryDimension

engine = MemoryEngine(storage_dir='./memory_storage')

entry = MemoryEntry(
    user_id='user_123',
    content_id='problem_456',
    content_type='question',
    dimensions={
        MemoryDimension.RECENCY: 0.9,
        MemoryDimension.FREQUENCY: 0.7,
        MemoryDimension.DIFFICULTY: 0.8,
        MemoryDimension.FATIGUE: 0.3,
    }
)

engine.add_entry('user_123', entry)

score = engine.compute_memory_score('user_123', 'problem_456')
print(f"Memory score: {score:.2f}")

profile = engine.get_profile('user_123')
print(f"Total interactions: {profile.total_interactions}")

engine.decay_memories('user_123', decay_rate=0.1)

consolidated = engine.consolidate_memories('user_123')
print(f"Consolidated profile: {consolidated}")
```

### Key Features
- 8-dimensional memory model for nuanced tracking
- Adaptive decay with configurable rates
- Cross-session memory consolidation
- Memory export/import for portability
- Weight management for dimension importance

---

## RagManager API

### Purpose
Implements multi-path retrieval with RRF (Reciprocal Rank Fusion) for intelligent document ranking.

### Retrieval Paths
- **semantic**: Embedding-based semantic similarity
- **keyword**: BM25 keyword matching
- **recent**: Recency-based ranking
- **company**: Company-specific document ranking
- **tags**: Tag-based document matching

### Key Classes

#### RetrievalPath
```python
@dataclass
class RetrievalPath:
    path_name: str
    weight: float
    enabled: bool
    config: Dict[str, Any]
```

#### RagManager
```python
class RagManager:
    def __init__(self, storage_dir: str = './rag_storage')
    def add_document(self, document: Dict[str, Any]) -> None
    def retrieve(self, query: str, user_id: Optional[str] = None, 
                 top_k: int = 10) -> List[Dict[str, Any]]
    def set_path_weight(self, path_name: str, weight: float) -> None
    def get_path_weights(self) -> Dict[str, float]
    def explain_ranking(self, query: str, doc_id: str) -> Dict[str, Any]
    def update_path_weights(self, weights: Dict[str, float]) -> None
```

### Usage Example
```python
from src.core import RagManager

manager = RagManager(storage_dir='./rag_storage')

documents = [
    {
        'id': 'doc_1',
        'text': 'Binary search algorithm explanation',
        'topic': 'algorithms',
        'company': 'google',
        'tags': ['search', 'binary', 'interview'],
    },
    {
        'id': 'doc_2',
        'text': 'System design for distributed cache',
        'topic': 'systems',
        'company': 'amazon',
        'tags': ['cache', 'distributed', 'design'],
    },
]

for doc in documents:
    manager.add_document(doc)

results = manager.retrieve('binary search', user_id='user_123', top_k=5)
for result in results:
    print(f"Doc: {result['id']}, Score: {result['score']:.2f}")

explanation = manager.explain_ranking('binary search', 'doc_1')
print(f"Ranking explanation: {explanation}")

manager.set_path_weight('semantic', 0.4)
manager.set_path_weight('keyword', 0.3)
manager.set_path_weight('recent', 0.2)
manager.set_path_weight('company', 0.05)
manager.set_path_weight('tags', 0.05)
```

### Key Features
- 5-path retrieval system for comprehensive coverage
- RRF fusion for combining multiple ranking signals
- Path weight customization and adaptation
- Ranking explainability with path contribution breakdown
- Embedding cache for performance optimization

---

## DataContracts API

### Purpose
Provides data governance, validation, and schema migration framework.

### Key Classes

#### DataValidator
```python
class DataValidator:
    def validate(self, data: Dict[str, Any], contract_name: str) -> bool
    def validate_with_errors(self, data: Dict[str, Any], 
                            contract_name: str) -> Tuple[bool, List[str]]
    def register_contract(self, name: str, contract: DataContract) -> None
    def get_contract(self, name: str) -> Optional[DataContract]
```

#### DataContract
```python
@dataclass
class DataContract:
    name: str
    version: int
    fields: Dict[str, FieldSchema]
    required_fields: List[str]
    
    def validate(self, data: Dict[str, Any]) -> bool
    def migrate(self, data: Dict[str, Any], target_version: int) -> Dict[str, Any]
```

### Usage Example
```python
from src.core import DataValidator

validator = DataValidator()

context_snapshot = {
    'session_id': 'session_123',
    'user_id': 'user_456',
    'context_data': {'topic': 'algorithms'},
    'timestamp': '2024-01-15T10:30:00',
}

is_valid = validator.validate(context_snapshot, 'ContextSnapshot')
print(f"Valid: {is_valid}")

is_valid, errors = validator.validate_with_errors(context_snapshot, 'ContextSnapshot')
if not is_valid:
    print(f"Validation errors: {errors}")

memory_entry = {
    'user_id': 'user_123',
    'content_id': 'content_456',
    'content_type': 'question',
    'dimensions': {'recency': 0.8, 'frequency': 0.6},
    'timestamp': '2024-01-15T10:30:00',
}

is_valid = validator.validate(memory_entry, 'MemoryEntry')
print(f"Valid: {is_valid}")
```

### Key Features
- Runtime validation with type checking
- Range and enum validation
- Schema migration framework
- Custom contract registration
- Detailed error reporting

---

## ExperimentFramework API

### Purpose
Provides baseline definitions, variant configurations, and statistical analysis for rigorous experiments.

### Baseline Configurations
- **B0**: Context off, Memory off, Single-path RAG
- **B1**: Context on, Memory on, Single-path RAG
- **B2**: Context on, Memory on, Multi-path RAG (no adaptive weights)

### Variant Configurations
- **V1**: Adaptive weights for RAG paths
- **V2**: Explainable ranking outputs
- **V3**: Robustness tests (noisy signals, drifted preferences)

### Key Classes

#### ExperimentRunner
```python
class ExperimentRunner:
    def __init__(self, output_dir: str = './experiment_results')
    def run_baseline_experiment(self, baseline_type: BaselineType,
                               num_runs: int = 3, seed_base: int = 42) -> List[ExperimentResult]
    def run_variant_experiment(self, variant_type: VariantType,
                              num_runs: int = 3, seed_base: int = 42) -> List[ExperimentResult]
    def save_results(self, filename: str = 'experiment_results.json') -> Path
    def generate_report(self) -> Dict[str, Any]
```

#### DataGenerator
```python
class DataGenerator:
    def __init__(self, seed: int = 42)
    def generate_queries(self, num_queries: int = 100) -> List[Dict[str, Any]]
    def generate_documents(self, num_docs: int = 500) -> List[Dict[str, Any]]
    def generate_relevance_judgments(self, queries: List[Dict],
                                    documents: List[Dict],
                                    sparsity: float = 0.1) -> List[Dict[str, Any]]
    def generate_user_interactions(self, num_interactions: int = 200) -> List[Dict[str, Any]]
```

#### StatisticalAnalyzer
```python
class StatisticalAnalyzer:
    @staticmethod
    def compute_mean_and_std(results: List[ExperimentResult]) -> Tuple[Dict, Dict]
    
    @staticmethod
    def compute_confidence_interval(results: List[ExperimentResult],
                                   confidence: float = 0.95) -> Dict[str, Tuple[float, float]]
    
    @staticmethod
    def compare_configurations(baseline_results: List[ExperimentResult],
                              variant_results: List[ExperimentResult]) -> Dict[str, Any]
```

### Usage Example
```python
from src.core import (
    ExperimentRunner, DataGenerator, StatisticalAnalyzer,
    BaselineType, VariantType
)

runner = ExperimentRunner(output_dir='./experiment_results')

b0_results = runner.run_baseline_experiment(
    baseline_type=BaselineType.B0,
    num_runs=3,
    seed_base=42
)

v1_results = runner.run_variant_experiment(
    variant_type=VariantType.V1,
    num_runs=3,
    seed_base=42
)

comparison = StatisticalAnalyzer.compare_configurations(b0_results, v1_results)
for metric, stats in comparison.items():
    improvement = stats['improvement_pct']
    print(f"{metric}: {improvement:+.2f}% improvement")

report = runner.generate_report()
runner.save_results('experiment_results.json')

gen = DataGenerator(seed=42)
queries = gen.generate_queries(num_queries=100)
documents = gen.generate_documents(num_docs=500)
judgments = gen.generate_relevance_judgments(queries, documents)
interactions = gen.generate_user_interactions(num_interactions=200)
```

### Key Features
- Predefined baseline and variant configurations
- Reproducible data generation with seed control
- Statistical analysis with confidence intervals
- Automatic report generation
- Experiment result persistence

---

## Integration Patterns

### Pattern 1: Full Pipeline
```python
from src.core import ContextStore, MemoryEngine, RagManager

store = ContextStore()
memory = MemoryEngine()
rag = RagManager()

context = store.create_snapshot({'user_id': 'user_123', 'topic': 'algorithms'})

results = rag.retrieve('binary search', user_id='user_123')

for result in results:
    entry = MemoryEntry(
        user_id='user_123',
        content_id=result['id'],
        content_type='document',
        dimensions={MemoryDimension.RECENCY: 1.0}
    )
    memory.add_entry('user_123', entry)
```

### Pattern 2: Experiment Evaluation
```python
from src.core import ExperimentRunner, BaselineType, VariantType

runner = ExperimentRunner()

baseline_results = runner.run_baseline_experiment(BaselineType.B2, num_runs=5)
variant_results = runner.run_variant_experiment(VariantType.V1, num_runs=5)

comparison = StatisticalAnalyzer.compare_configurations(baseline_results, variant_results)
report = runner.generate_report()
```

### Pattern 3: Data Validation
```python
from src.core import DataValidator

validator = DataValidator()

data = {'user_id': 'user_123', 'content_id': 'content_456', ...}
is_valid, errors = validator.validate_with_errors(data, 'MemoryEntry')

if not is_valid:
    print(f"Validation failed: {errors}")
```

---

## Performance Characteristics

| Operation | Latency | Throughput | Memory |
|-----------|---------|-----------|--------|
| ContextStore.create_snapshot | ~1-2ms | 500-1000 ops/sec | ~0.5MB per 1000 ops |
| MemoryEngine.add_entry | ~0.5-1ms | 1000-2000 ops/sec | ~0.3MB per 1000 ops |
| RagManager.retrieve | ~50-100ms | 10-20 ops/sec | ~1-2MB per query |
| DataValidator.validate | ~0.1-0.5ms | 2000-10000 ops/sec | <0.1MB |

---

## Error Handling

All modules follow consistent error handling patterns:

```python
try:
    result = manager.retrieve('query')
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Runtime error: {e}")
```

---

## Best Practices

1. **Always use context snapshots** for session management
2. **Regularly decay memories** to maintain relevance
3. **Validate data** before storing with DataContracts
4. **Use multiple retrieval paths** for comprehensive results
5. **Run experiments with multiple seeds** for statistical significance
6. **Monitor performance** with benchmarks
7. **Implement failure recovery** for production systems

---

## Troubleshooting

### Issue: Low retrieval quality
- Check RAG path weights are balanced
- Verify documents are properly indexed
- Review memory scores for ranking bias

### Issue: Memory bloat
- Increase decay rate for older entries
- Consolidate memories regularly
- Archive old sessions

### Issue: Validation failures
- Check data schema matches contract version
- Verify required fields are present
- Review field value ranges

---

## Version History

- **v1.0** (2024-01-15): Initial release with 4 core modules
- **v1.1** (2024-01-20): Added ExperimentFramework
- **v1.2** (2024-01-25): Added performance benchmarks and integration tests
