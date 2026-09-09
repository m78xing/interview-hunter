# 后台功能改进计划

## 1. 定时调度改进

### 当前问题
- `HeartbeatDriver` 使用 `asyncio.sleep(60)` 轮询
- Streamlit 是同步框架，asyncio 任务在后台可能不稳定
- 每次重启 Streamlit 需要重新初始化调度

### 替代方案

| 方案 | 优点 | 缺点 | 适用性 |
|------|------|------|--------|
| **APScheduler** | 成熟稳定，支持多种触发器 | 增加依赖 | ✅ 推荐 |
| **schedule** | 轻量简单 | 功能单一 | ⚠️ 可用 |
| **系统 cron** | 不依赖应用 | 需要服务器权限 | ❌ 不适合 |
| **保持 asyncio** | 无额外依赖 | Streamlit 兼容性差 | ❌ 不推荐 |

### 推荐方案：APScheduler

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    run_collection,
    'cron',
    hour=8,
    minute=0,
    id='daily_crawl',
    replace_existing=True
)
scheduler.start()
```

**优势**：
- 后台线程运行，不影响 Streamlit 主进程
- 支持 cron 表达式，灵活配置时间
- 支持任务持久化（可选）
- 成熟的错误处理和重试机制

---

## 2. 爬取关键字从长期记忆获取

### 当前流程
```
config.yaml → Supervisor → CollectorAgent
```

### 改进后流程
```
UserPreferenceStore (长期记忆) → Supervisor → CollectorAgent
                                    ↓ (如果记忆为空)
                              config.yaml (默认值)
```

### 修改点

| 文件 | 修改内容 |
|------|----------|
| `src/agents/supervisor.py` | `run_collection()` 从 `UserPreferenceStore` 获取关键字 |
| `src/agents/collector.py` | 支持动态传入关键字列表 |
| `app.py` | 初始化时传入 `UserPreferenceStore` 给 Supervisor |

### 代码变更

```python
# supervisor.py
async def run_collection(self):
    # 优先从长期记忆获取关键字
    keywords = self.preference_store.get_keywords("default")
    if not keywords:
        keywords = self.default_keywords  # 回退到默认值
    
    self.collector.keywords = keywords
    raw_posts = await self.collector.collect()
    ...
```

---

## 3. 数据库内容查看界面

### 页面设计

```
┌─────────────────────────────────────────────────────────────┐
│  📊 数据库管理                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┬───────────────┬───────────────┐         │
│  │ 卡片总数      │ 公司数        │ 岗位数        │         │
│  │ 1,234         │ 15            │ 8             │         │
│  └───────────────┴───────────────┴───────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 🔍 搜索: [________] 公司: [全部▼] 难度: [全部▼]    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 问题                          │ 公司   │ 难度 │ 标签 │  │
│  ├───────────────────────────────┼────────┼──────┼──────┤  │
│  │ 快速排序的时间复杂度？        │ 字节   │ 中   │ 算法 │  │
│  │ Redis 缓存穿透如何解决？      │ 阿里   │ 高   │ 系统 │  │
│  │ ...                           │ ...    │ ...  │ ...  │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  第 1-10 条，共 1,234 条     [< 上一页] [1] [2] [3] [下一页 >] │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 功能列表

| 功能 | 说明 |
|------|------|
| 统计卡片 | 卡片总数、公司数、岗位数 |
| 搜索过滤 | 按关键词、公司、难度过滤 |
| 分页显示 | 每页 10/20/50 条 |
| 卡片详情 | 点击展开查看完整 Q&A |
| 删除卡片 | 支持单条删除（可选） |

### 文件结构

```
pages/
└── database_viewer.py  # 新增：数据库内容查看页面
```

---

## 4. 爬取完成后邮件通知

### 需求
每次爬取面经完成后，自动发送邮件通知用户，包含：
- 新增面经数量
- 按公司分类统计
- 最近面经列表

### 复用 miniClaw 的 email-notifier Skill

已在 `../miniClaw/skills/email-notifier` 中实现完整功能：

| 文件 | 说明 |
|------|------|
| `send.py` | CLI 入口，支持 `--dry-run`、`--to` 等参数 |
| `SKILL.md` | 技能说明文档 |

### 集成方式

