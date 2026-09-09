from xhs_spider import XHSSpider
from local_processor import LocalProcessor
from storage import Storage, InterviewItem
from typing import List
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class XHSCrawler:
    def __init__(self):
        self.spider = XHSSpider()
        self.processor = LocalProcessor()
        self.storage = Storage()

    def fetch_interviews(self, keywords, max_per_keyword, days_range):
        return self.spider.fetch_interviews(keywords, max_per_keyword, days_range)

    def get_detail(self, url):
        return self.spider.get_detail(url)

    def process(self, title, content, url, platform, date):
        return self.processor.process(title, content, url, platform, date)

    def save(self, item):
        return self.storage.save(item)
    
    def run(self, keywords, max_per_keyword, days_range):
        new_interviews = []
        try:
            raw_interviews = self.fetch_interviews(keywords, max_per_keyword, days_range)
            for raw in raw_interviews:
                processed = self.process(raw.title, raw.content, raw.url, "小红书", raw.date)
                item = InterviewItem(
                    id="",
                    title=processed.title,
                    company=processed.company,
                    position=processed.position,
                    date=processed.date,
                    tags=processed.tags,
                    summary=processed.summary,
                    full_content=processed.full_content,
                    source_url=processed.source_url,
                    source_platform=processed.source_platform,
                    created_at=""
                )
                if self.storage.save(item):
                    new_interviews.append(item.to_dict())
                    print(f"✓ 保存: {processed.title[:40]}...")
                else:
                    print(f"- 重复: {processed.title[:40]}...")
        except Exception as e:
            print(f"⚠ 小红书采集出错: {e}")
        
        print(f"采集完成！新增 {len(new_interviews)} 篇面经")
        stats = self.storage.get_stats()
        print(f"总面经数: {stats.get('total', 0)}")
        return stats
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="小红书爬虫工具")
    parser.add_argument("--keywords", type=str, nargs='+', default=["agent 面经"], help="搜索关键字")
    parser.add_argument("--max_per_keyword", type=int, default=1, help="每个关键字最多爬取数量")
    parser.add_argument("--days_range", type=int, default=7, help="爬取最近多少天内的面经")
    
    args = parser.parse_args()
    
    crawler = XHSCrawler()
    crawler.run(args.keywords, args.max_per_keyword, args.days_range)