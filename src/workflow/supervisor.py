"""
采集编排器 - 协调采集工作流各环节执行
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict

from .collector import CollectorWorkflow, RawPost
from .analyzer import AnalyzerWorkflow
from .scheduler import SchedulerWorkflow
from ..storage import SQLiteClient, ChromaClient, Card
from ..core import HeartbeatDriver, RecommendationEngine, LLMAuditor
from ..core.checkpoint_manager import CheckpointManager


@dataclass
class SystemState:
    """系统状态"""
    running: bool = False
    last_heartbeat: Optional[datetime] = None
    collector_status: str = "idle"
    analyzer_status: str = "idle"
    scheduler_status: str = "idle"
    errors: List[Dict] = field(default_factory=list)


class CollectionOrchestrator:
    """采集编排器 - 负责协调采集工作流"""
    
    def __init__(
        self,
        sqlite_client: SQLiteClient,
        chroma_client: ChromaClient,
        collector: CollectorWorkflow,
        analyzer: AnalyzerWorkflow,
        scheduler: SchedulerWorkflow,
        heartbeat: HeartbeatDriver,
        llm_auditor: Optional[LLMAuditor] = None,
        checkpoint_dir: str = "./memory/checkpoints",
        user_memory = None,
        preference_store = None,
        email_notifier = None
    ):
        self.sqlite = sqlite_client
        self.chroma = chroma_client
        self.collector = collector
        self.analyzer = analyzer
        self.scheduler = scheduler
        self.heartbeat = heartbeat
        self.auditor = llm_auditor
        self.user_memory = user_memory
        self.preference_store = preference_store
        self.email_notifier = email_notifier
        
        self.state = SystemState()
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        
        self.logger = logging.getLogger(__name__)
        
        self._heartbeat_callback: Optional[Callable] = None
    
    def _wrap_heartbeat_sync(self):
        """包装异步心跳回调为同步调用"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 已在事件循环中，调度协程执行
            loop.call_soon(lambda: asyncio.create_task(self._on_heartbeat()))
        except RuntimeError:
            # 无运行中的事件循环，创建新的
            asyncio.run(self._on_heartbeat())
    
    async def initialize(self):
        """初始化系统"""
        self.logger.info("初始化系统...")

        self.heartbeat.set_on_tick(self._wrap_heartbeat_sync)
        self.heartbeat.start()

        self.state.running = True
        self.logger.info("系统初始化完成")

    async def shutdown(self):
        """关闭系统"""
        self.logger.info("关闭系统...")

        self.state.running = False
        self.scheduler.end_session()
        self.heartbeat.stop()

        self.logger.info("系统已关闭")
    
    async def _on_heartbeat(self):
        """心跳回调"""
        self.logger.info("执行心跳任务...")
        self.state.last_heartbeat = datetime.now()
        
        try:
            await self._run_collection_cycle()
            
            await self._run_daily_audit()
            
        except Exception as e:
            self.logger.error(f"心跳任务执行失败: {e}")
            self.state.errors.append({
                "time": datetime.now().isoformat(),
                "error": str(e)
            })
    
    async def _run_collection_cycle(self):
        """运行采集周期"""
        if self.preference_store:
            keywords = self.preference_store.get_keywords("default")
            if keywords:
                self.collector.keywords = keywords
                self.logger.info(f"Keywords from preference store: {keywords}")
            else:
                self.logger.info("No keywords in preference store, using defaults")

        self.state.collector_status = "running"
        self.logger.info(f"采集开始: {datetime.now().isoformat()}")
        
        try:
            raw_posts = await self.collector.collect()
            
            if not raw_posts:
                self.logger.info("没有新的帖子")
                return
            
            self.state.analyzer_status = "running"
            
            cards = await self.analyzer.analyze(raw_posts)
            
            new_count = 0
            duplicate_count = 0
            similar_count = 0
            
            for card in cards:
                is_dup, dup_id = self.analyzer.check_duplicate(card, self.chroma)
                
                if is_dup:
                    duplicate_count += 1
                    self.logger.info(f"卡片重复跳过: {card.id} -> {dup_id}")
                    continue
                
                similar = self.analyzer.check_similar(card, self.chroma)
                if similar:
                    similar_count += 1
                    self.logger.info(f"卡片相似: {card.id} -> {similar}")
                
                self.sqlite.insert_card(card)
                
                text = f"{card.question} {card.answer}"
                metadata = {
                    "company": card.company,
                    "position": card.position,
                    "tags": ",".join(card.tags),
                    "difficulty": card.difficulty
                }
                self.chroma.add_card(card.id, text, metadata)
                
                self.logger.info(f"新增卡片: {card.id} - {card.company}/{card.position}")
                
                new_count += 1
            
            self.logger.info(
                f"采集周期完成: 新增 {new_count}, "
                f"重复 {duplicate_count}, 相似 {similar_count}"
            )
            
            if self.email_notifier and new_count > 0:
                try:
                    total = self.sqlite.get_total_cards()
                    stats = {"total": total, "today": new_count}
                    cards_data = [
                        {
                            "question": card.question,
                            "company": card.company,
                            "position": card.position,
                            "tags": card.tags,
                            "answer": card.answer[:150],
                        }
                        for card in cards[:20]
                    ]
                    self.email_notifier.send_notification(cards_data, stats)
                except Exception as e:
                    self.logger.warning(f"邮件通知发送失败: {e}")
            
        except Exception as e:
            self.logger.error(f"采集周期失败: {e}")
            raise
        finally:
            self.state.collector_status = "idle"
            self.state.analyzer_status = "idle"
    
    async def _run_daily_audit(self):
        """运行每日审计"""
        if not self.auditor:
            return
        
        self.state.scheduler_status = "running"
        
        try:
            result = await self.scheduler.trigger_daily_audit()
            
            if result:
                self.logger.info(f"每日审计完成: {result.get('learning_strategy', '')}")
        
        except Exception as e:
            self.logger.error(f"每日审计失败: {e}")
        finally:
            self.state.scheduler_status = "idle"
    
    def start_learning_session(
        self,
        target_company: str = "",
        limit: int = 20
    ) -> List[Dict]:
        """开始学习会话"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.scheduler.start_session(target_company, limit))
        finally:
            loop.close()
    
    def get_next_card(self) -> Optional[Dict]:
        """获取下一张卡片"""
        return self.scheduler.get_next_card()
    
    def submit_review(self, card_id: str, quality: int, time_taken: int = 0):
        """提交复习结果"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.scheduler.record_review(card_id, quality, time_taken))
        finally:
            loop.close()
    
    def get_recommendations(self, card_id: str, limit: int = 3) -> List[Dict]:
        """获取推荐"""
        return self.scheduler.get_recommendations(card_id, limit)
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "system": {
                "running": self.state.running,
                "last_heartbeat": self.state.last_heartbeat.isoformat() if self.state.last_heartbeat else None,
                "errors": self.state.errors[-5:]
            },
            "agents": {
                "collector": self.state.collector_status,
                "analyzer": self.state.analyzer_status,
                "scheduler": self.state.scheduler_status
            },
            "stats": {
                "collector": self.collector.get_stats(),
                "analyzer": self.analyzer.get_stats(),
                "total_cards": self.sqlite.get_total_cards(),
                "today_reviews": self.sqlite.get_today_review_count()
            },
            "heartbeat": self.heartbeat.get_status()
        }
    
    def update_keywords(self, keywords: List[str]):
        """更新爬虫关键字"""
        self.collector.update_keywords(keywords)
    
    def add_keyword(self, keyword: str):
        """添加关键字"""
        self.collector.add_keyword(keyword)
    
    def remove_keyword(self, keyword: str):
        """移除关键字"""
        self.collector.remove_keyword(keyword)
    
    def save_checkpoint(self, metadata: Optional[Dict] = None) -> str:
        """保存系统状态 checkpoint"""
        state_dict = {
            'system_state': asdict(self.state),
            'collector_stats': self.collector.get_stats(),
            'analyzer_stats': self.analyzer.get_stats(),
            'total_cards': self.sqlite.get_total_cards(),
            'today_reviews': self.sqlite.get_today_review_count(),
            'heartbeat_status': self.heartbeat.get_status()
        }
        
        return self.checkpoint_manager.save_checkpoint(
            agent_name="supervisor",
            state=state_dict,
            metadata=metadata or {'reason': 'manual_save'}
        )
    
    def load_checkpoint(self, checkpoint_path: Optional[str] = None) -> bool:
        """加载系统状态 checkpoint"""
        try:
            if checkpoint_path is None:
                checkpoint = self.checkpoint_manager.get_latest_checkpoint("supervisor")
                if not checkpoint:
                    self.logger.warning("No checkpoint found")
                    return False
            else:
                checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_path)
            
            if checkpoint and checkpoint.state:
                state_data = checkpoint.state.get('system_state', {})
                self.state.running = state_data.get('running', False)
                self.state.last_heartbeat = datetime.fromisoformat(state_data['last_heartbeat']) if state_data.get('last_heartbeat') else None
                self.state.collector_status = state_data.get('collector_status', 'idle')
                self.state.analyzer_status = state_data.get('analyzer_status', 'idle')
                self.state.scheduler_status = state_data.get('scheduler_status', 'idle')
                self.state.errors = state_data.get('errors', [])
                
                self.logger.info(f"Checkpoint loaded successfully from {checkpoint.timestamp}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
        
        return False
    
    def list_checkpoints(self) -> list:
        """列出所有 checkpoint"""
        return self.checkpoint_manager.list_checkpoints("supervisor")
    
    def cleanup_old_checkpoints(self, keep_count: int = 5):
        """清理旧的 checkpoint"""
        self.checkpoint_manager.cleanup_old_checkpoints("supervisor", keep_count)
    
    def update_keywords_from_preferences(self):
        """根据用户偏好更新爬虫关键字"""
        if not self.user_memory:
            self.logger.warning("User memory not available, skipping preference-based keyword update")
            return
        
        try:
            keywords = self.user_memory.generate_keywords()
            self.collector.update_keywords(keywords)
            
            self.logger.info(f"根据用户偏好更新关键字: {keywords}")
        except Exception as e:
            self.logger.error(f"Failed to update keywords from preferences: {e}")
