"""
LocalProcessor - 本地处理模块

纯本地处理，无需调用LLM：
1. 关键词提取
2. 摘要生成
3. 公司/岗位提取
4. 标签分类
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ProcessedInterview:
    """处理后的面经"""
    title: str
    company: str
    position: str
    tags: list
    summary: str
    full_content: str
    source_url: str
    source_platform: str
    date: str


class LocalProcessor:
    """本地处理器 - 无需LLM调用"""
    
    TECH_KEYWORDS = {
        "LLM/大模型": ["大模型", "LLM", "LLMs", "语言模型", "GPT", "ChatGPT", "GPT-4", "Claude", "文心", "通义", "GLM", "Baichuan", "Qwen"],
        
        "RAG": ["RAG", "检索增强", "Retrieval", "向量检索", "向量数据库", "embedding", "Embedding", "FAISS", "Milvus", "Pinecone"],
        
        "Agent": ["Agent", "agent", "智能体", "ReAct", "CoT", "思维链", "工具调用", "tool", "planning", "多Agent"],
        
        "LangChain": ["LangChain", "langchain", "LangGraph", "LlamaIndex"],
        
        "深度学习": ["深度学习", "神经网络", "CNN", "RNN", "LSTM", "Transformer", "注意力机制", "attention", "transformer"],
        
        "机器学习": ["机器学习", "ML", "机器学习", "算法", "模型训练", "特征工程", "监督学习", "无监督学习"],
        
        "NLP": ["NLP", "自然语言处理", "分词", "命名实体识别", "NER", "情感分析", "文本分类", "文本生成"],
        
        "Python": ["Python", "python"],
        
        "系统设计": ["系统设计", "架构", "微服务", "分布式", "高并发", "缓存", "数据库", "MySQL", "Redis", "MongoDB"],
        
        "Docker/K8s": ["Docker", "K8s", "Kubernetes", "容器", "container", "k8s"],
        
        "GPU/推理": ["GPU", "CUDA", "推理优化", "模型部署", "vLLM", "TensorRT", "量化", "加速"],
        
        "强化学习": ["强化学习", "RL", "RLHF", "PPO", "reward", "reward model", "人类反馈"],
        
        "向量数据库": ["向量数据库", "vector", "embedding", "milvus", "faiss", "pinecone", "weaviate"],
    }
    
    def __init__(self, summary_length: int = 300):
        self.summary_length = summary_length
    
    def process(self, title: str, content: str, url: str, platform: str = "牛客网", date: str = "") -> ProcessedInterview:
        """
        处理面经内容
        
        Args:
            title: 原始标题
            content: 完整内容
            url: 来源URL
            platform: 来源平台
            date: 日期
            
        Returns:
            ProcessedInterview
        """
        company, position = self._extract_company_position(title)
        
        tags = self._extract_tags(title, content)
        
        summary = self._generate_summary(content)
        
        if not date:
            date = self._extract_date(content) or self._extract_date_from_title(title)
        
        return ProcessedInterview(
            title=title,
            company=company,
            position=position or self._infer_position(title, content),
            tags=tags,
            summary=summary,
            full_content=content,
            source_url=url,
            source_platform=platform,
            date=date or "未知"
        )
    
    def _extract_company_position(self, title: str) -> tuple:
        """提取公司和岗位"""
        companies = {
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
            "商汤": ["商汤", "SenseTime"],
            "旷视": ["旷视", "Megvii"],
            "蔚来": ["蔚来", "NIO"],
            "理想汽车": ["理想", "Li Auto"],
        }
        
        company = "其他"
        for c, keywords in companies.items():
            for kw in keywords:
                if kw in title:
                    company = c
                    break
            if company != "其他":
                break
        
        position = ""
        position_patterns = [
            r'[-｜|]\s*(.+?(?:工程师|开发|算法|实习|研究员|专家|架构|Leader)[^\s-]*)',
            r'【(.+?)】',
            r'面经[:：]\s*(.+?)(?:\s|$)',
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, title)
            if match:
                position = match.group(1).strip()
                position = re.sub(r'面经.*', '', position)
                break
        
        return company, position
    
    def _extract_tags(self, title: str, content: str) -> list:
        """提取技术标签"""
        tags = []
        text = title + " " + content
        
        for tag, keywords in self.TECH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text.lower() or kw in text:
                    if tag not in tags:
                        tags.append(tag)
                    break
        
        if not tags:
            tags.append("其他技术")
        
        return tags[:8]
    
    def _generate_summary(self, content: str) -> str:
        """生成摘要 - 纯规则方式"""
        if not content:
            return ""
        
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        summary_parts = []
        question_count = 0
        
        for line in lines:
            if len(line) < 10 or len(line) > 300:
                continue
            
            if '？' in line or '?' in line:
                question_count += 1
                if question_count <= 5:
                    clean_line = re.sub(r'^[0-9a-zA-Z]+[、.)]?\s*', '', line)
                    summary_parts.append(clean_line)
        
        if summary_parts:
            summary = '；'.join(summary_parts[:5])
        else:
            first_lines = [l for l in lines if 20 < len(l) < 200][:3]
            summary = '；'.join(first_lines)
        
        if len(summary) > self.summary_length:
            summary = summary[:self.summary_length] + "..."
        
        return summary
    
    def _extract_date(self, content: str) -> Optional[str]:
        """从内容提取日期"""
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                groups = match.groups()
                return f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
        
        return None
    
    def _extract_date_from_title(self, title: str) -> Optional[str]:
        """从标题提取日期"""
        patterns = [
            r'(\d{1,2})[月](\d{1,2})日?',
            r'(\d{2})/(\d{1,2})',
        ]
        
        from datetime import datetime
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                groups = match.groups()
                if len(groups[0]) == 4:
                    return f"{groups[0]}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                else:
                    year = datetime.now().year
                    return f"{year}-{int(groups[0]):02d}-{int(groups[1]):02d}"
        
        return None
    
    def _infer_position(self, title: str, content: str) -> str:
        """推断岗位"""
        text = title + " " + content
        
        position_map = {
            "算法工程师": ["算法工程师", "算法岗", "算法面经"],
            "后端开发": ["后端", "服务端", "Go开发", "Java开发", "Python开发"],
            "大模型开发": ["大模型", "LLM", "AI应用", "Agent开发"],
            "前端开发": ["前端", "FE"],
            "测试开发": ["测试", "QA"],
            "运维开发": ["运维", "SRE", "DevOps"],
        }
        
        for position, keywords in position_map.items():
            for kw in keywords:
                if kw in text:
                    return position
        
        return "技术岗"
