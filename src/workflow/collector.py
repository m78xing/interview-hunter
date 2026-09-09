"""
采集工作流 - 从牛客网、小红书等平台爬取面经
"""
import logging
import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class RawPost:
    """原始帖子"""
    title: str
    content: str
    url: str
    platform: str
    date: str
    author: str = ""
    is_mock: bool = False  


class CollectorWorkflow:
    """采集工作流 - 负责爬取面经"""
    
    def __init__(
        self,
        keywords: Optional[List[str]] = None,
        max_per_keyword: int = 5,
        days_range: int = 7,
        skills_dir: Optional[str] = None
    ):
        self.keywords = keywords or ["大模型 面经", "LLM 面经"]
        self.max_per_keyword = max_per_keyword
        self.days_range = days_range
        self.skills_dir = skills_dir
        
        self._nowcoder_crawler = None
        self._xhs_crawler = None
        
        self.last_collection_time: Optional[datetime] = None
        self.stats = {
            "total_collected": 0,
            "keywords_processed": 0,
            "errors": []
        }
        
        self.logger = logging.getLogger(__name__)
        self._init_crawlers()
    
    def _init_crawlers(self):
        """初始化爬虫"""
        skills_path = self.skills_dir
        if skills_path:
            skills_path = os.path.abspath(skills_path)
        else:
            skills_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "skills"))
        
        nowcoder_path = os.path.join(skills_path, "nowcoder-crawler")
        xhs_path = os.path.join(skills_path, "xhs-crawler")
        
        if os.path.exists(nowcoder_path) and nowcoder_path not in sys.path:
            sys.path.insert(0, nowcoder_path)
            try:
                from nowcoder_spider import nowcoderSpider  # type: ignore[reportMissingImports]
                self._nowcoder_crawler = nowcoderSpider()
                self.logger.info(f"牛客网爬虫初始化成功: {nowcoder_path}")
            except ImportError as e:
                self.logger.warning(f"牛客网爬虫导入失败: {e}")
            except Exception as e:
                self.logger.warning(f"牛客网爬虫初始化失败: {e}")
        
        if os.path.exists(xhs_path) and xhs_path not in sys.path:
            sys.path.insert(0, xhs_path)
            try:
                from xhs_spider import XHSSpider  # type: ignore[reportMissingImports]
                self._xhs_crawler = XHSSpider()
                self.logger.info(f"小红书爬虫初始化成功: {xhs_path}")
            except ImportError as e:
                self.logger.warning(f"小红书爬虫导入失败: {e}")
            except Exception as e:
                self.logger.warning(f"小红书爬虫初始化失败: {e}")
    
    async def collect(self) -> List[RawPost]:
        """执行采集"""
        self.logger.info(f"开始采集，关键字: {self.keywords}")
        
        all_posts = []
        
        for keyword in self.keywords:
            try:
                self.logger.info(f"采集关键字: {keyword}")
                
                posts = await self._collect_keyword(keyword)
                
                all_posts.extend(posts)
                
                self.stats["keywords_processed"] += 1
                self.stats["total_collected"] += len(posts)
                
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"采集 {keyword} 失败: {e}")
                self.stats["errors"].append({
                    "keyword": keyword,
                    "error": str(e),
                    "time": datetime.now().isoformat()
                })
        
        self.last_collection_time = datetime.now()
        
        self.logger.info(f"采集完成，共 {len(all_posts)} 篇")
        
        return all_posts
    
    async def _collect_keyword(self, keyword: str) -> List[RawPost]:
        """采集单个关键字"""
        posts = []
        
        posts.extend(await self._collect_nowcoder(keyword))
        posts.extend(await self._collect_xiaohongshu(keyword))
        
        if not posts:
            self.logger.warning(f"真实爬虫未返回数据，使用模拟数据: {keyword}")
            posts = await self._collect_mock(keyword)
        
        return posts
    
    def _title_matches_keyword(self, title: str, keyword: str) -> bool:
        """检查标题是否匹配关键词"""
        title_lower = title.lower()
        keyword_lower = keyword.lower()
        parts = keyword_lower.replace(' 面经', '').replace('面经', '').split()
        return any(p in title_lower for p in parts)
    
    async def _collect_nowcoder(self, keyword: str) -> List[RawPost]:
        """采集牛客网"""
        if not self._nowcoder_crawler:
            self.logger.warning("牛客网爬虫未初始化")
            return []
        
        try:
            raw_interviews = await asyncio.to_thread(
                self._nowcoder_crawler.fetch_interviews,
                [keyword],
                self.max_per_keyword,
                self.days_range
            )
            
            posts = []
            for raw in raw_interviews:
                if not self._title_matches_keyword(raw.title, keyword):
                    self.logger.debug(f"跳过不相关结果: {raw.title}")
                    continue
                    
                post = RawPost(
                    title=raw.title,
                    content=raw.content or raw.title,
                    url=raw.url,
                    platform="牛客网",
                    date=raw.date or datetime.now().strftime("%Y-%m-%d"),
                    author=getattr(raw, 'author', '') or ''
                )
                posts.append(post)
            
            self.logger.info(f"牛客网采集到 {len(posts)} 篇")
            return posts
        except Exception as e:
            self.logger.error(f"牛客网采集失败: {e}")
            return []
    
    async def _collect_xiaohongshu(self, keyword: str) -> List[RawPost]:
        """采集小红书"""
        if not self._xhs_crawler:
            self.logger.warning("小红书爬虫未初始化")
            return []
        
        try:
            raw_interviews = await asyncio.to_thread(
                self._xhs_crawler.fetch_interviews,
                [keyword],
                self.max_per_keyword,
                self.days_range
            )
            
            posts = []
            for raw in raw_interviews:
                post = RawPost(
                    title=raw.title,
                    content=raw.content or raw.title,
                    url=raw.url,
                    platform="小红书",
                    date=raw.date or datetime.now().strftime("%Y-%m-%d"),
                    author=getattr(raw, 'author', '') or ''
                )
                posts.append(post)
            
            self.logger.info(f"小红书采集到 {len(posts)} 篇")
            return posts
        except Exception as e:
            self.logger.error(f"小红书采集失败: {e}")
            return []
    
    async def _collect_mock(self, keyword: str) -> List[RawPost]:
        """采集单个关键字（模拟实现，备用）"""
        posts = []
        
        platforms = ["牛客网", "小红书"]
        
        for i in range(min(2, self.max_per_keyword)):
            post = RawPost(
                title=f"{keyword.replace(' 面经', '')} 面试经验 {i+1}",
                content=f"""
面试题目：
1. 请介绍一下 {keyword.split()[0]} 的原理？
2. 它有什么优缺点？
3. 如何进行优化？
4. 与其他技术相比有什么不同？

面试反馈：
- 需要深入理解底层原理
- 优化方法是考察重点
- 实战经验很重要
                """.strip(),
                url=f"https://example.com/interview/{keyword}/{i}",
                platform=platforms[i % len(platforms)],
                date=datetime.now().strftime("%Y-%m-%d"),
                author=f"用户{i+1}",
                is_mock=True
            )
            posts.append(post)
        
        return posts
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "last_collection_time": self.last_collection_time.isoformat() if self.last_collection_time else None
        }
    
    def update_keywords(self, keywords: List[str]):
        """更新关键字"""
        self.keywords = keywords
        self.logger.info(f"关键字已更新: {keywords}")
    
    def add_keyword(self, keyword: str):
        """添加关键字"""
        if keyword not in self.keywords:
            self.keywords.append(keyword)
            self.logger.info(f"添加关键字: {keyword}")
    
    def remove_keyword(self, keyword: str):
        """移除关键字"""
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            self.logger.info(f"移除关键字: {keyword}")
