---
name: xhs-crawler
description: |
  小红书面经爬虫。爬取小红书上的面试经验分享笔记。
  当用户要求"爬取小红书面经"、"获取小红书面试经验"时触发。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - playwright
    emoji: "📕"
---

# xhs-crawler - 小红书面经爬虫

爬取小红书（xiaohongshu.com）上的面试经验分享笔记。

## 文件结构

```
xhs-crawler/
├── xhs_spider.py        # 小红书爬虫核心（包含登录验证）
├── collect.py           # 采集入口
├── local_processor.py  # 本地处理（摘要、标签等）
└── storage.py          # 存储管理
```

## 使用流程

### 步骤 1：验证登录状态

| 命令 | 功能 |
|------|------|
| `python xhs_spider.py --status` | 验证是否登录 |

### 步骤 2：扫码登录（如未登录）

首次使用需要扫码登录：

| 命令 | 功能 |
|------|------|
| `python collect.py --login` | 打开浏览器界面登录小红书本，需要用户主动扫码登录 |

登录状态会保存到 `xhs_user_data/` 目录，后续自动复用。

### 步骤 3：运行爬取

使用 `collect.py` 采集面经：

```bash
python collect.py --keywords "大模型面经" --max_per_keyword 5 --days_range 7
```
参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--keywords` | 搜索关键字（每个关键字用双引号括起来，多个用空格分隔） | "agent 面经" "LLM面经" |
| `--max_per_keyword` | 每个关键字最多爬取数量 | 1 |
| `--days_range` | 爬取最近多少天内的面经 | 7 |

## 示例

```bash
# 采集大模型相关面经，最近7天的，每个关键词最多5篇
python collect.py --keywords "大模型 面经" "LLM面经" "Agent 面经" --max_per_keyword 1 --days_range 7

# 采集字节跳动面试经验
python collect.py --keywords "字节跳动面试" --max_per_keyword 10 --days_range 30

# 采集算法工程师面经
python collect.py --keywords "算法工程师面经" --max_per_keyword 20
```

## 输出结果

采集的面经保存到主目录下的 `crawl_data` 目录下：

- `raw/YYYY-MM-DD` - 当天采集的面经
- `INDEX.json` - 索引文件
- `by_company` - 按公司分类的面经目录

## 依赖

```bash
pip install playwright requests beautifulsoup4
playwright install chromium
```

## 注意事项

- **首次使用必须先登录**
- 登录状态保存在 `xhs_user_data/`
- 爬取频率不宜过高，避免被封禁
- 建议先验证登录状态再批量采集
