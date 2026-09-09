# Interview Hunter 模块设计

## 概述

两个核心模块：
1. **每日面经** - 每天基于记忆曲线选取10条
2. **对话学习** - 三Agent自动路由，LLM驱动

---

## 模块一：每日面经（Daily Mission）

### 1.1 数据模型

```python
@dataclass
class DailyMission:
    user_id: str
    date: str                    # 日期 "2026-04-03"
    card_ids: List[str]          # 选取的10条卡片ID
    is_locked: bool              # 是否锁定（当天不再改变）
    created_at: str
```

**存储方式**：SQLite 表 `daily_missions`

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT | 用户ID |
| date | TEXT | 日期 |
| card_ids | TEXT | JSON 列表 |
| is_locked | INTEGER | 0/1 锁定状态 |
| created_at | TEXT | 创建时间 |

### 1.2 选取逻辑（基于记忆曲线）

使用 SM-2 算法的间隔和易度因子来计算每张卡片的复习优先级。

```python
class DailyMissionManager:
    def select_daily_cards(self, user_id: str, limit: int = 10) -> List[str]:
        """
        选取逻辑（基于记忆曲线）：
        1. 从 SQLite 获取所有卡片
        2. 获取每张卡片的复习统计（interval, ease_factor, correct_count, total_reviews）
        3. 计算优先级分数：
           - retrievability: 可回忆性（interval越大越低）
           - weakness: 薄弱点（错误率越高越高）
           - priority = (1 - retrievability) * 0.6 + weakness * 0.4
        4. 按优先级排序，选取前10条
        5. 存入数据库，标记 is_locked=True
        """
```

**优先级计算公式**：

```python
# 1. 可回忆性分数（SM-2 算法）
retrievability = (1 - 0.5) * (2 ** (-interval / ease_factor)) + 0.5

# 2. 薄弱点分数
accuracy = correct_count / total_reviews if total_reviews > 0 else 0.5
weakness = 1 - accuracy

# 3. 综合优先级
priority_score = (1 - retrievability) * 0.6 + weakness * 0.4
```

**规则**：
- 每天凌晨检查日期变化，若日期变化 → 重新选取
- 选取后 `is_locked=True`，当天不再改变
- 可手动调用 `reset_daily()` 重置
- 新卡片（无复习记录）权重为 0.5，中等优先级

### 1.3 前端交互

```
┌─────────────────────────────┐
│  今日面经 (2026-04-03)      │
├─────────────────────────────┤
│  基于记忆曲线选取            │
├─────────────────────────────┤
│  1. [算法] 快速排序... [遗忘:高]│
│  2. [系统设计] 分布式事务...  │
│  ...                        │
│  (共10条，已锁定)            │
├─────────────────────────────┤
│  [开始复习] [重置今日]       │
└─────────────────────────────┘
```

---

## 模块二：对话学习（Chat Learning）

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    对话学习入口                              │
│                   LearningRouter                            │
│              (自动判断意图，分发到对应Agent)                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ 焦虑缓解Agent │   │ 卡片问答Agent │   │ 面试模拟Agent │
│ (最简单)    │   │ (中等)      │   │ (最复杂)    │
└─────────────┘   └─────────────┘   └─────────────┘
```

### 2.2 LearningRouter（意图识别 + 关键字更新）

入口路由，负责判断用户意图，将对话分发到对应的Agent。同时处理关键字更新（不需要专门Agent）。

```python
class LearningRouter:
    """对话学习入口 - 自动判断用户意图并路由"""
    
    def route(self, user_message: str, current_mode: str = None) -> str:
        """
        判断用户意图：
        - anxiety_relief: 焦虑缓解 / 闲聊
        - card_quiz: 卡片问答
        - interview_sim: 面试模拟
        - modify_keywords: 修改爬虫关键字
        """
```

**意图识别 Prompt**：

```
你是一个对话学习路由器。

用户消息：{user_message}

