"""
Context Store - 集中化上下文管理，支持会话级与跨会话上下文、摘要、版本控制
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class ContextSnapshot:
    """上下文快照 - 记录某个时刻的会话上下文"""
    session_id: str
    version: int
    summary: str
    tokens: int
    created_at: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ContextSnapshot':
        return cls(**data)


@dataclass
class ContextManifest:
    """上下文清单 - 管理某个会话的所有版本"""
    session_id: str
    versions: List[ContextSnapshot] = field(default_factory=list)
    latest_version: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_snapshot(self, snapshot: ContextSnapshot) -> None:
        self.versions.append(snapshot)
        self.latest_version = snapshot.version
    
    def get_latest_snapshot(self) -> Optional[ContextSnapshot]:
        if self.versions:
            return self.versions[-1]
        return None
    
    def get_snapshot_by_version(self, version: int) -> Optional[ContextSnapshot]:
        for snap in self.versions:
            if snap.version == version:
                return snap
        return None


class ContextStore:
    """集中化上下文存储 - 支持持久化、版本控制、跨会话摘要"""
    
    def __init__(self, storage_dir: str = "./memory/contexts"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.manifests: Dict[str, ContextManifest] = {}
        self._load_all_manifests()
    
    def _load_all_manifests(self) -> None:
        """从磁盘加载所有 manifests"""
        manifest_dir = self.storage_dir / "manifests"
        if manifest_dir.exists():
            for manifest_file in manifest_dir.glob("*.json"):
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        session_id = data['session_id']
                        manifest = ContextManifest(
                            session_id=session_id,
                            versions=[ContextSnapshot.from_dict(v) for v in data.get('versions', [])],
                            latest_version=data.get('latest_version', 0),
                            created_at=data.get('created_at', datetime.now().isoformat())
                        )
                        self.manifests[session_id] = manifest
                except Exception as e:
                    self.logger.warning(f"Failed to load manifest {manifest_file}: {e}")
    
    def _save_manifest(self, session_id: str) -> None:
        """保存单个 manifest 到磁盘"""
        manifest_dir = self.storage_dir / "manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        
        manifest = self.manifests.get(session_id)
        if not manifest:
            return
        
        manifest_file = manifest_dir / f"{session_id}.json"
        try:
            data = {
                'session_id': manifest.session_id,
                'versions': [v.to_dict() for v in manifest.versions],
                'latest_version': manifest.latest_version,
                'created_at': manifest.created_at
            }
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Manifest saved: {manifest_file}")
        except Exception as e:
            self.logger.error(f"Failed to save manifest {manifest_file}: {e}")
    
    def save_context(self, session_id: str, context: dict, version: int) -> None:
        """保存上下文快照"""
        if session_id not in self.manifests:
            self.manifests[session_id] = ContextManifest(session_id=session_id)
        
        snapshot = ContextSnapshot(
            session_id=session_id,
            version=version,
            summary=context.get('summary', ''),
            tokens=context.get('tokens', 0),
            created_at=datetime.now().isoformat(),
            source=context.get('source', 'user'),
            metadata=context.get('metadata', {})
        )
        
        self.manifests[session_id].add_snapshot(snapshot)
        self._save_manifest(session_id)
        self.logger.info(f"Context saved: session={session_id}, version={version}")
    
    def load_latest_context(self, session_id: str) -> Optional[dict]:
        """加载最新的上下文"""
        manifest = self.manifests.get(session_id)
        if not manifest:
            self.logger.warning(f"No manifest found for session {session_id}")
            return None
        
        snapshot = manifest.get_latest_snapshot()
        if not snapshot:
            return None
        
        return {
            'session_id': snapshot.session_id,
            'version': snapshot.version,
            'summary': snapshot.summary,
            'tokens': snapshot.tokens,
            'created_at': snapshot.created_at,
            'source': snapshot.source,
            'metadata': snapshot.metadata
        }
    
    def load_context_by_version(self, session_id: str, version: int) -> Optional[dict]:
        """按版本号加载上下文"""
        manifest = self.manifests.get(session_id)
        if not manifest:
            return None
        
        snapshot = manifest.get_snapshot_by_version(version)
        if not snapshot:
            return None
        
        return {
            'session_id': snapshot.session_id,
            'version': snapshot.version,
            'summary': snapshot.summary,
            'tokens': snapshot.tokens,
            'created_at': snapshot.created_at,
            'source': snapshot.source,
            'metadata': snapshot.metadata
        }
    
    def inject_context_into_prompt(self, prompt_template: str, session_id: str) -> str:
        """将上下文注入到 prompt 模板中"""
        context = self.load_latest_context(session_id)
        if not context:
            self.logger.warning(f"No context found for session {session_id}, returning original template")
            return prompt_template
        
        # 替换模板中的占位符
        injected_prompt = prompt_template
        injected_prompt = injected_prompt.replace("{context_summary}", context.get('summary', ''))
        injected_prompt = injected_prompt.replace("{context_tokens}", str(context.get('tokens', 0)))
        injected_prompt = injected_prompt.replace("{context_source}", context.get('source', ''))
        
        self.logger.debug(f"Context injected into prompt for session {session_id}")
        return injected_prompt
    
    def prune_old_contexts(self, session_id: str, keep_count: int = 5) -> None:
        """删除旧的上下文快照，只保留最近的 keep_count 个"""
        manifest = self.manifests.get(session_id)
        if not manifest:
            return
        
        if len(manifest.versions) > keep_count:
            manifest.versions = manifest.versions[-keep_count:]
            self._save_manifest(session_id)
            self.logger.info(f"Pruned old contexts for session {session_id}, kept {keep_count}")
    
    def get_context_history(self, session_id: str, limit: int = 10) -> List[dict]:
        """获取上下文历史"""
        manifest = self.manifests.get(session_id)
        if not manifest:
            return []
        
        history = []
        for snapshot in manifest.versions[-limit:]:
            history.append({
                'version': snapshot.version,
                'summary': snapshot.summary,
                'tokens': snapshot.tokens,
                'created_at': snapshot.created_at,
                'source': snapshot.source
            })
        return history
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return list(self.manifests.keys())
    
    def delete_session(self, session_id: str) -> None:
        """删除整个会话的上下文"""
        if session_id in self.manifests:
            del self.manifests[session_id]
            manifest_file = self.storage_dir / "manifests" / f"{session_id}.json"
            if manifest_file.exists():
                manifest_file.unlink()
            self.logger.info(f"Session deleted: {session_id}")
