"""
LLM 审计模块
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LLMAuditor:
    """LLM 审计器 - 定期分析学习数据，调整策略"""
    
    AUDIT_PROMPT = """
你是一个面经学习策略分析师。

## 用户学习数据分析

### 最近复习统计
{review_stats}

### 标签错误率
{tag_error_rates}

### 当前爬虫关键字
{current_keywords}

### 薄弱标签
{weak_tags}

### 掌握度矩阵
{mastery_matrix}

## 请给出以下建议（JSON格式）：

{{
    "learning_strategy": "学习策略建议（1-2句话）",
    "keyword_adjustments": [
        {{
            "action": "add/remove/increase_priority",
            "keyword": "关键词",
            "reason": "原因"
        }}
    ],
    "focus_areas": ["需要重点加强的领域"],
    "deprioritize_areas": ["可以暂时放低的领域"],
    "difficulty_adjustments": {{
        "tag_name": "easy/medium/hard"
    }}
}}
"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        consecutive_errors_threshold: int = 5,
        error_rate_threshold: float = 0.6
    ):
        self.api_key = api_key
        self.model = model
        self.consecutive_errors_threshold = consecutive_errors_threshold
        self.error_rate_threshold = error_rate_threshold
        
        self.last_audit_time: Optional[datetime] = None
        self.audit_history: List[Dict] = []
    
    def _call_llm(self, prompt: str) -> Optional[Dict]:
        """调用 LLM"""
        try:
            import httpx
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个数据分析专家，只返回JSON格式的回答。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000
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
                    logger.error(f"LLM 调用失败: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"LLM 调用异常: {e}")
            return None
    
    def should_trigger_threshold_audit(
        self,
        tag: str,
        consecutive_errors: int,
        error_rate: float
    ) -> bool:
        """检查是否应该触发阈值审计"""
        return (
            consecutive_errors >= self.consecutive_errors_threshold and
            error_rate >= self.error_rate_threshold
        )
    
    def should_trigger_daily_audit(self) -> bool:
        """检查是否应该触发每日审计"""
        if not self.last_audit_time:
            return True
        
        now = datetime.now()
        if now.date() > self.last_audit_time.date():
            if now.hour >= 0 and now.hour < 6:
                return True
        
        return False
    
    def audit(
        self,
        review_stats: Dict,
        tag_error_rates: Dict,
        current_keywords: List[str],
        weak_tags: List[str],
        mastery_matrix: Dict
    ) -> Optional[Dict]:
        """执行审计"""
        logger.info("开始 LLM 审计...")
        
        prompt = self.AUDIT_PROMPT.format(
            review_stats=json.dumps(review_stats, ensure_ascii=False, indent=2),
            tag_error_rates=json.dumps(tag_error_rates, ensure_ascii=False, indent=2),
            current_keywords=", ".join(current_keywords),
            weak_tags=", ".join(weak_tags) if weak_tags else "无",
            mastery_matrix=json.dumps(mastery_matrix, ensure_ascii=False, indent=2)
        )
        
        result = self._call_llm(prompt)
        
        if result:
            self.last_audit_time = datetime.now()
            result['audit_time'] = self.last_audit_time.isoformat()
            self.audit_history.append(result)
            
            logger.info(f"审计完成: {result.get('learning_strategy', '')}")
        
        return result
    
    def analyze_threshold_trigger(
        self,
        tag: str,
        consecutive_errors: int,
        recent_logs: List[Dict]
    ) -> Dict:
        """分析阈值触发的情况，生成轻量级建议"""
        
        error_logs = [log for log in recent_logs if log.get('quality', 0) < 3]
        
        suggestions = []
        
        if consecutive_errors >= self.consecutive_errors_threshold:
            suggestions.append({
                "type": "difficulty_adjustment",
                "tag": tag,
                "action": "reduce_difficulty",
                "reason": f"连续{consecutive_errors}次错误",
                "suggestion": "暂时降低该知识点难度，推荐基础题"
            })
        
        return {
            "triggered_tag": tag,
            "consecutive_errors": consecutive_errors,
            "suggestions": suggestions,
            "needs_llm_audit": len(suggestions) > 2
        }
    
    def get_audit_summary(self) -> Dict:
        """获取审计摘要"""
        return {
            "last_audit_time": self.last_audit_time.isoformat() if self.last_audit_time else None,
            "total_audits": len(self.audit_history),
            "recent_suggestions": self.audit_history[-3:] if self.audit_history else []
        }