**方案 A：直接调用 CLI（推荐）**
```python
# supervisor.py 中爬取完成后
import subprocess
subprocess.run([
    "python", "../miniClaw/skills/email-notifier/send.py",
    "--interviews", "workspace/interview"
])
```

**方案 B：复制 notifier 模块到本项目**
```
src/core/
└── email_notifier.py  # 从 miniClaw 复制并适配
```

### 修改点

| 文件 | 修改内容 |
|------|----------|
| `src/agents/supervisor.py` | 爬取完成后调用邮件通知 |
| `src/config/settings.py` | 添加邮件配置项 |
| `config.yaml` | 添加 email 配置 |

### 配置要求

```yaml
email:
  enabled: true
  smtp_host: smtp.qq.com
  smtp_port: 587
  smtp_user: your_email@qq.com
  smtp_password: your_auth_code
  from_name: InterviewHunter面经助手
  to: your_email@qq.com
```

### 注意事项
- 需要用户配置 SMTP 授权码
- 首次使用建议 `--dry-run` 测试
- 邮件发送失败不应阻塞主流程

---

## 5. 每日面经熟悉程度按钮

### 需求
在每日面经列表中，为每个面经卡片添加熟悉程度选择按钮。

### 设计

```
┌─────────────────────────────────────────────────────────────┐
│ 1. [字节] Redis 缓存穿透如何解决？  [遗忘: 高]              │
│                                                             │
│ 公司: 字节 | 岗位: 后端开发 | 难度: 高                      │
│ 答案内容...                                                 │
│                                                             │
│ 熟悉程度: [😕 陌生] [🤔 模糊] [😐 一般] [😊 熟悉] [🎯 掌握]  │
└─────────────────────────────────────────────────────────────┘
```

### 熟悉程度等级

| 等级 | 值 | 含义 | 对 SM-2 的影响 |
|------|-----|------|---------------|
| 陌生 | 0 | 完全不会 | 重置 interval，缩短复习间隔 |
| 模糊 | 1 | 有点印象 | 小幅增加 interval |
| 一般 | 2 | 大致了解 | 正常 SM-2 调度 |
| 熟悉 | 3 | 比较熟练 | 延长复习间隔 |
| 掌握 | 4 | 完全掌握 | 大幅延长复习间隔 |

### 修改点

| 文件 | 修改内容 |
|------|----------|
| `pages/todays_mission.py` | 在每个 expander 内添加 5 个按钮 |
| `src/core/daily_mission.py` | 添加 `record_familiarity(card_id, level)` 方法 |
| `src/storage/sqlite_client.py` | 更新卡片 stats（interval, ease_factor） |

### SM-2 算法映射

```python
# 熟悉程度 → SM-2 quality 映射
FAMILIARITY_TO_QUALITY = {
    0: 0,  # 陌生 → 完全错误
    1: 1,  # 模糊 → 勉强回忆
    2: 3,  # 一般 → 正确回忆但有困难
    3: 4,  # 熟悉 → 正确回答
    4: 5,  # 掌握 → 完美回答
}
```

### 交互流程
1. 用户点击展开面经卡片
2. 查看问题和答案
3. 选择熟悉程度按钮
4. 系统更新 SM-2 调度参数
5. 按钮高亮显示当前选择

---

## 6. 卡片问答召回来源标注

### 需求
卡片问答模块回答后，列出本次召回的面经卡片来源，让用户知道回答是基于哪些面经生成的。

### 当前问题
- `CardQuizAgent.chat()` 和 `chat_stream()` 内部执行了 RAG 搜索
- 搜索结果传入了 system prompt 给 LLM
- 用户无法看到召回了哪些卡片，无法判断回答来源

### 改进方案

**修改 Agent 返回值**：
```python
# 当前：只返回 response 文本
return response

# 改进后：返回 (response, sources)
return {
    "response": response,
    "sources": [
        {"card_id": "xxx", "question": "...", "company": "...", "similarity": 0.85},
        ...
    ]
}
```

### 修改点

| 文件 | 修改内容 |
|------|----------|
| `src/agents/card_quiz_agent.py` | `chat()` 和 `chat_stream()` 返回包含 sources 的结构 |
| `pages/chat_learning.py` | 渲染回答后显示召回的卡片列表 |

### 前端显示效果

