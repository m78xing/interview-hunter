"""
心胜调度器 - 基于 APScheduler 的定时任务

重构版本:
1. start() 时校验 on_tick 已设置
2. 简化异步处理 - 统一要求调用方传入同步函数或已 await 的结果
3. 清晰的错误提示
"""
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, List
from enum import Enum
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class HeartbeatState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"


class HeartbeatDriver:
    """心跳驱动 - 定时触发任务执行"""
    
    def __init__(
        self,
        scheduled_times: Optional[List[str]] = None,
        cooldown_minutes: int = 60,
        on_tick: Optional[Callable] = None
    ):
        self.scheduled_times = scheduled_times or ["08:00"]
        self.cooldown_seconds = cooldown_minutes * 60
        self.on_tick = on_tick  # 可以在构造函数传入，也可以在 start() 前赋值

        self.state = HeartbeatState.IDLE
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.consecutive_errors = 0

        self.logger = logging.getLogger(__name__)
        self._scheduler = BackgroundScheduler(daemon=True)
    
    def start(self):
        """启动定时调度"""
        # 校验: on_tick 必须在启动前设置
        if not self.on_tick:
            raise ValueError(
                "on_tick must be set before start(). "
                "Either pass it in constructor or assign it before start()."
            )
        
        for time_str in self.scheduled_times:
            hour, minute = map(int, time_str.split(':'))
            self._scheduler.add_job(
                self._execute_task,
                CronTrigger(hour=hour, minute=minute),
                id=f'heartbeat_{time_str.replace(":", "")}',
                replace_existing=True,
                max_instances=1,
            )

        self._scheduler.start()
        self.next_run = self._get_next_run()
        if self.next_run:
            self.logger.info(f"APScheduler 启动，下次执行: {self.next_run.strftime('%Y-%m-%d %H:%M')}")
    
    def stop(self):
        """停止调度"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self.logger.info("定时调度已停止")
    
    def trigger_now(self):
        """立即触发一次任务"""
        if self.state == HeartbeatState.RUNNING:
            self.logger.warning("任务正在执行中，跳过")
            return
        
        if not self.on_tick:
            self.logger.error("on_tick 未设置，无法触发")
            return
        
        self._execute_task()
    
    def _execute_task(self):
        """执行任务"""
        self.state = HeartbeatState.RUNNING
        self.logger.info(f"[任务] 开始执行 {datetime.now().isoformat()}")

        try:
            if self.on_tick:
                self.on_tick()  # 统一同步调用，调用方负责处理异步
                
            self.last_run = datetime.now()
            self.consecutive_errors = 0
            self.logger.info("[任务] 执行完成")

        except Exception as e:
            self.consecutive_errors += 1
            self.logger.error(f"[任务] 执行失败: {e}")

        self.state = HeartbeatState.IDLE
        self.next_run = self._get_next_run()
    
    def _get_next_run(self) -> Optional[datetime]:
        """获取下次执行时间"""
        if not self.scheduled_times:
            return None

        now = datetime.now()
        earliest = None

        for time_str in self.scheduled_times:
            hour, minute = map(int, time_str.split(':'))
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if target <= now:
                target += timedelta(days=1)

            if earliest is None or target < earliest:
                earliest = target

        return earliest
    
    def get_status(self) -> dict:
        """获取状态"""
        in_cooldown = False
        if self.last_run and self.cooldown_seconds:
            in_cooldown = (datetime.now() - self.last_run).total_seconds() < self.cooldown_seconds

        return {
            "state": self.state.value,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.strftime('%H:%M') if self.next_run else None,
            "scheduled_times": self.scheduled_times,
            "consecutive_errors": self.consecutive_errors,
            "in_cooldown": in_cooldown,
            "on_tick_set": self.on_tick is not None
        }
    
    def set_on_tick(self, callback: Callable):
        """设置回调 - 支持链式调用"""
        self.on_tick = callback
        return self