判断用户想要什么模式（返回JSON）：
{
    "mode": "anxiety_relief" | "card_quiz" | "interview_sim" | "modify_keywords",
    "keywords": "关键字（仅 modify_keywords 时有值）",
    "action": "add" | "delete" | "replace" | "none"（仅 modify_keywords 时有值）,
    "confidence": 0.0-1.0,
    "reason": "理由"
}

模式说明：
- anxiety_relief: 用户在倾诉消极情绪、压力、焦虑，或者只是闲聊/打招呼
- card_quiz: 用户想学习/复习面经卡片，问答形式
- interview_sim: 用户想模拟面试，会提供简历或要求开始面试
- modify_keywords: 用户想修改爬虫关键字（"改成搜索xxx"、"加上xxx"、"删除xxx"等）

只返回 JSON。
```

### 2.3 关键字更新（不是Agent）

关键字更新是 LearningRouter 的子功能，不需要专门的Agent：

```python
class LearningRouter:
    def handle_keywords(self, user_message: str, preference_store: UserPreferenceStore):
        """处理关键字更新（不是Agent，只是功能）"""
        # 1. LLM 解析关键字和操作
        # 2. 根据 action (add/delete/replace) 操作
        # 3. 存到长期记忆
        
        if action == "add":
            keywords = preference_store.get_keywords(user_id)
            keywords.extend(new_keywords)
            preference_store.save_keywords(user_id, keywords)
        elif action == "delete":
            keywords = preference_store.get_keywords(user_id)
            for kw in new_keywords:
                if kw in keywords:
                    keywords.remove(kw)
            preference_store.save_keywords(user_id, keywords)
        elif action == "replace":
            preference_store.save_keywords(user_id, new_keywords)
```

**示例**：

| 用户输入 | 意图 | 操作 | 结果 |
|----------|------|------|------|
| "改成搜索redis" | modify_keywords | replace | ["redis"] |
| "加上百度" | modify_keywords | add | ["redis", "百度"] |
| "删除redis" | modify_keywords | delete | ["百度"] |

只返回 JSON。
```

### 2.3 焦虑缓解Agent（AnxietyReliefAgent）

最简单的一个Agent，用于情感支持和闲聊。

**触发场景**：
- 用户表达消极情绪（焦虑、压力、迷茫）
- 用户想要闲聊（打招呼、随便聊聊）
- 用户说"累"、"烦"、"不想学习了"等

**System Prompt**：

```
你是一个温暖的面试陪伴者。
- 理解用户的焦虑和压力
- 提供情感支持和鼓励
- 不要说教或讲大道理
- 适度共情，适度鼓励
- 如果用户情绪过于消极，建议寻求专业帮助
- 如果用户只是闲聊，保持轻松友好的氛围
- 可以适度引导用户进入学习状态，但不要强制
```

### 2.4 卡片问答Agent（CardQuizAgent）

中等复杂度，负责问答式复习。

```python
class CardQuizAgent:
    def __init__(self, rag_manager, sqlite_client):
        self.rag = rag_manager
        self.sqlite = sqlite_client
    
    def start_quiz(self, topic: str = None):
        if topic:
            results = self.rag.search(topic, limit=1)
            return results[0].card
        else:
            card = self.sqlite.get_due_card()
            return card
    
    def check_answer(self, user_answer: str, card: Card):
        # 展示问题 → 用户回答 → 展示答案 → 评分
```

### 2.5 面试模拟Agent（InterviewSimAgent）

最复杂的一个Agent，模拟真实面试。

```python
class InterviewSimAgent:
    def __init__(self, llm_client, rag_manager):
        self.llm = llm_client
        self.rag = rag_manager
    
    def set_resume(self, resume_text: str):
        """设置用户简历"""
    
    def generate_question(self):
        """生成问题"""
    
    def generate_followup(self, user_answer: str):
        """生成追问"""
    
    def evaluate(self):
        """面试结束评估"""
```

### 2.6 前端交互