```
┌─────────────────────────────────────────────────────────────┐
│ [模型回答内容...]                                            │
│                                                             │
│ ─── 召回来源 ───                                            │
│ 📄 1. Redis 缓存穿透如何解决？ (字节 - 后端)  相似度: 0.92  │
│ 📄 2. Redis 缓存雪崩和击穿的区别？ (阿里 - 后端)  相似度: 0.78│
│ 📄 3. 如何设计一个高可用的缓存系统？ (腾讯 - 架构)  相似度: 0.65│
└─────────────────────────────────────────────────────────────┘
```

### 无召回来源时
如果 RAG 搜索无结果，显示：
```
💡 未找到相关面经，以下回答基于模型自身知识
```

---

## 7. 历史会话列表

### 需求
在对话学习界面右侧添加历史会话列表，点击可切换会话。

### 当前状态
- `ContextStore` 已有 `list_sessions()` 方法列出所有会话
- `ContextStore` 已有 `get_context_history()` 方法获取会话历史
- `ContextManager` 已有 `get_context()` 方法加载会话上下文
- 数据已持久化到 `memory/contexts/manifests/` 目录

### 布局设计

```
┌──────────────────────────────────┬──────────────────┐
│                                  │  📋 历史会话      │
│                                  │                  │
│  💬 对话学习主区域                │  ┌────────────┐  │
│                                  │  │ 2024-04-03  │  │
│  [用户消息]                       │  │ 焦虑缓解    │  │
│  [AI 回复]                        │  │ 12 条消息   │  │
│  [用户消息]                       │  └────────────┘  │
│  [AI 回复]                        │  ┌────────────┐  │
│                                  │  │ 2024-04-02  │  │
│                                  │  │ 卡片问答    │  │
│  [输入框]                         │  │ 8 条消息    │  │
│                                  │  └────────────┘  │
│                                  │  ┌────────────┐  │
│                                  │  │ 2024-04-01  │  │
│                                  │  │ 面试模拟    │  │
│                                  │  │ 25 条消息   │  │
│                                  │  └────────────┘  │
│                                  │                  │
│                                  │  [+ 新建会话]    │
└──────────────────────────────────┴──────────────────┘
```

### 功能列表

| 功能 | 说明 |
|------|------|
| 会话列表 | 显示所有历史会话，按时间倒序 |
| 会话摘要 | 显示日期、模式、消息数量 |
| 切换会话 | 点击加载该会话的历史消息 |
| 新建会话 | 清空当前对话，创建新 session |
| 删除会话 | 可选：删除不需要的会话 |

### 修改点

| 文件 | 修改内容 |
|------|----------|
| `pages/chat_learning.py` | 右侧添加会话列表 sidebar，支持切换 |
| `src/core/context_store.py` | 添加 `get_session_summary(session_id)` 方法 |
| `src/core/context_manager.py` | 添加 `list_all_sessions()` 方法 |

### 会话摘要生成
从 `ContextSnapshot` 中提取：
- `created_at` → 显示日期
- `summary` → 显示会话主题
- `chat_history` 长度 → 显示消息数量
- 最后一条消息的模式 → 显示标签（焦虑缓解/卡片问答/面试模拟）

---

## 实现优先级

### 第一阶段：定时调度改进
1. 安装 APScheduler
2. 替换 HeartbeatDriver
3. 集成到 app.py

### 第二阶段：关键字从长期记忆获取
4. 修改 Supervisor 初始化
5. 修改 CollectorAgent 支持动态关键字
6. 测试爬取流程

### 第三阶段：数据库查看界面
7. 创建 `database_viewer.py`
8. 实现搜索、过滤、分页
9. 集成到导航

### 第四阶段：邮件通知
10. 集成 miniClaw 的 email-notifier
11. 修改 Supervisor 爬取完成后调用
12. 添加邮件配置项

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/core/heartbeat.py` | 替换为 APScheduler | 或使用新文件 `src/core/scheduler.py` |
| `src/agents/supervisor.py` | 修改 | 从 UserPreferenceStore 获取关键字 + 邮件通知 |
| `src/agents/collector.py` | 修改 | 支持动态关键字 |
| `app.py` | 修改 | 集成新调度器 + 传入 PreferenceStore |
| `pages/database_viewer.py` | 新增 | 数据库查看页面 |
| `src/config/settings.py` | 修改 | 添加邮件配置 |
| `config.yaml` | 修改 | 添加 email 配置 |
| `requirements.txt` | 修改 | 添加 apscheduler |
