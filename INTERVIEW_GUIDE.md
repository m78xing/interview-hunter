# Interview Hunter 代码详解文档

> 面试官拷打指南 - 基于实际代码的架构、设计模式与常见问题

## 目录

1. [项目概览](#1-项目概览)
2. [系统架构](#2-系统架构)
3. [核心模块详解](#3-核心模块详解)
4. [设计模式](#4-设计模式)
5. [数据流与交互](#5-数据流与交互)
6. [关键算法](#6-关键算法)
7. [常见面试问题](#7-常见面试问题)

---

## 1. 项目概览

### 1.1 技术栈

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | Streamlit | Python Web 框架 |
| 存储 | SQLite + Chroma | 关系型 + 向量型 |
| LLM | DeepSeek API | 通过 httpx 调用 |
| 定时任务 | APScheduler | 心跳调度 |
| Agent | 自实现 | Supervisor 协调模式 |

### 1.2 模块结构 (实际代码)

```
src/
├── workflow/          # 采集流程工作流 (4个)
│   ├── supervisor.py      # 采集编排器
│   ├── collector.py      # 采集工作流
│   ├── analyzer.py       # 分析工作流
│   └── scheduler.py      # 调度工作流
├── agents/            # 对话学习 Agent (4个)
│   ├── learning_router.py # 意图路由
│   ├── anxiety_agent.py  # 焦虑缓解
│   ├── card_quiz_agent.py # 卡片问答
│   └── interview_agent.py # 面试模拟
├── core/              # 核心算法 (19个)
...
```
            )
```

**面试问题**:
- Q: 为什么用 APScheduler 而不是简单的 while True + sleep?
- A: APScheduler 支持 Cron 表达式、更精确的时间控制、持久化、异常处理

---

### 3.2 RagManager (多路召回 + RRF 融合)

**文件**: `src/core/rag_manager.py`

```python
class MultiPathRetrieval:
    def multi_path_search(self, query, company=None, tags=None, limit=10):
        retrieval_results = {}
        
        # 5种检索路径
        retrieval_results['semantic'] = self.retrieve_semantic(query, limit)
        retrieval_results['keyword'] = self.retrieve_keyword(query, limit)
        retrieval_results['recent'] = self.retrieve_recent(limit)
        
        if company:
            retrieval_results['company'] = self.retrieve_by_company(company, limit)
        
        if tags:
            retrieval_results['similar_tags'] = self.retrieve_similar_tags(tags, limit)
        
        # RRF 融合
        fused = self.fuse_with_rrf(retrieval_results, k=60)
        return fused[:limit]
```

**检索路径**:
1. **semantic**: Chroma 向量相似度
2. **keyword**: TF-IDF 词频匹配
3. **recent**: SQLite 时间排序
4. **company**: Chroma 标签过滤
5. **similar_tags**: 标签重叠度

---

### 3.3 SearchResultReranker (重排)

**文件**: `src/core/reranker.py`

```python
class SearchResultReranker:
    def rerank_results(self, results, weights=None):
        # weights: {
        #   'original': 0.3,      # 原始分数
        #   'retrievability': 0.25, # 遗忘曲线
        #   'weakness': 0.2,       # 薄弱点
        #   'preference': 0.15,    # 用户偏好
        #   'recency': 0.1        # 时效性
        # }
        
        final_score = (
            original_score * weights['original'] +
            rerank_score * (1 - weights['original'])
        )
```

**评分因子**:
- `retrievability`: 基于 SM-2 间隔计算
- `weakness`: 1 - 正确率
- `preference`: 用户偏好匹配度 (公司、标签、难度)
- `recency`: 30天内的时效性

---

### 3.4 EventBus (事件总线)

**文件**: `src/core/event_bus.py`

```python
class EventType(Enum):
    COLLECTION_STARTED = "collection_started"
    COLLECTION_COMPLETED = "collection_completed"
    CARD_ADDED = "card_added"
    REVIEW_SUBMITTED = "review_submitted"
    STRATEGY_ADJUSTED = "strategy_adjusted"
    ...

class EventBus:
    def publish(self, event_type, source, data):
        event = Event(event_type=event_type, ...)
        self.event_history.append(event)
        
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(event)
```

**观察者模式应用**: Supervisor 发布事件，各模块订阅处理

---

### 3.5 CheckpointManager (状态持久化)

**文件**: `src/core/checkpoint_manager.py`

```python
class CheckpointManager:
    def save_checkpoint(self, agent_name, state, metadata=None):
        checkpoint = AgentCheckpoint(
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            state=state,
            metadata=metadata or {}
        )
        # 保存为 JSON 文件
    
    def get_latest_checkpoint(self, agent_name):
        # 按修改时间排序，返回最新的
```

---

### 3.6 EmbeddingProvider (向量嵌入)

**文件**: `src/core/embedding_provider.py`

```python
class EmbeddingProviderFactory:
    _providers = {
        "openai": OpenAIEmbeddingProvider,
        "cohere": CohereEmbeddingProvider,
        "local": LocalEmbeddingProvider,   # sentence-transformers
        "mock": MockEmbeddingProvider,     # 哈希生成假向量
    }
    
    @classmethod
    def create(cls, config: EmbeddingConfig) -> EmbeddingProvider:
        provider_class = cls._providers.get(config.provider)
        return provider_class(config)
```

**面试问题**:
- Q: 为什么用工厂模式?
- A: 解耦 Embedding 提供者实现，便于切换/扩展模型

---

### 3.7 ContextStore (上下文存储)

**文件**: `src/core/context_store.py`

```python
class ContextStore:
    """支持会话级与跨会话上下文、版本控制"""
    
    def save_context(self, session_id, context, version):
        snapshot = ContextSnapshot(
            session_id=session_id,
            version=version,
            summary=context.get('summary', ''),
            ...
        )
        self.manifests[session_id].add_snapshot(snapshot)
    
    def load_latest_context(self, session_id):
        # 加载最新版本
    
    def inject_context_into_prompt(self, prompt_template, session_id):
        # 替换 {context_summary} 等占位符
```

---

### 3.8 MemoryEngine (多维记忆)

**文件**: `src/core/memory_engine.py`

```python
class MemoryDimension(Enum):
    RECENCY = "recency"        # 时效性 0.25
    FREQUENCY = "frequency"    # 频率 0.20
    DIFFICULTY = "difficulty"  # 难度 0.20
    FATIGUE = "fatigue"        # 疲劳 0.15
    MOOD = "mood"              # 心情 0.10
    TIME_OF_DAY = "time_of_day" # 时段 0.05
    TOPIC_IMPORTANCE = "topic_importance" # 0.03
    WEAK_TAGS = "weak_tags"    # 薄弱 0.02
```

**衰减函数**:
```python
decay_factor = decay_rate ** (days_elapsed / decay_interval_days)
value = entry.value * decay_factor
```

---

### 3.9 UserMemoryModule (用户长期记忆)

**文件**: `src/core/user_memory.py`

```python
@dataclass
class CrawlStrategy:
    priority_companies: List[str]  # 目标公司
    priority_tags: List[str]       # 重点标签
    avoid_tags: List[str]          # 回避标签
    difficulty_focus: str          # 难度聚焦

class UserMemoryModule:
    def record_learning(self, card_id, company, tags, quality, difficulty):
        # 更新统计: 正确/错误数、薄弱标签
        # 自动调整爬取策略
    
    def generate_keywords(self) -> List[str]:
        # 生成爬取关键字组合
```

---

### 3.10 SQLiteClient (关系存储)

**文件**: `src/storage/sqlite_client.py`

**表结构**:
```sql
cards: id, question, answer, company, position, tags, difficulty, source_url, source_platform, created_at

review_logs: id, card_id, reviewed_at, quality, time_taken

card_stats: card_id, total_reviews, correct_count, error_count, last_reviewed_at, ease_factor, interval_days

tag_stats: tag, total_reviews, correct_count, error_count, mastery_level
```

**SM-2 实现**:
```python
def update_ease_factor(card_id, quality):
    ef = old_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)
    interval = 1 if quality < 3 else max(1, old_interval * ef)
```

---

### 3.11 ChromaClient (向量存储)

**文件**: `src/storage/chroma_client.py`

```python
class ChromaClient:
    def search_similar(self, query_text, n_results=5):
        query_embedding = self._create_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        # 距离转相似度: score = 1 - distance
    
    def check_duplicate(self, text, threshold=0.92):
        # 超过阈值视为重复
```

---

## 4. 设计模式

### 4.1 工厂模式 (EmbeddingProviderFactory)

```python
EmbeddingProviderFactory.create(EmbeddingConfig(
    provider="openai",
    model="text-embedding-3-small"
))
```

### 4.2 观察者模式 (EventBus)

```python
event_bus.subscribe(EventType.CARD_ADDED, handler)
event_bus.publish(EventType.CARD_ADDED, "analyzer", {"card_id": "..."})
```

### 4.3 策略模式 (RagManager)

```python
# 运行时切换检索路径组合
retrieval_results['semantic'] = ...
retrieval_results['keyword'] = ...
```

### 4.4 责任链模式 (Supervisor)

```python
# 采集 → 分析 → 去重 → 存储 → 向量索引 → 邮件通知
```

---

## 5. 数据流与交互

### 5.1 采集流程

```
HeartbeatDriver (_execute_task)
    │
    ▼
Supervisor._run_collection_cycle()
    │
    ├─▶ CollectorWorkflow.collect()
    │      ├─▶ 牛客网爬虫
    │      ├─▶ 小红书爬虫
    │      └─▶ Mock fallback
    │
    ├─▶ AnalyzerWorkflow.analyze(raw_posts)
    │      ├─▶ LLM 提取 (DeepSeek API)
    │      └─▶ 规则提取 fallback
    │
    ├─▶ 去重检测 (Chroma)
    │
    ├─▶ SQLite insert_card()
    │
    ├─▶ Chroma add_card()
    │
    └─▶ EventBus.publish(COLLECTION_COMPLETED)
```

### 5.2 学习流程

```
User 打开学习页面
    │
    ▼
SchedulerWorkflow.start_session(target_company, limit)
    │
    ├─▶ SQLite.get_all_cards()
    │      └─▶ 按时间排序
    │
    └─▶ 返回卡片列表
    
    ▼
User 提交复习质量评分 (0-5)
    │
    ▼
SchedulerWorkflow.record_review(card_id, quality, time_taken)
    │
    ├─▶ SQLite.add_review_log()
    │
    ├─▶ SQLite.update_ease_factor() ← SM-2
    │
    ├─▶ 更新 tag_stats
    │
    └─▶ 检查阈值 → LLMAuditor.trigger_threshold_audit()
```

### 5.3 问答/检索流程

```
User 输入问题
    │
    ▼
RagManager.search(query)  ← 使用 rag_manager.py (已合并)
    │
    ├─▶ 语义检索 (Chroma)
    ├─▶ 关键词检索 (TF-IDF)
    ├─▶ 最近检索 (SQLite)
    ├─▶ 公司检索 (Chroma 过滤)
    └─▶ 标签检索 (重叠度)
    │
    ▼
RRF 融合 → Top-K
    │
    ▼
SearchResultReranker.rerank_results()
    │
    ├─▶ retrievability (遗忘曲线)
    ├─▶ weakness (薄弱点)
    ├─▶ preference (用户偏好)
    └─▶ recency (时效性)
    │
    ▼
返回重排后的结果
```

---

## 6. 关键算法

### 6.1 RRF (倒数排名融合) - RagManager 实现

```python
def _rrf_fusion(self, path_results: Dict[str, List[Tuple[str, float]]], k: int = 60) -> Dict[str, float]:
    rrf_scores = {}
    
    for path, results in path_results.items():
        weight = self.path_weights.get(path, 0.1)
        for rank, (card_id, score) in enumerate(results, 1):
            if card_id not in rrf_scores:
                rrf_scores[card_id] = 0
            rrf_scores[card_id] += weight * (1 / (k + rank))
    
    return rrf_scores
```

**优点**: 基于排名而非绝对分数，各路径公平融合

### 6.2 SM-2 遗忘曲线

```python
ease_factor = old_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
ease_factor = max(1.3, ease_factor)

if quality < 3:
    interval = 1  # 错误重置
else:
    interval = max(1, old_interval * ease_factor)
```

### 6.3 向量去重

```python
def check_duplicate(self, text, threshold=0.92):
    embedding = self._create_embedding(text)
    results = self.collection.query(query_embeddings=[embedding], n_results=1)
    
    similarity = 1 - results.distances[0][0]
    return similarity >= threshold
```

---

## 7. 常见面试问题

### 7.1 系统设计类

| 问题 | 答案要点 |
|------|----------|
| 为什么用 Supervisor 协调模式? | 解耦各Agent职责，统一调度，便于扩展 |
| 为什么同时用 SQLite 和 Chroma? | SQLite存结构化元数据+统计，Chroma做向量检索 |
| 如何保证数据一致性? | SQLite为主存储，Chroma为索引，事务保证 |
| 爬虫失败怎么办? | Mock数据fallback、邮件告警、错误重试 |

### 7.2 技术细节类

| 问题 | 答案要点 |
|------|----------|
| RRF vs 分数加权? | RRF基于排名，对各路径公平，避免极端值主导 |
| APScheduler优势? | Cron表达式、持久化、异常处理、线程安全 |
| Checkpoint设计考量? | 状态恢复、故障恢复、系统迁移 |
| 多路召回各路径作用? | 语义(向量)、关键词(TF-IDF)、最近(时间)、公司/标签(过滤) |

### 7.3 优化与扩展类

| 问题 | 答案要点 |
|------|----------|
| 如何提升检索质量? | 增加检索路径、调整RRF权重、添加重排层 |
| 冷启动问题? | Mock数据、规则提取、用户偏好初始化 |
| 推荐多样性? | diversity_penalty、recently_shown_tags追踪 |
| 多用户支持? | Session隔离、用户画像、偏好存储 |

### 7.4 编码实现类

| 问题 | 答案要点 |
|------|----------|
| 工厂模式好处? | 解耦创建逻辑，便于扩展新Provider |
| 观察者模式应用? | EventBus解耦事件生产者/消费者 |
| SM-2参数调优? | 最小EF=1.3，初始间隔=1天 |

---

## 附录: 核心类清单 (当前实际代码)

| 类名 | 文件 | 职责 |
|------|------|------|
| **Agent 层** | | |
| CollectionOrchestrator | workflow/supervisor.py | 编排器 - 采集流程总控 |
| CollectorWorkflow | workflow/collector.py | 采集 - 爬虫 |
| AnalyzerWorkflow | workflow/analyzer.py | 分析 - LLM提取卡片 |
| SchedulerWorkflow | workflow/scheduler.py | 调度 - 学习推荐 |
| LearningRouter | agents/learning_router.py | 入口 - 意图路由+关键字 |
| AnxietyAgent | agents/anxiety_agent.py | 焦虑缓解 |
| CardQuizAgent | agents/card_quiz_agent.py | 卡片问答 |
| InterviewAgent | agents/interview_agent.py | 面试模拟 |
| **Core 层** | | |
| HeartbeatDriver | core/heartbeat.py | 定时任务 |
| EventBus | core/event_bus.py | 事件驱动 |
| CheckpointManager | core/checkpoint_manager.py | 状态持久化 |
| EmbeddingProviderFactory | core/embedding_provider.py | 向量工厂 |
| RagManager | core/rag_manager.py | 多路召回+RRF |
| SearchResultReranker | core/reranker.py | 结果重排 |
| ContextStore | core/context_store.py | 上下文存储 |
| ContextManager | core/context_manager.py | 上下文摘要 |
| MemoryEngine | core/memory_engine.py | 多维记忆 |
| UserMemoryModule | core/user_memory.py | 用户长期记忆 |
| UserPreferenceStore | core/preference_store.py | 用户偏好 |
| RecommendationEngine | core/recommendation.py | 推荐引擎 |
| LLMAuditor | core/llm_audit.py | LLM审计 |
| DailyMissionManager | core/daily_mission.py | 每日任务 |
| **Storage 层** | | |
| SQLiteClient | storage/sqlite_client.py | 关系存储 |
| ChromaClient | storage/chroma_client.py | 向量存储 |

---

> 文档版本: 2026-04-11 (基于实际代码)
> 面试官: 🖐️ 还有问题吗?

---

## 📝 历史记录

### 2026-04-11 清理记录

**删除的冗余代码**:
- `src/core/multi_retrieval.py` - 功能与 `rag_manager.py` 重复，已合并
- `src/core/preference_crawler.py` - 只是 `UserMemoryModule` 的代理层，无实质逻辑

**修改的文件**:
- `src/agents/scheduler.py` - 改用 `RagManager` 替代 `MultiPathRetrieval`
- `src/core/__init__.py` - 清理导出

**当前模块数量**: 19 core + 8 agents + 2 storage