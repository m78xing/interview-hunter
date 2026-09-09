# 优化快速参考指南

## 新增模块使用指南

### 1. ContextStore - 上下文管理

```python
from src.core import ContextStore

# 初始化
context_store = ContextStore(storage_dir="./memory/contexts")

# 保存上下文
context = {
    'summary': '用户正在学习 Python 基础',
    'tokens': 150,
    'source': 'user',
    'metadata': {'topic': 'python'}
}
context_store.save_context('session_1', context, version=1)

# 加载最新上下文
latest = context_store.load_latest_context('session_1')

# 注入到 prompt
template = "Context: {context_summary}, Tokens: {context_tokens}"
injected = context_store.inject_context_into_prompt(template, 'session_1')

# 获取历史
history = context_store.get_context_history('session_1', limit=10)
```

### 2. MemoryEngine - 多维记忆

```python
from src.core import MemoryEngine, MemoryDimension

# 初始化
memory_engine = MemoryEngine(storage_dir="./memory/engine")

# 更新记忆
memory_engine.update_memory(
    session_id='session_1',
    card_id='card_1',
    dimension=MemoryDimension.RECENCY.value,
    value=0.9,
    weight=1.0
)

# 获取记忆
entries = memory_engine.get_memory('session_1', 'card_1')

# 生成摘要
summary = memory_engine.summarize_memory('session_1')

# 设置维度权重
weights = {
    MemoryDimension.RECENCY.value: 0.35,
    MemoryDimension.FREQUENCY.value: 0.25
}
memory_engine.set_memory_weights('session_1', weights)

# 导出/导入
exported = memory_engine.export_memory('session_1')
memory_engine.import_memory('session_2', exported)
```

### 3. RagManager - 多路径检索

```python
from src.core import RagManager, RetrievalPath

# 初始化
rag_manager = RagManager(chroma_client, sqlite_client, embedding_provider)

# 多路径搜索
results = rag_manager.search(
    query='Python 装饰器原理',
    session_id='session_1',
    limit=10,
    company='字节跳动',
    tags=['python', 'advanced']
)

# 设置路径权重
weights = {
    RetrievalPath.SEMANTIC.value: 0.45,
    RetrievalPath.KEYWORD.value: 0.30
}
rag_manager.set_path_weights(weights)

# 获取结果解释
for result in results:
    explanation = rag_manager.explain_result(result)
    print(explanation)
```

### 4. DataValidator - 数据验证

```python
from src.core import DataValidator

# 初始化
validator = DataValidator()

# 验证数据
data = {
    'session_id': 'session_1',
    'version': 1,
    'summary': 'Test',
    'tokens': 100,
    'created_at': '2024-01-01T00:00:00',
    'source': 'test'
}

is_valid, errors = validator.validate('ContextSnapshot', data)
if not is_valid:
    print(f"Validation errors: {errors}")
```

## 集成到应用

### 在 app.py 中初始化

```python
from src.core import ContextStore, MemoryEngine, RagManager, DataValidator

def init_system():
    # ... 现有初始化代码 ...
    
    # 初始化新模块
    context_store = ContextStore()
    memory_engine = MemoryEngine()
    rag_manager = RagManager(chroma, sqlite, embedding_provider)
    data_validator = DataValidator()
    
    # 传递给 supervisor
    supervisor = SupervisorAgent(
        # ... 现有参数 ...
        context_store=context_store,
        memory_engine=memory_engine,
        rag_manager=rag_manager,
        data_validator=data_validator
    )
    
    return supervisor, settings, user_memory, event_bus
```

## 数据流示例

### 完整的学习会话流程

```python
# 1. 开始会话 - 加载上下文
context = context_store.load_latest_context('session_1')
prompt = context_store.inject_context_into_prompt(template, 'session_1')

# 2. 执行搜索 - 多路径检索
results = rag_manager.search(
    query=user_query,
    session_id='session_1',
    company=user_preference.target_company,
    tags=user_preference.weak_tags
)

# 3. 验证结果 - 数据契约检查
for result in results:
    is_valid, errors = data_validator.validate('RetrievalResult', result.to_dict())
    if not is_valid:
        logger.warning(f"Invalid result: {errors}")

# 4. 更新记忆 - 记录学习行为
memory_engine.update_memory(
    session_id='session_1',
    card_id=result.card_id,
    dimension=MemoryDimension.RECENCY.value,
    value=1.0
)

# 5. 保存上下文 - 记录会话状态
new_context = {
    'summary': f'用户学习了 {len(results)} 道题目',
    'tokens': count_tokens(results),
    'source': 'system'
}
context_store.save_context('session_1', new_context, version=2)
```

## 性能优化建议

### 1. 缓存策略
```python
# 缓存嵌入结果
rag_manager.refresh_embedding_cache(card_ids)

# 定期清理旧上下文
context_store.prune_old_contexts('session_1', keep_count=10)

# 合并旧记忆
memory_engine.consolidate_memory('session_1', keep_latest_n=100)
```

### 2. 批量操作
```python
# 批量导入记忆
for session_id in session_list:
    exported = memory_engine.export_memory(session_id)
    memory_engine.import_memory(f"{session_id}_backup", exported)
```

### 3. 监控与日志
```python
# 记录关键操作
logger.info(f"Context saved: session={session_id}, version={version}")
logger.info(f"Memory updated: dimension={dimension}, value={value}")
logger.info(f"Search completed: results={len(results)}, time={elapsed_time}ms")
```

## 常见问题

### Q: 如何处理上下文版本冲突？
A: ContextStore 自动管理版本号，每次保存时递增。使用 `load_context_by_version()` 加载特定版本。

### Q: 记忆衰减如何工作？
A: MemoryEngine 使用指数衰减：`decay = rate ^ (days_elapsed / interval)`。可通过 `decay_rate` 和 `decay_interval_days` 配置。

### Q: 如何自定义检索路径权重？
A: 使用 `rag_manager.set_path_weights(weights)` 动态调整权重。权重会影响 RRF 融合结果。

### Q: 数据验证失败怎么办？
A: 检查返回的 `errors` 列表，修复数据后重新验证。可使用 `SchemaMigration` 进行版本迁移。

## 测试命令

```bash
# 运行 ContextStore 测试
python -m pytest tests/test_context_store.py -v

# 运行 MemoryEngine 测试
python -m pytest tests/test_memory_engine.py -v

# 运行所有测试
python -m pytest tests/ -v

# 编译检查
python -m py_compile src/core/context_store.py
python -m py_compile src/core/memory_engine.py
python -m py_compile src/core/rag_manager.py
python -m py_compile src/core/data_contracts.py
```

## 文件位置速查

| 功能 | 文件 |
|------|------|
| 上下文管理 | `src/core/context_store.py` |
| 多维记忆 | `src/core/memory_engine.py` |
| 多路径检索 | `src/core/rag_manager.py` |
| 数据契约 | `src/core/data_contracts.py` |
| 测试 | `tests/test_*.py` |
| 计划文档 | `.sisyphus/plans/Plan-*.md` |
| 执行总结 | `.sisyphus/plans/EXECUTION_SUMMARY.md` |

---

**最后更新**: 2024-01-03
**版本**: 1.0
**状态**: 核心模块实现完成，待集成测试和文档完善
