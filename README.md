# Interview Hunter - 面经猎手

猎取面经，智能学习。

## 技术栈

- 多 Agent 架构 (自实现)
- Chroma (向量数据库)
- SQLite (关系数据)
- Streamlit (前端)
- deepseek-chat (LLM)

## 项目结构

```
interview-hunter/
├── src/
│   ├── agents/         # Agent 实现
│   ├── storage/       # 存储层
│   ├── core/          # 核心算法
│   └── config/        # 配置
├── pages/             # Streamlit 页面
├── memory/            # 用户数据
└── skills/           # 爬虫 Skill
```

## 快速开始

```bash
# 设置环境变量（可选）
export DEEPSEEK_API_KEY="your-api-key-here"

# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run app.py
```

## 核心功能

1. **智能采集**: 自动爬取牛客网、小红书面经
2. **卡片生成**: LLM 提取 Q&A 卡片
3. **遗忘曲线**: SM-2 算法调度复习
4. **多因子推荐**: 遗忘曲线 + 薄弱点 + 岗位热度 + 知识依赖
5. **LLM 审计**: 自适应调整学习策略
6. **对话学习**: 基于向量搜索的智能问答学习界面
