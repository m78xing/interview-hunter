"""
XHSSpider - 小红书面经爬虫

爬取小红书面经内容
参考 InterviewExperienceCrawlerAgent 的 xhs_crawler.py 实现

登录状态说明：
- 首次使用需要扫码登录，状态会保存到本地
- 后续定时任务可复用登录状态

使用方法：
- 首次登录: python -m subagents.interview_collector.xhs_spider --login
- 检查状态: python -m subagents.interview_collector.xhs_spider --status
"""

import asyncio
import re
import time
import random
import os
import logging
from datetime import datetime
from typing import Optional, Set, List, Dict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote as urlquote
import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


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


class XHSSpider:
    """小红书面经爬虫"""
    
    BASE_URL = "https://www.xiaohongshu.com"
    SEARCH_URL = "https://www.xiaohongshu.com/search_result"
    
    def __init__(self, timeout: int = 30, user_data_dir: str = None):
        self.timeout = timeout
        
        if user_data_dir is None:
            user_data_dir = str(Path(__file__).parent / "xhs_user_data")
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        
        self._visited_urls: Set[str] = set()
    
    def _cleanup_chrome_locks(self):
        """清理 Chrome 遗留的锁文件"""
        for lock_name in ("SingletonLock", "SingletonCookie", "lockfile", ".com.google.Chrome.LOCK"):
            lock_path = os.path.join(self.user_data_dir, lock_name)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                    logger.info(f"已清理 Chrome 锁文件: {lock_path}")
                except Exception:
                    pass
    
    def _is_logged_in(self, page) -> bool:
        """
        增强版登录检测
        
        判断逻辑：
        1. 如果 URL 包含 login/signin → 未登录
        2. 如果存在二维码元素 → 未登录（即使有其他元素）
        3. 如果存在用户头像或昵称 → 已登录
        4. 其他情况 → 未登录
        """
        try:
            current_url = page.url.lower()
            
            # 1. URL 检查：登录页直接返回 False
            if "login" in current_url or "signin" in current_url:
                return False
            
            # 2. 反向检查：二维码元素存在 = 未登录
            qr_selectors = [
                "[class*='qrcode']",
                "[class*='qr-code']",
                "[class*='login-qr']",
                "[class*='scan-qr']",
                "canvas[class*='qr']"
            ]
            for selector in qr_selectors:
                if page.locator(selector).count() > 0:
                    logger.debug(f"检测到二维码元素: {selector}")
                    return False
            
            # 3. 正向检查：必须存在用户头像或昵称
            login_indicators = [
                ".user-avatar",
                ".avatar",
                ".nickname",
                "[class*='userInfo']",
                "[class*='user-info']",
                "[class*='login-name']"
            ]
            for selector in login_indicators:
                if page.locator(selector).count() > 0:
                    logger.debug(f"检测到登录元素: {selector}")
                    return True
            
            # 4. 兜底：搜索结果卡片存在说明已加载内容
            if page.locator("section.note-item, div[class*='note-item']").count() > 0:
                logger.debug("检测到搜索结果卡片")
                return True
            
            logger.debug("未检测到任何登录状态元素")
            return False
            
        except Exception:
            return False
    
    def _wait_for_login(self, page, wait_seconds: int = 120) -> bool:
        """
        在弹出浏览器中等待用户扫码登录。
        每 5 秒检测一次登录状态，超时后返回 False。
        """
        logger.warning(
            f"⚠️  未检测到小红书登录状态，请在弹出的浏览器窗口中扫码登录。"
            f"将等待最多 {wait_seconds} 秒后自动继续..."
        )
        deadline = time.time() + wait_seconds
        check_interval = 5
        
        while time.time() < deadline:
            remaining = int(deadline - time.time())
            try:
                page.wait_for_timeout(check_interval * 1000)
                
                # 详细调试信息
                is_logged_in = self._is_logged_in(page)
                logger.info(f"   登录检测结果: {is_logged_in}, URL: {page.url[:50]}..., 剩余 {remaining} 秒")
                
                if is_logged_in:
                    logger.info("✅ 检测到登录成功，继续...")
                    return True
                    
            except Exception as e:
                logger.warning(f"   检测过程出错: {e}")
                break
        
        logger.warning(f"⏰ 等待 {wait_seconds} 秒后仍未登录")
        return False
    
    def _get_search_links_with_playwright(
        self,
        keyword: str = "面经",
        max_notes: int = 20,
        headless: bool = False,
    ) -> List[Dict]:
        """使用 Playwright 获取小红书搜索结果链接"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright 未安装: pip install playwright && playwright install chromium")
            return []
        
        self._cleanup_chrome_locks()
        
        results: List[Dict] = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=headless,
                    viewport={"width": 1920, "height": 1080},
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"],
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                
                search_url = (
                    f"{self.SEARCH_URL}"
                    f"?keyword={urlquote(keyword)}&source=web_search_result_notes"
                )
                logger.info(f"XHS 访问搜索页: {search_url}")
                
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    logger.warning(f"XHS 页面加载超时，尝试继续: {e}")
                page.wait_for_timeout(4000)
                
                logged_in = self._is_logged_in(page)
                if not logged_in:
                    if headless:
                        logger.warning(
                            "XHS 未登录（headless 模式）。"
                            "请先以 --login 参数运行完成扫码，"
                            "登录状态将保存到 xhs_user_data 供后续复用。"
                        )
                        browser.close()
                        return []
                    else:
                        logger.info("浏览器已打开，请在浏览器中扫码登录小红书...")
                        if not self._wait_for_login(page, wait_seconds=120):
                            browser.close()
                            return []
                        try:
                            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                        except Exception:
                            pass
                        page.wait_for_timeout(4000)
                
                try:
                    page.wait_for_selector(
                        "section.note-item, div[class*='note-item'], "
                        "div.note-item, a[href*='/explore/']",
                        timeout=20000
                    )
                except Exception:
                    logger.warning("XHS 未找到搜索结果（可能登录状态已过期或页面结构变化）")
                
                cards = page.locator(
                    "section.note-item, div[class*='note-item'], div.note-item"
                ).all()
                logger.info(f"XHS 找到 {len(cards)} 个结果卡片")
                
                if not cards:
                    logger.warning("XHS 未找到任何卡片，检查选择器或登录状态")
                    browser.close()
                    return []
                
                processed_ids: set = set()
                
                for card in cards:
                    if len(results) >= max_notes:
                        break
                    try:
                        title_elem = card.locator(".title span, h3, [class*='title']").first
                        title = title_elem.inner_text().strip() if title_elem.count() > 0 else "无标题"
                        
                        card.click(button="left", timeout=5000)
                        try:
                            page.wait_for_url("**/explore/*", wait_until="domcontentloaded", timeout=10000)
                        except Exception:
                            page.wait_for_timeout(2000)
                        
                        current_url = page.url
                        note_id = current_url.split("/")[-1].split("?")[0]
                        
                        if note_id not in processed_ids and note_id:
                            processed_ids.add(note_id)
                            results.append({"title": title, "link": current_url})
                            logger.info(f"XHS 获取链接 [{len(results)}/{max_notes}]: {title[:30]}")
                        
                        try:
                            page.go_back(wait_until="domcontentloaded", timeout=10000)
                        except Exception:
                            pass
                        page.wait_for_timeout(random.uniform(1500, 3000))
                        
                    except Exception as e:
                        logger.debug(f"XHS 单卡片获取失败，跳过: {e}")
                        if "explore" in page.url:
                            try:
                                page.go_back(wait_until="domcontentloaded", timeout=10000)
                                page.wait_for_timeout(2000)
                            except Exception:
                                pass
                
                browser.close()
                
        except Exception as e:
            logger.error(f"Playwright 执行出错: {e}")
        
        logger.info(f"XHS keyword={keyword!r} 共获取 {len(results)} 条链接")
        return results
    
    def _fetch_detail_with_playwright(self, url: str, headless: bool = True) -> Optional[Dict]:
        """使用 Playwright 获取帖子详情"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None
        
        self._cleanup_chrome_locks()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=headless,
                    viewport={"width": 1920, "height": 1080},
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"],
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
                
                data = page.evaluate("""() => {
                    try {
                        const s = window.__INITIAL_STATE__ || {};
                        const noteId = (window.__INITIAL_STATE__?.note?.noteId || location.pathname.split('/').pop()?.split('?')[0]) || '';
                        const noteMap = s.note?.noteDetailMap || {};
                        const note = noteMap[noteId]?.note || Object.values(noteMap)[0]?.note;
                        if (note) {
                            return {
                                title: note.title || '',
                                content: note.desc || '',
                                time: note.time || note.lastModifyTime || note.createTime || 0
                            };
                        }
                    } catch {}
                    return null;
                }""")
                
                if data and (data.get("content") or "").strip():
                    browser.close()
                    post_time = ""
                    if data.get("time"):
                        try:
                            post_time = datetime.fromtimestamp(data["time"] / 1000).strftime("%Y-%m-%d")
                        except Exception:
                            pass
                    return {
                        "title": data.get("title", "").strip(),
                        "content": data.get("content", "").strip(),
                        "date": post_time
                    }
                
                desc_el = page.query_selector(".desc, [class*='desc'], .note-content")
                if desc_el:
                    content = desc_el.inner_text()
                    title_el = page.query_selector("h1, .title")
                    title = title_el.inner_text() if title_el else ""
                    browser.close()
                    return {"title": title.strip(), "content": content.strip(), "date": ""}
                
                browser.close()
                
        except Exception as e:
            logger.debug(f"Playwright 详情获取失败: {e}")
        
        return None
    
    def login(self, wait_seconds: int = 120) -> bool:
        """
        弹出浏览器进行扫码登录
        返回 True 表示登录成功
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright 未安装")
            return False
        
        logger.info(f"打开小红书登录窗口，请扫码... 最多等待 {wait_seconds} 秒")
        
        self._cleanup_chrome_locks()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=False,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"],
                )
                
                page = browser.pages[0] if browser.pages else browser.new_page()
                logger.info(f"正在访问: {self.BASE_URL}")
                page.goto(f"{self.BASE_URL}", wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(2000)
                
                logger.info(f"页面加载完成，当前URL: {page.url}")
                
                is_logged = self._is_logged_in(page)
                logger.info(f"首次登录检测结果: {is_logged}")
                
                if is_logged:
                    logger.info("✅ 已处于登录状态，无需重复扫码")
                    browser.close()
                    return True
                
                logger.info("未检测到登录状态，开始等待扫码...")
                if not self._wait_for_login(page, wait_seconds=wait_seconds):
                    browser.close()
                    return False
                
                browser.close()
                return True
                
        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return False
        
        self._cleanup_chrome_locks()
        
        result = False
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=True,
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
                try:
                    page.goto(f"{self.BASE_URL}", wait_until="networkidle", timeout=12000)
                    page.wait_for_timeout(2000)
                    result = self._is_logged_in(page)
                except Exception:
                    pass
                browser.close()
        except Exception:
            pass
        
        return result
    
    def _extract_company_position(self, title: str, content: str = "") -> tuple:
        """从标题和内容提取公司和岗位"""
        company_map = {
            "字节跳动": ["字节跳动", "字节"],
            "腾讯": ["腾讯", "Tencent"],
            "阿里巴巴": ["阿里巴巴", "阿里", "Alibaba"],
            "百度": ["百度", "Baidu"],
            "小米": ["小米", "Xiaomi"],
            "美团": ["美团", "Meituan"],
            "京东": ["京东", "JD"],
            "拼多多": ["拼多多", "PDD"],
            "快手": ["快手", "Kuaishou"],
            "网易": ["网易", "NetEase"],
            "蚂蚁集团": ["蚂蚁", "蚂蚁金服"],
            "华为": ["华为", "Huawei"],
            "滴滴": ["滴滴", "Didi"],
            "小红书": ["小红书"],
            "哔哩哔哩": ["bilibili", "B站", "哔哩哔哩"],
        }
        
        combined = title + " " + (content or "")
        
        company = "其他"
        for c, keywords in company_map.items():
            for kw in keywords:
                if kw in combined:
                    company = c
                    break
            if company != "其他":
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
    
    def _extract_date(self, text: str) -> str:
        """提取日期"""
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                return f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
        
        return datetime.now().strftime("%Y-%m-%d")
    
    def _get_search_links_fallback(self, keyword: str, max_notes: int = 10) -> List[dict]:
        """备用方式获取搜索链接（简单爬取）"""
        results = []
        
        try:
            search_url = f"{self.SEARCH_URL}?keyword={urlquote(keyword)}&source=web_search_result_notes"
            
            response = self.session.get(search_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                if '/explore/' in href or '/discovery/item/' in href:
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    text = link.get_text(strip=True)
                    
                    if text and len(text) > 5 and full_url not in [r['link'] for r in results]:
                        results.append({"title": text[:100], "link": full_url})
                        
                        if len(results) >= max_notes:
                            break
            
        except Exception as e:
            logger.warning(f"备用搜索方式失败: {e}")
        
        return results
    
    def _fetch_detail_simple(self, url: str) -> Optional[str]:
        """简单方式获取帖子详情"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_elem = soup.select_one('.desc, [class*="desc"], .note-content, .content')
            
            if content_elem:
                return content_elem.get_text(separator="\n", strip=True)
            
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and '__INITIAL_STATE__' in script.string:
                    match = re.search(r'"desc"\s*:\s*"([^"]*)"', script.string)
                    if match:
                        return match.group(1)
            
            return response.text[:5000]
            
        except Exception as e:
            logger.warning(f"详情获取失败 {url}: {e}")
            return None
    
    def get_detail(self, url: str) -> Optional[str]:
        """获取帖子详情"""
        data = self._fetch_detail_with_playwright(url, headless=True)
        if data:
            return data.get("content")
        
        return self._fetch_detail_simple(url)
    
    def search_by_keyword(self, keyword: str, max_results: int = 10, days_range: int = 7) -> list:
        """按关键词搜索面经"""
        from datetime import timedelta
        
        interviews = []
        cutoff_date = (datetime.now() - timedelta(days=days_range)).strftime("%Y-%m-%d")
        
        links = self._get_search_links_with_playwright(keyword, max_results, headless=True)
        
        if not links:
            links = self._get_search_links_fallback(keyword, max_results)
        
        for link_info in links[:max_results]:
            url = link_info["link"]
            
            if url in self._visited_urls:
                continue
            self._visited_urls.add(url)
            
            title = link_info["title"]
            content = self.get_detail(url) or ""
            
            if not content:
                content = f"标题: {title}\n来源: {url}"
            
            company, position = self._extract_company_position(title, content)
            
            interview = Interview(
                title=title[:200],
                content=content[:5000],
                url=url,
                company=company,
                position=position,
                date=self._extract_date(content)
            )
            
            if interview.date >= cutoff_date or not interview.date:
                interviews.append(interview)
            
            time.sleep(random.uniform(2, 4))
        
        return interviews
    
    def fetch_interviews(self, keywords: list, max_per_keyword: int = 10, days_range: int = 7) -> list:
        """批量获取面经"""
        self._visited_urls.clear()
        all_interviews = []
        seen_urls = set()
        
        logger.info("使用小红书搜索采集...")
        
        for keyword in keywords:
            logger.info(f"搜索关键词: {keyword}")
            
            interviews = self.search_by_keyword(keyword, max_per_keyword, days_range)
            
            for interview in interviews:
                if interview.url not in seen_urls:
                    seen_urls.add(interview.url)
                    all_interviews.append(interview)
            
            time.sleep(random.uniform(2, 4))
        
        logger.info(f"小红书共获取 {len(all_interviews)} 篇面经")
        return all_interviews


def test():
    """测试爬虫"""
    spider = XHSSpider()
    
    logger.info(f"登录状态: {spider.is_logged_in()}")
    
    interviews = spider.search_by_keyword("大模型 面经", max_results=3)
    
    for interview in interviews:
        logger.info(f"\n标题: {interview.title[:60]}...")
        logger.info(f"URL: {interview.url}")
        logger.info(f"公司: {interview.company}")
        logger.info(f"日期: {interview.date}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="小红书爬虫工具")
    parser.add_argument("--login", action="store_true", help="打开浏览器进行扫码登录")
    parser.add_argument("--status", action="store_true", help="检查登录状态")
    parser.add_argument("--test", action="store_true", help="测试搜索功能")
    
    args = parser.parse_args()
    
    if args.login:
        spider = XHSSpider()
        success = spider.login()
        if success:
            logger.info("✅ 登录成功！")
        else:
            logger.error("❌ 登录失败或超时")
    elif args.status:
        spider = XHSSpider()
        logged_in = spider.is_logged_in()
        logger.info(f"登录状态: {logged_in}")
    elif args.test:
        test()
    else:
        parser.print_help()
