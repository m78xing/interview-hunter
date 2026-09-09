"""
NaukangSpider - 牛客网面经爬虫（增强版）

爬取牛客网面经板块的面经内容
使用标签页URL获取数据
支持 AJAX API 方式和 DOM 解析方式
"""

import re
import time
import json
import random
import requests
from datetime import datetime, timedelta
from typing import Optional, Set, List, Tuple
from bs4 import BeautifulSoup
from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass
class Interview:
    """面经数据结构"""
    title: str
    content: str
    url: str
    company: str = ""
    position: str = ""
    date: str = ""
    author: str = ""


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

RULES = {
    "company": {
        "字节": "字节跳动", "bytedance": "字节跳动", "抖音": "字节跳动",
        "阿里": "阿里巴巴", "淘天": "阿里巴巴", "蚂蚁": "蚂蚁集团",
        "腾讯": "腾讯", "美团": "美团", "百度": "百度", "快手": "快手",
        "拼多多": "拼多多", "京东": "京东", "网易": "网易", "小红书": "小红书",
        "华为": "华为", "米哈游": "米哈游", "滴滴": "滴滴", "蔚来": "蔚来",
        "理想": "理想", "小鹏": "小鹏", "b站": "Bilibili", "哔哩哔哩": "Bilibili",
    },
    "role": [
        "后端", "前端", "算法", "测试", "测开", "客户端", "安卓", "大数据", "产品", "运营",
        "Java", "C++", "Python", "Go", "嵌入式",
    ],
}


