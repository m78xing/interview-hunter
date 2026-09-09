"""
Storage Module - 面经存储管理

负责：
1. 管理面经的存储结构
2. 维护索引文件（INDEX.json）
3. 去重检查
4. 按公司/标签分类存储
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class InterviewItem:
    """单篇面经"""
    id: str
    title: str
    company: str
    position: str
    date: str
    tags: list
    summary: str
    full_content: str
    source_url: str
    source_platform: str
    created_at: str
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class Storage:
    """面经存储管理器"""
    
    def __init__(self, workspace: Optional[str] = None):
        if workspace is None:
            workspace = Path(__file__).parent.parent.parent / "crawl_data"
        self.workspace = Path(workspace)
        self.index_file = self.workspace / "INDEX.json"
        self.index_md_file = self.workspace / "index.md"
        self.by_company_dir = self.workspace / "by_company"
        self.by_keyword_dir = self.workspace / "by_keyword"
        self.raw_dir = self.workspace / "raw"
        
        self._ensure_dirs()
        
        self._index: dict = self._load_index()
    
    def _ensure_dirs(self):
        """确保目录结构存在"""
        dirs = [
            self.workspace,
            self.by_company_dir,
            self.by_keyword_dir,
            self.raw_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> dict:
        """加载索引文件"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"interviews": [], "companies": {}, "keywords": {}}
    
    def _save_index(self):
        """保存索引文件"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, title: str, source_url: str) -> str:
        """生成唯一ID"""
        import hashlib
        key = f"{title}{source_url}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def _extract_company(self, title: str) -> str:
        """从标题提取公司名"""
        companies = [
            "字节跳动", "字节", "腾讯", "阿里巴巴", "阿里", "百度", 
            "小米", "美团", "京东", "拼多多", "快手", "网易",
            "蚂蚁", "蚂蚁金服", "阿里云", "商汤", "旷视",
            "华为", "字节", "小红书", "bilibili", "B站"
        ]
        for c in companies:
            if c in title:
                return c
        return "其他"
    
    def _sanitize_filename(self, name: str) -> str:
        """文件名安全化"""
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name[:50]
        return name
    
    def is_duplicate(self, source_url: str) -> bool:
        """检查是否重复"""
        for item in self._index.get("interviews", []):
            if item.get("source_url") == source_url:
                return True
        return False
    
    def save(self, item: InterviewItem) -> bool:
        """
        保存面经
        
        Returns:
            True if saved, False if duplicate
        """
        if self.is_duplicate(item.source_url):
            return False
        
        item.id = self._generate_id(item.title, item.source_url)
        item.company = self._extract_company(item.title)
        item.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        raw_dir = self.raw_dir / date_str
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = self._sanitize_filename(f"{item.company}-{item.position}-{item.id}.md")
        file_path = raw_dir / f"{file_name}.md"
        
        content = self._build_markdown(item)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        item_dict = item.to_dict()
        item_dict["file_path"] = str(file_path)
        
        self._index["interviews"].append(item_dict)
        
        company = item.company
        if company not in self._index["companies"]:
            self._index["companies"][company] = []
        self._index["companies"][company].append(item.id)
        
        for tag in item.tags:
            if tag not in self._index["keywords"]:
                self._index["keywords"][tag] = []
            self._index["keywords"][tag].append(item.id)
        
        self._save_index()
        self._update_index_md()
        self._append_to_company_file(item, file_path)
        
        return True
    
    def _build_markdown(self, item: InterviewItem) -> str:
        """构建Markdown格式"""
        tags_str = ", ".join([f"#{t}" for t in item.tags])
        
        md = f"""---
title: {item.title}
company: {item.company}
position: {item.position}
date: {item.date}
tags: [{tags_str}]
source: {item.source_url}
platform: {item.source_platform}
created_at: {item.created_at}
---

## 摘要

{item.summary}

## 核心技术问题

{self._extract_questions(item.full_content)}

---

## 完整面经内容

{item.full_content}

---

**原文链接**: [{item.source_url}]({item.source_url})