```
┌─────────────────────────────────────────────┐
│  💬 对话学习                                 │
├─────────────────────────────────────────────┤
│  [对话历史 - 自动识别模式]                   │
│                                             │
│  你: 最近好焦虑                               │
│  🤖: [焦虑缓解] 我理解你的感受...            │
│                                             │
│  你: 介绍一下快速排序                        │
│  🤖: [卡片问答] 快速排序是一种...            │
│                                             │
│  你: 想模拟面试                              │
│  🤖: [面试模拟] 请提供简历...                │
│                                             │
├─────────────────────────────────────────────┤
│  [输入框]  ────── [发送]                     │
└─────────────────────────────────────────────┘
```

### 2.7 数据存储

| 数据 | 存储 | 说明 |
|------|------|------|
| 对话历史 | ContextStore | 短期记忆，持久化 |
| 面试记录 | ContextStore | 面试结束后保存评估 |
| 简历信息 | UserPreferenceStore | 长期记忆，跨会话 |
| 爬虫关键字 | UserPreferenceStore | 从对话中获取 |

---

## 模块三：记忆管理

### 3.1 设计思路

```
┌─────────────────────────────────────────────────────────────┐
│                    记忆管理                                  │
├─────────────────────────────────────────────────────────────┤
│  短期记忆（会话级） - 对话历史 - ContextStore - session_id  │
│  长期记忆（持久级） - 爬虫关键字 - UserPreferenceStore - user_id │
└─────────────────────────────────────────────────────────────┘
```

**注意**：记忆管理与每日面经的卡片抽取是**独立的**：
- 每日面经需要的数据来自 SQLite（interval, ease_factor, correct_count 等）
- 长期记忆只存储爬虫关键字

### 3.2 数据来源对比

| 功能 | 需要的数据 | 数据来源 |
|------|------------|----------|
| 每日面经卡片选取 | interval, ease_factor, correct_count, total_reviews | SQLite `card_stats` 表 |
| 爬虫关键字存储 | keywords | 长期记忆（JSON文件） |

### 3.3 存储方式

#### 短期记忆：ContextStore（JSON 文件）

```
memory/
└── contexts/
    └── manifests/
        └── {session_id}.json
```

```json
{
  "session_id": "session_abc123",
  "versions": [{
    "chat_history": [
      {"role": "user", "content": "介绍一下快速排序"},
      {"role": "assistant", "content": "快速排序是..."}
    ],
    "created_at": "2026-04-03T10:00:00"
  }],
  "latest_version": 1
}
```

#### 长期记忆：UserPreferenceStore（JSON 文件）

```
memory/
└── preferences/
    └── {user_id}_keywords.json
```

```json
{
  "user_id": "user_default",
  "keywords": ["redis", "阿里", "字节跳动"],
  "updated_at": "2026-04-03T10:00:00"
}
```

### 3.4 触发机制

#### 短期记忆（对话历史）的触发

| 触发时机 | 触发动作 |
|----------|----------|
| 用户发送消息 | 将用户消息存入 ContextStore |
| Agent 回复后 | 将回复内容存入 ContextStore |
| 对话结束时 | 保存完整对话历史到 ContextStore |

```python
def handle_message(user_message: str):
    # 1. 加载历史
    history = context_store.load_latest_context(session_id)
    
    # 2. 添加新消息
    history["chat_history"].append({
        "role": "user", 
        "content": user_message
    })
    
    # 3. 调用 Agent
    response = agent.chat(user_message)
    
    # 4. 保存回复
    history["chat_history"].append({
        "role": "assistant",
        "content": response
    })
    
    # 5. 持久化
    context_store.save_context(session_id, history, version=+1)
```

#### 长期记忆（爬虫关键字）的触发

| 触发时机 | 触发动作 |
|----------|----------|
| 识别到 modify_keywords 意图 | 更新 UserPreferenceStore |
| 爬虫启动前 | 读取 UserPreferenceStore 加载关键字 |