class nowcoderSpider:
    """牛客网面经爬虫（增强版）"""
    
    BASE_URL = "https://www.nowcoder.com"
    SEARCH_URL = "https://www.nowcoder.com/discuss/experience"
    
    HEADERS = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": BASE_URL,
    }
    
    def __init__(self, timeout: int = 30, cookie: str = ""):
        self.timeout = timeout
        self.cookie = cookie
        self.session = requests.Session()
        self._update_headers()
        self._visited_urls: Set[str] = set()
    
    def _update_headers(self):
        """更新请求头"""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": self.BASE_URL,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": self.cookie,
        })
    
    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """随机延迟"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def _clean_text(self, text: str) -> str:
        """清理文本，保留换行符"""
        if not text:
            return ""
        # 保留换行符，只压缩同一行内的空白字符
        lines = []
        for line in text.split('\n'):
            line = re.sub(r'[ \t]+', ' ', line)  # 只压缩空格和tab
            line = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', line)
            lines.append(line.strip())
        # 移除连续的空行
        result = []
        prev_empty = False
        for line in lines:
            is_empty = not line.strip()
            if is_empty:
                if not prev_empty:
                    result.append('')
                prev_empty = True
            else:
                result.append(line)
                prev_empty = False
        return '\n'.join(result).strip()
    
    def _timestamp_to_date(self, timestamp_ms: int) -> str:
        """毫秒时间戳转日期字符串"""
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """从文本提取日期"""
        if not text:
            return None
        
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',
            r'(\d{2})-(\d{2})',
        ]
        
        now = datetime.now()
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups[0]) == 4:
                    return f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                else:
                    return f"{now.year}-{int(groups[0]):02d}-{int(groups[1]):02d}"
        
        return None
    
    def _extract_company_position(self, title: str, text: str = "") -> tuple:
        """从标题和内容提取公司和岗位"""
        combined = title + " " + (text or "")
        
        company = "其他"
        for key, name in RULES["company"].items():
            if key.lower() in combined.lower():
                company = name
                break
        
        position = ""
        position_patterns = [
            r'[-｜|]\s*(.+?(?:工程师|开发|算法|运营|产品经理|实习|研究员|专家|架构|Leader)[^\s-]*)',
            r'【(.+?)】',
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, title)
            if match:
                position = match.group(1).strip()
                position = re.sub(r'面经.*', '', position)
                position = re.sub(r'公司.*', '', position)
                break
        
        if not position:
            if any(kw in combined for kw in ["算法", "algorithm"]):
                position = "算法工程师"
            elif any(kw in combined for kw in ["开发", "后端", "前端"]):
                position = "开发工程师"
            elif any(kw in combined for kw in ["AI", "人工智能", "LLM", "大模型"]):
                position = "AI工程师"
            else:
                position = "技术岗"
        
        return company, position
    
    def _fetch_content_from_dom(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """从 DOM 解析正文"""
        title, body = "", ""
        
        title_selectors = [
            ("span", {"class": lambda x: x and "post-title" in str(x)}),
            ("h1", {}),
            ("div", {"class": lambda x: x and "title" in str(x).lower()}),
        ]
        
        for tag, attrs in title_selectors:
            el = soup.find(tag, attrs) if attrs else soup.find(tag)
            if el:
                t = el.get_text(strip=True)
                if t and len(t) < 200:
                    title = t.replace("_牛客网", "").strip()
                    break
        
        content_selectors = [
            ("div", {"class": lambda x: x and "nc-post-content" in str(x)}),
            ("div", {"class": lambda x: x and "post-topic-des" in str(x)}),
            ("div", {"class": lambda x: x and "feed-detail-content" in str(x)}),
            ("div", {"class": lambda x: x and "detail-content" in str(x)}),
            ("div", {"class": lambda x: x and "content-body" in str(x)}),
            ("div", {"class": lambda x: x and "post-content" in str(x)}),
            ("div", {"class": lambda x: x and "article-content" in str(x)}),
        ]
        
        for tag, attrs in content_selectors:
            div = soup.find(tag, attrs)
            if div:
                for t in div(["script", "style"]):
                    t.decompose()
                text = div.get_text(separator="\n", strip=True)
                if len(text) > 50:
                    body = text
                    break
        
        if not body:
            for aid in ["js-post-content", "post-content", "main-content"]:
                div = soup.find(id=aid)
                if div:
                    for t in div(["script", "style"]):
                        t.decompose()
                    text = div.get_text(separator="\n", strip=True)
                    if len(text) > 50:
                        body = text
                        break
        
        return title, body
    
    def _extract_json_object(self, html: str, start_pattern: str) -> dict:
        """
        从 HTML 中提取 JSON 对象
        正确处理嵌套花括号和转义字符
        """
        match = re.search(start_pattern, html)
        if not match:
            return {}
        
        start_pos = match.start()
        
        depth = 0
        in_string = False
        escape_next = False
        json_start = match.end() - 1
        
        i = json_start
        while i < len(html) and i < start_pos + 500000:
            c = html[i]
            
            if escape_next:
                escape_next = False
                i += 1
                continue
            
            if c == '\\' and in_string:
                escape_next = True
                i += 1
                continue
            
            if c == '"' and not escape_next:
                in_string = not in_string
                i += 1
                continue
            
            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        json_end = i + 1
                        json_str = html[json_start:json_end]
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                        break
            
            i += 1
        
        return {}
    
    def _extract_from_initial_state(self, html: str) -> Tuple[str, str]:
        """从 __INITIAL_STATE__ JSON 中提取正文"""
        data = self._extract_json_object(html, r'window\.__INITIAL_STATE__\s*=\s*\{')
        
        if not data:
            return "", ""
        
        try:
            if 'prefetchData' in data:
                for k, v in data['prefetchData'].items():
                    if isinstance(v, dict) and 'ssrCommonData' in v:
                        content_data = v['ssrCommonData'].get('contentData', {})
                        if content_data:
                            title = content_data.get('title', '')
                            content = content_data.get('content', '')
                            
                            if content:
                                content = re.sub(r'!\[.*?\]\([^\)]+\)', '', content)
                                content = re.sub(r'<[^>]+>', '', content)
                                content = re.sub(r'\n{3,}', '\n\n', content)
                                return title.strip(), content.strip()
            
            if 'postDetail' in data and data['postDetail']:
                title = data['postDetail'].get('title', '')
                content = data['postDetail'].get('content', '')
                
                if content:
                    content = re.sub(r'!\[.*?\]\([^\)]+\)', '', content)
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    return title.strip(), content.strip()
        
        except Exception:
            pass
        
        return "", ""
    
    def _extract_experience_questions(self, html: str) -> List[dict]:
        """
        从 __INITIAL_STATE__ 中提取 experienceQuestionList
        这是牛客网面经的详细问题回答
        """
        data = self._extract_json_object(html, r'window\.__INITIAL_STATE__\s*=\s*\{')
        
        if not data:
            return []
        
        try:
            if 'prefetchData' in data:
                for k, v in data['prefetchData'].items():
                    if isinstance(v, dict) and 'ssrCommonData' in v:
                        exp_list = v['ssrCommonData'].get('experienceQuestionList', [])
                        if exp_list:
                            return exp_list
            
            return []
            
        except Exception:
            return []
    
    def _format_experience_questions(self, exp_list: List[dict]) -> str:
        """格式化 experienceQuestionList 为可读文本"""
        lines = []
        lines.append("=" * 50)
        lines.append("【面经详细问题与回答】")
        lines.append("=" * 50)
        
        for i, q in enumerate(exp_list, 1):
            title = q.get('title', '')
            answer = q.get('answer', '')
            
            # 将转义的换行符 \\n 转换为真正的换行符
            answer = answer.replace('\\n', '\n')
            
            lines.append(f"\n## 问题 {i}: {title}")
            lines.append("")
            lines.append(answer)
            lines.append("")
        
        return '\n'.join(lines)
    
    def _parse_page(self, html: str, page_url: str = "") -> list:
        """解析页面获取面经列表"""
        soup = BeautifulSoup(html, 'html.parser')
        interviews = []
        
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            
            if '/discuss/' not in href and '/feed/' not in href:
                continue
            
            url_path = href.split('?')[0]
            if not url_path or url_path in self._visited_urls:
                continue
            
            text = link.get_text(strip=True)
            
            if len(text) < 15:
                continue
            
            self._visited_urls.add(url_path)
            
            full_url = self.BASE_URL + url_path
            
            parent = link.find_parent(['div', 'li', 'article', 'tr', 'td'])
            parent_text = ""
            if parent:
                parent_text = parent.get_text()
            
            date_str = self._extract_date_from_text(parent_text) or datetime.now().strftime("%Y-%m-%d")
            
            title = self._clean_text(text)[:200]
            
            interview = Interview(
                title=title,
                content="",
                url=full_url,
                date=date_str
            )
            
            company, position = self._extract_company_position(title, parent_text)
            interview.company = company
            interview.position = position
            
            interviews.append(interview)
        
        return interviews
    
    def _search_by_ajax(self, keyword: str, page: int = 1) -> List[dict]:
        """使用 AJAX API 搜索"""
        from urllib.parse import quote
        
        current_timestamp = int(time.time() * 1000)
        api_url = f"https://gw-c.nowcoder.com/api/sparta/pc/search?_={current_timestamp}"
        
        payload = {
            "type": "all",
            "query": keyword,
            "page": page,
            "tag": [],
            "order": "",
        }
        
        safe_keyword = quote(keyword)
        headers = self.session.headers.copy()
        headers.update({
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.nowcoder.com/search/all?query={safe_keyword}&type=all",
            "Origin": "https://www.nowcoder.com",
            "Accept": "application/json, text/plain, */*",
        })
        
        try:
            resp = self.session.post(api_url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            records = data.get("data", {}).get("records", [])
            
            results = []
            for rec in records:
                try:
                    moment = rec.get("data", {}).get("momentData", {})
                    content_id = moment.get("id") or rec.get("data", {}).get("contentId")
                    uuid = moment.get("uuid", "")
                    
                    if not content_id or not uuid:
                        continue
                    
                    title = moment.get("title", "")
                    post_url = f"{self.BASE_URL}/feed/main/detail/{uuid}"
                    
                    created_at = moment.get("createdAt", 0)
                    pub_time = self._timestamp_to_date(created_at) if created_at else ""
                    
                    results.append({
                        "title": title,
                        "url": post_url,
                        "date": pub_time,
                    })
                except Exception:
                    continue
            
            return results
            
        except Exception as e:
            print(f"AJAX 搜索失败: {e}")
            return []
    
    def search_by_keyword(self, keyword: str, max_results: int = 10, days_range: int = 7) -> list:
        """按关键词搜索面经"""
        interviews = []
        page = 1
        cutoff_date = (datetime.now() - timedelta(days=days_range)).strftime("%Y-%m-%d")
        
        while len(interviews) < max_results and page <= 5:
            print(f"搜索关键词: {keyword} 第 {page} 页...")
            
            ajax_results = self._search_by_ajax(keyword, page)
            
            if ajax_results:
                for result in ajax_results:
                    if len(interviews) >= max_results:
                        break
                    
                    interview = Interview(
                        title=result["title"][:200],
                        content="",
                        url=result["url"],
                        date=result["date"] or cutoff_date
                    )
                    
                    company, position = self._extract_company_position(interview.title)
                    interview.company = company
                    interview.position = position
                    
                    if interview.date and interview.date >= cutoff_date:
                        interviews.append(interview)
                    elif not interview.date:
                        interviews.append(interview)
                
                page += 1
                self._random_delay(2, 4)
            else:
                break
        
        return interviews[:max_results]
    
    def search_by_tag(self, tag_id: str = "643", max_results: int = 10, days_range: int = 7) -> list:
        """按标签搜索面经"""
        interviews = []
        page = 1
        cutoff_date = (datetime.now() - timedelta(days=days_range)).strftime("%Y-%m-%d")
        
        while len(interviews) < max_results and page <= 10:
            url = f"{self.SEARCH_URL}?tagId={tag_id}&page={page}&sortType=1"
            
            try:
                self._update_headers()
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                page_interviews = self._parse_page(response.text, url)
                
                if not page_interviews:
                    break
                
                for interview in page_interviews:
                    if len(interviews) >= max_results:
                        break
                    
                    if interview.date >= cutoff_date:
                        interviews.append(interview)
                
                page += 1
                self._random_delay()
                
            except requests.RequestException as e:
                print(f"请求失败: {e}")
                break
        
        return interviews[:max_results]
    
    def get_detail(self, url: str) -> Optional[str]:
        """获取面经详情"""
        try:
            self._update_headers()
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            html = response.text
            
            if len(html) < 10000:
                return None
            
            title, body = self._fetch_content_from_dom(BeautifulSoup(html, 'html.parser'))
            
            if not body or len(body) < 100:
                title, body = self._extract_from_initial_state(html)
            
            exp_list = self._extract_experience_questions(html)
            if exp_list:
                body = self._format_experience_questions(exp_list)
            
            if body:
                body = re.sub(r'查看\d+道真题.*?(?=\n|$)', '', body)
                body = re.sub(r'点赞.*?(?:评论|收藏|分享)', '', body)
                body = re.sub(r'收藏.*?(?:评论|分享)', '', body)
                body = re.sub(r'已编辑', '', body)
                body = re.sub(r'\n{3,}', '\n\n', body)
                return self._clean_text(body)
            
            return None
            
        except requests.RequestException as e:
            print(f"获取详情失败 {url}: {e}")
            return None
    
    def fetch_interviews(self, keywords: list, max_per_keyword: int = 10, days_range: int = 7) -> list:
        """批量获取面经"""
        self._visited_urls.clear()
        all_interviews = []
        seen_urls: Set[str] = set()
        
        print("使用牛客网标签页采集...")
        
        tag_interviews = self.search_by_tag(tag_id="643", max_results=max_per_keyword * 3, days_range=days_range)
        for interview in tag_interviews:
            if interview.url not in seen_urls:
                seen_urls.add(interview.url)
                all_interviews.append(interview)
        
        for keyword in keywords:
            print(f"搜索关键词: {keyword}")
            
            interviews = self.search_by_keyword(keyword, max_per_keyword, days_range)
            
            for interview in interviews:
                if interview.url not in seen_urls:
                    seen_urls.add(interview.url)
                    all_interviews.append(interview)
            
            self._random_delay(2, 4)
        
        print(f"牛客网共获取 {len(all_interviews)} 篇面经")
        return all_interviews


def test():
    """测试爬虫"""
    spider = nowcoderSpider ()
    
    interviews = spider.search_by_tag(max_results=5)
    
    for interview in interviews:
        print(f"\n标题: {interview.title[:60]}...")
        print(f"URL: {interview.url}")
        print(f"公司: {interview.company}")
        print(f"日期: {interview.date}")


if __name__ == "__main__":
    test()
