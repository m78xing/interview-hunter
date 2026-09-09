---
name: nowcoder-crawler
description: |
  牛客网面经爬虫。爬取牛客网上的面试经验分享文章。
  当用户要求"爬取牛客网面经"、"获取牛客面试经验"时触发。
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
    emoji: "📝"
---

# nowcoder-crawler - 牛客网面经爬虫

爬取牛客网（nowcoder.com）上的面试经验分享。

## 功能

- 按关键词搜索面经
- 爬取面经详情（公司、岗位、面试题、经验分享）
- 支持日期范围过滤
- 自动保存到本地

## 命令

| 命令 | 功能 |
|------|------|
| `python collect.py --keyword "关键词"` | 按关键词爬取面经 |
| `python collect.py --keyword "LLM" --days 7` | 爬取最近7天的面经 |
| `python collect.py --keyword "大模型" --max 20` | 最多爬取20篇 |
| `python collect.py --help` | 查看完整帮助 |

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--keyword` | 搜索关键词（必填） | - |
| `--days` | 爬取最近N天的面经 | 7 |
| `--max` | 最大爬取数量 | 10 |
| `--output` | 输出目录 | workspace/interview |

## 示例

```bash
# 爬取大模型相关面经
python collect.py --keyword "大模型" --days 7

# 爬取字节跳动面经
python collect.py --keyword "字节跳动" --max 20

# 爬取算法工程师面经
python collect.py --keyword "算法工程师"
```

## 输出

采集的面经保存到主目录下的 `crawl_data` 目录下：

- `raw/YYYY-MM-DD` - 当天采集的面经
- `INDEX.json` - 索引文件
- `by_company` - 按公司分类的面经目录

## 注意事项

- 牛客网可能有反爬机制，爬取间隔不宜过短
- 建议配合 email-notifier 使用，采集完成后发送邮件通知