```python
# 在 LearningRouter 中
def route(self, user_message: str):
    intent = self.llm_recognize(user_message)
    
    if intent["mode"] == "modify_keywords":
        # 触发长期记忆更新
        keywords = intent["keywords"]
        action = intent["action"]
        
        if action == "replace":
            preference_store.save_keywords(user_id, keywords)
        elif action == "add":
            for kw in keywords:
                preference_store.add_keyword(user_id, kw)
        elif action == "delete":
            for kw in keywords:
                preference_store.remove_keyword(user_id, kw)
        
        return "关键字已更新"
```

### 3.5 接口设计

```python
class UserPreferenceStore:
    def save_keywords(self, user_id: str, keywords: List[str]):
        file = self.storage_path / f"{user_id}_keywords.json"
        with open(file, 'w') as f:
            json.dump({
                "user_id": user_id,
                "keywords": keywords,
                "updated_at": datetime.now().isoformat()
            }, f)
    
    def get_keywords(self, user_id: str) -> List[str]:
        file = self.storage_path / f"{user_id}_keywords.json"
        if file.exists():
            return json.load(file).get("keywords", [])
        return []
    
    def add_keyword(self, user_id: str, keyword: str):
        keywords = self.get_keywords(user_id)
        if keyword not in keywords:
            keywords.append(keyword)
            self.save_keywords(user_id, keywords)
    
    def remove_keyword(self, user_id: str, keyword: str):
        keywords = self.get_keywords(user_id)
        if keyword in keywords:
            keywords.remove(keyword)
            self.save_keywords(user_id, keywords)

### 3.6 爬虫加载关键字

```python
class CollectorAgent:
    def __init__(
        self,
        keywords: Optional[List[str]] = None,
        preference_store: Optional[UserPreferenceStore] = None,
        user_id: str = "default",
        ...
    ):
        # 优先级：传入的 keywords > 记忆中的 > 默认值
        if keywords:
            self.keywords = keywords
        elif preference_store:
            self.keywords = preference_store.get_keywords(user_id)
        else:
            self.keywords = ["大模型 面经", "LLM 面经"]
```

---

## 模块四：上下文管理

### 4.1 Prompt 构建

```
1. System Prompt（固定）
2. User Profile（长期记忆）
3. Chat History（短期记忆）
4. User Message（当前消息）
```

### 4.2 会话过长处理

当对话超过上下文窗口时，采用**分层摘要**策略：

```python
class ContextManager:
    def get_context(self, session_id: str) -> str:
        history = self.context_store.load_latest_context(session_id)
        turns = history.get("chat_history", [])
        
        if len(turns) > 20:
            old_turns = turns[:-10]
            summary = self.llm.summarize(old_turns)
            return f"[摘要]\n{summary}\n\n[最近]\n{format_turns(turns[-10:])}"
        
        return format_turns(turns[-10:])
```

---

## 模块五：前端界面

### 5.1 页面结构

```
┌───────────────┬───────────────┬───────────────┐
│  每日面经     │  对话学习     │  控制中心     │
└───────────────┴───────────────┴───────────────┘
```

### 5.2 文件结构

```
pages/
├── todays_mission.py      # 每日面经
├── chat_learning.py       # 对话学习
└── control_center.py      # 控制中心
```

---

## 实现优先级

### 第一阶段

1. LLM 客户端封装
2. LearningRouter（意图识别）
3. 焦虑缓解Agent

### 第二阶段

4. 卡片问答Agent
5. 每日面经（基于记忆曲线）

### 第三阶段

6. 面试模拟Agent
7. 上下文管理
8. 前端界面

---

## 文件结构

```
src/
├── core/
│   ├── context_store.py      # 短期记忆
│   ├── preference_store.py    # 用户偏好（长期记忆）
│   ├── rag_manager.py         # 多路径检索
│   └── llm_client.py         # LLM 调用
│
├── agents/
│   ├── learning_router.py    # 入口路由
│   ├── anxiety_agent.py      # 焦虑缓解Agent
│   ├── card_quiz_agent.py    # 卡片问答Agent
│   └── interview_agent.py    # 面试模拟Agent
│
└── pages/
    ├── todays_mission.py     # 每日面经
    ├── chat_learning.py      # 对话学习
    └── control_center.py    # 控制中心
```