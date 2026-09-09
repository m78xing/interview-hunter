"""
分析工作流 - 从面经中提取 Q&A 卡片
"""
import json
import re
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from .collector import RawPost
from ..storage import Card
from ..config.settings import DEFAULT_COMPANIES, DEFAULT_POSITIONS


class AnalyzerWorkflow:
    """分析工作流 - 负责从面经中提取卡片"""
    
    CARD_EXTRACTION_PROMPT = """
你是一个面经知识提炼专家。请从以下面经中提取 3-5 个核心面试问题和详细答案。

面经标题：{title}
面经内容：{content}

请按以下JSON格式输出：
{{
    "cards": [
        {{
            "question": "面试问题",
            "answer": "详细答案（包含关键知识点）",
            "difficulty": "easy/medium/hard",
            "tags": ["标签1", "标签2"]
        }}
    ],
    "summary": "面经摘要"
}}
"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        duplicate_threshold: float = 0.92,
        similar_threshold: float = 0.75,
        companies: Optional[List[str]] = None,
        positions: Optional[List[str]] = None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.duplicate_threshold = duplicate_threshold
        self.similar_threshold = similar_threshold
        self.companies = companies or DEFAULT_COMPANIES
        self.positions = positions or DEFAULT_POSITIONS
        
        self.stats = {
            "processed": 0,
            "cards_generated": 0,
            "duplicates_skipped": 0,
            "similar_merged": 0
        }
        
        self.logger = logging.getLogger(__name__)
    
    def _call_llm(self, prompt: str) -> Optional[Dict]:
        """调用 LLM"""
        if not self.api_key:
            self.logger.warning("API key 为空，跳过 LLM 调用")
            return None

        from httpx import ReadTimeout
        
        try:
            import httpx
            
            with httpx.Client(timeout=httpx.Timeout(60.0, read=120.0)) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.startswith('```'):
                        content = content[3:]
                    if content.endswith('```'):
                        content = content[:-3]
                    
                    return json.loads(content.strip())
                else:
                    self.logger.error(f"LLM 调用失败: {response.status_code}")
                    return None
                    
        except ReadTimeout as e:
            self.logger.error(f"LLM 调用超时: {e}")
            return None
        except Exception as e:
            self.logger.error(f"LLM 调用异常: {e}")
            return None
    
    def _extract_cards_by_rules(self, post: RawPost) -> List[Dict]:
        """基于规则提取卡片（无 LLM 时的 fallback）"""
        cards = []
        content = post.content
        
        question_patterns = [
            r'[\d一二三四五六七八九十]+\.\s*(.+)',
            r'问[：:]\s*(.+)',
            r'面试问题[：:]\s*(.+)',
            r'(.+?)\?\s*',
            r'(.+?)\？\s*',
        ]
        
        questions = []
        for pattern in question_patterns:
            matches = re.findall(pattern, content)
            questions.extend(matches)
        
        for q in questions[:5]:
            q = q.strip()
            if len(q) > 5 and len(q) < 200:
                answer_start = content.find(q) if q in content else -1
                if answer_start > 0:
                    answer = content[answer_start:answer_start+500]
                else:
                    answer = content[:500]
                
                tags = []
                for kw in ['大模型', 'LLM', 'Agent', '深度学习', '机器学习', '神经网络', 'Transformer', 'RAG', '向量']:
                    if kw in q or kw in content:
                        tags.append(kw)
                if not tags:
                    tags = ['面试题']
                
                cards.append({
                    'question': q,
                    'answer': answer[:500],
                    'difficulty': 'medium',
                    'tags': tags
                })
        
        return cards
    
    def _extract_company_position(self, title: str, content: str) -> Tuple[str, str]:
        """提取公司和岗位"""
        company = "其他"
        for c in self.companies:
            if c in title or c in content[:500]:
                company = c
                break
        
        position = "技术岗"
        for p in self.positions:
            if p in title:
                position = p
                break
        
        return company, position
    
    async def analyze(self, raw_posts: List[RawPost]) -> List[Card]:
        """分析原始帖子，提取卡片"""
        self.logger.info(f"开始分析 {len(raw_posts)} 篇帖子")
        
        all_cards = []
        
        for post in raw_posts:
            try:
                cards = await self._analyze_post(post)
                all_cards.extend(cards)
                self.stats["processed"] += 1
                self.stats["cards_generated"] += len(cards)
            except Exception as e:
                self.logger.error(f"分析帖子失败: {e}")
        
        self.logger.info(f"分析完成，生成 {len(all_cards)} 张卡片")
        
        return all_cards
    
    async def _analyze_post(self, post: RawPost) -> List[Card]:
        """分析单个帖子"""
        company, position = self._extract_company_position(post.title, post.content)
        
        prompt = self.CARD_EXTRACTION_PROMPT.format(
            title=post.title,
            content=post.content
        )
        
        result = self._call_llm(prompt)
        
        if not result or 'cards' not in result:
            self.logger.info("LLM 解析失败，使用规则提取")
            card_data_list = self._extract_cards_by_rules(post)
        else:
            card_data_list = result['cards']
        
        cards = []
        for card_data in card_data_list:
            card_id = self._generate_card_id(
                card_data['question'] + post.url
            )
            
            card = Card(
                id=card_id,
                question=card_data['question'],
                answer=card_data['answer'],
                company=company,
                position=position,
                tags=card_data.get('tags', []),
                difficulty=card_data.get('difficulty', 'medium'),
                source_url=post.url,
                source_platform=post.platform,
                created_at=datetime.now().isoformat()
            )
            cards.append(card)
        
        return cards
    
    def _generate_card_id(self, text: str) -> str:
        """生成卡片ID"""
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    def check_duplicate(self, card: Card, chroma_client) -> Tuple[bool, Optional[str]]:
        """检查重复"""
        text = f"{card.question} {card.answer}"
        
        result = chroma_client.check_duplicate(text, self.duplicate_threshold)
        
        if result:
            self.stats["duplicates_skipped"] += 1
            return True, result.get('id')
        
        return False, None
    
    def check_similar(self, card: Card, chroma_client) -> Optional[Dict]:
        """检查相似"""
        text = f"{card.question} {card.answer}"
        
        results = chroma_client.search_similar(text, n_results=3, threshold=self.similar_threshold)
        
        if results and len(results) > 0:
            self.stats["similar_merged"] += 1
            return results[0]
        
        return None
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