*本面经由 miniClaw 自动采集于 {item.source_platform}，采集时间: {item.created_at}*
"""
        return md
    
    def _extract_questions(self, content: str) -> str:
        """提取面试问题"""
        lines = content.split('\n')
        questions = []
        for line in lines:
            line = line.strip()
            if line and ('？' in line or '?' in line) and len(line) < 200:
                if any(kw in line for kw in ['原理', '机制', '流程', '区别', '实现', '优化', '架构', '方法', '什么', '如何', '为什么']):
                    questions.append(f"- {line}")
        
        if questions:
            return '\n'.join(questions[:15])
        return "- （请查看完整内容）"
    
    def _update_index_md(self):
        """更新总索引Markdown"""
        interviews = self._index.get("interviews", [])
        interviews.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        lines = ["# 面经索引\n"]
        lines.append(f"\n总计: {len(interviews)} 篇\n")
        
        lines.append("\n## 按公司\n")
        for company, ids in sorted(self._index.get("companies", {}).items()):
            lines.append(f"- **{company}**: {len(ids)} 篇")
        
        lines.append("\n## 按关键词\n")
        popular_tags = sorted(self._index.get("keywords", {}).items(), key=lambda x: len(x[1]), reverse=True)
        for tag, ids in popular_tags[:20]:
            lines.append(f"- **{tag}**: {len(ids)} 篇")
        
        lines.append("\n## 最新面经\n")
        for item in interviews[:20]:
            tags_str = " ".join([f"`{t}`" for t in item.get("tags", [])[:5]])
            lines.append(f"- [{item['title']}]({item.get('file_path', '')}) {tags_str}")
        
        with open(self.index_md_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _append_to_company_file(self, item: InterviewItem, file_path: Path):
        """追加到公司分类文件"""
        company_file = self.by_company_dir / f"{self._sanitize_filename(item.company)}.md"
        
        tags_str = ", ".join([f"#{t}" for t in item.tags])
        
        entry = f"""

### {item.title}

**岗位**: {item.position}  
**时间**: {item.date}  
**标签**: {tags_str}

**摘要**: {item.summary[:200]}...

**查看全文**: [{file_path.name}]({file_path.absolute()}) | [原文链接]({item.source_url})

---
"""
        
        if company_file.exists():
            with open(company_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if item.id not in content:
                content += entry
        else:
            content = f"""# {item.company} 面经

## 统计
共收录 {len(self._index.get('companies', {}).get(item.company, []))} 篇

---
""" + entry
        
        with open(company_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def get_recent(self, limit: int = 10) -> list:
        """获取最近的面经"""
        interviews = self._index.get("interviews", [])
        interviews.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return interviews[:limit]
    
    def search(self, keyword: str) -> list:
        """搜索面经"""
        results = []
        keyword_lower = keyword.lower()
        
        for item in self._index.get("interviews", []):
            text = f"{item.get('title', '')} {item.get('summary', '')} {item.get('tags', [])}".lower()
            if keyword_lower in text:
                results.append(item)
        
        return results
    
    def get_by_company(self, company: str) -> list:
        """按公司获取"""
        ids = self._index.get("companies", {}).get(company, [])
        interviews = {i["id"]: i for i in self._index.get("interviews", [])}
        return [interviews.get(id) for id in ids if id in interviews]
    
    def get_by_keyword(self, keyword: str) -> list:
        """按关键词获取"""
        ids = self._index.get("keywords", {}).get(keyword, [])
        interviews = {i["id"]: i for i in self._index.get("interviews", [])}
        return [interviews.get(id) for id in ids if id in interviews]
    
    def get_full_content(self, item_id: str) -> Optional[str]:
        """获取完整内容"""
        interviews = {i["id"]: i for i in self._index.get("interviews", [])}
        item = interviews.get(item_id)
        
        if item and "file_path" in item:
            file_path = Path(item["file_path"])
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                parts = content.split("---")
                if len(parts) > 3:
                    return parts[-2].strip()
        
        return None
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total": len(self._index.get("interviews", [])),
            "companies": len(self._index.get("companies", {})),
            "keywords": len(self._index.get("keywords", {})),
            "today": len([i for i in self._index.get("interviews", []) 
                         if i.get("created_at", "").startswith(datetime.now().strftime("%Y-%m-%d"))])
        }
