"""
Agent 状态持久化 - 支持 checkpoint 保存和加载
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class AgentCheckpoint:
    timestamp: str
    agent_name: str
    state: Dict[str, Any]
    metadata: Dict[str, Any]


class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "./memory/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_checkpoint(
        self,
        agent_name: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        checkpoint = AgentCheckpoint(
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            state=state,
            metadata=metadata or {}
        )
        
        filename = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.checkpoint_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(checkpoint), f, ensure_ascii=False, indent=2)
            self.logger.info(f"Checkpoint saved: {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def load_checkpoint(self, filepath: str) -> AgentCheckpoint:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            checkpoint = AgentCheckpoint(**data)
            self.logger.info(f"Checkpoint loaded: {filepath}")
            return checkpoint
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            raise
    
    def get_latest_checkpoint(self, agent_name: str) -> Optional[AgentCheckpoint]:
        checkpoints = sorted(
            self.checkpoint_dir.glob(f"{agent_name}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if checkpoints:
            return self.load_checkpoint(str(checkpoints[0]))
        return None
    
    def list_checkpoints(self, agent_name: Optional[str] = None) -> list:
        if agent_name:
            pattern = f"{agent_name}_*.json"
        else:
            pattern = "*.json"
        
        checkpoints = []
        for filepath in sorted(self.checkpoint_dir.glob(pattern), reverse=True):
            try:
                checkpoint = self.load_checkpoint(str(filepath))
                checkpoints.append({
                    'filepath': str(filepath),
                    'timestamp': checkpoint.timestamp,
                    'agent_name': checkpoint.agent_name,
                    'metadata': checkpoint.metadata
                })
            except Exception as e:
                self.logger.warning(f"Failed to load checkpoint {filepath}: {e}")
        
        return checkpoints
    
    def cleanup_old_checkpoints(self, agent_name: str, keep_count: int = 5):
        checkpoints = sorted(
            self.checkpoint_dir.glob(f"{agent_name}_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for checkpoint in checkpoints[keep_count:]:
            try:
                checkpoint.unlink()
                self.logger.info(f"Deleted old checkpoint: {checkpoint}")
            except Exception as e:
                self.logger.warning(f"Failed to delete checkpoint {checkpoint}: {e}")
