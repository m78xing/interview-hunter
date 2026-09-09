"""
ContextStore 单元测试
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from src.core.context_store import ContextStore, ContextSnapshot, ContextManifest


class TestContextSnapshot:
    def test_snapshot_creation(self):
        snapshot = ContextSnapshot(
            session_id="session_1",
            version=1,
            summary="Test summary",
            tokens=100,
            created_at="2024-01-01T00:00:00",
            source="test"
        )
        assert snapshot.session_id == "session_1"
        assert snapshot.version == 1
        assert snapshot.summary == "Test summary"
    
    def test_snapshot_to_dict(self):
        snapshot = ContextSnapshot(
            session_id="session_1",
            version=1,
            summary="Test",
            tokens=50,
            created_at="2024-01-01T00:00:00",
            source="test"
        )
        data = snapshot.to_dict()
        assert data['session_id'] == "session_1"
        assert data['version'] == 1
    
    def test_snapshot_from_dict(self):
        data = {
            'session_id': 'session_1',
            'version': 1,
            'summary': 'Test',
            'tokens': 50,
            'created_at': '2024-01-01T00:00:00',
            'source': 'test',
            'metadata': {}
        }
        snapshot = ContextSnapshot.from_dict(data)
        assert snapshot.session_id == 'session_1'
        assert snapshot.version == 1


class TestContextManifest:
    def test_manifest_creation(self):
        manifest = ContextManifest(session_id="session_1")
        assert manifest.session_id == "session_1"
        assert len(manifest.versions) == 0
        assert manifest.latest_version == 0
    
    def test_add_snapshot(self):
        manifest = ContextManifest(session_id="session_1")
        snapshot = ContextSnapshot(
            session_id="session_1",
            version=1,
            summary="Test",
            tokens=50,
            created_at="2024-01-01T00:00:00",
            source="test"
        )
        manifest.add_snapshot(snapshot)
        assert len(manifest.versions) == 1
        assert manifest.latest_version == 1
    
    def test_get_latest_snapshot(self):
        manifest = ContextManifest(session_id="session_1")
        snapshot1 = ContextSnapshot(
            session_id="session_1", version=1, summary="v1", tokens=50,
            created_at="2024-01-01T00:00:00", source="test"
        )
        snapshot2 = ContextSnapshot(
            session_id="session_1", version=2, summary="v2", tokens=100,
            created_at="2024-01-02T00:00:00", source="test"
        )
        manifest.add_snapshot(snapshot1)
        manifest.add_snapshot(snapshot2)
        
        latest = manifest.get_latest_snapshot()
        assert latest.version == 2
        assert latest.summary == "v2"


class TestContextStore:
    @pytest.fixture
    def temp_storage(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_context_store_creation(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        assert store.storage_dir.exists()
    
    def test_save_and_load_context(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        context = {
            'summary': 'Test context',
            'tokens': 100,
            'source': 'test',
            'metadata': {'key': 'value'}
        }
        
        store.save_context('session_1', context, version=1)
        loaded = store.load_latest_context('session_1')
        
        assert loaded is not None
        assert loaded['summary'] == 'Test context'
        assert loaded['tokens'] == 100
        assert loaded['version'] == 1
    
    def test_load_context_by_version(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        context1 = {'summary': 'v1', 'tokens': 50, 'source': 'test'}
        context2 = {'summary': 'v2', 'tokens': 100, 'source': 'test'}
        
        store.save_context('session_1', context1, version=1)
        store.save_context('session_1', context2, version=2)
        
        loaded_v1 = store.load_context_by_version('session_1', 1)
        loaded_v2 = store.load_context_by_version('session_1', 2)
        
        assert loaded_v1['summary'] == 'v1'
        assert loaded_v2['summary'] == 'v2'
    
    def test_inject_context_into_prompt(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        context = {
            'summary': 'Important context',
            'tokens': 150,
            'source': 'user'
        }
        store.save_context('session_1', context, version=1)
        
        template = "Context: {context_summary}, Tokens: {context_tokens}"
        injected = store.inject_context_into_prompt(template, 'session_1')
        
        assert 'Important context' in injected
        assert '150' in injected
    
    def test_prune_old_contexts(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        for i in range(10):
            context = {'summary': f'v{i}', 'tokens': i*10, 'source': 'test'}
            store.save_context('session_1', context, version=i+1)
        
        assert len(store.manifests['session_1'].versions) == 10
        
        store.prune_old_contexts('session_1', keep_count=5)
        assert len(store.manifests['session_1'].versions) == 5
    
    def test_get_context_history(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        for i in range(3):
            context = {'summary': f'v{i}', 'tokens': i*10, 'source': 'test'}
            store.save_context('session_1', context, version=i+1)
        
        history = store.get_context_history('session_1')
        assert len(history) == 3
        assert history[0]['version'] == 1
        assert history[-1]['version'] == 3
    
    def test_list_sessions(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        context = {'summary': 'test', 'tokens': 50, 'source': 'test'}
        store.save_context('session_1', context, version=1)
        store.save_context('session_2', context, version=1)
        
        sessions = store.list_sessions()
        assert 'session_1' in sessions
        assert 'session_2' in sessions
    
    def test_delete_session(self, temp_storage):
        store = ContextStore(storage_dir=temp_storage)
        
        context = {'summary': 'test', 'tokens': 50, 'source': 'test'}
        store.save_context('session_1', context, version=1)
        
        assert 'session_1' in store.list_sessions()
        store.delete_session('session_1')
        assert 'session_1' not in store.list_sessions()
    
    def test_persistence_across_instances(self, temp_storage):
        store1 = ContextStore(storage_dir=temp_storage)
        context = {'summary': 'persistent', 'tokens': 100, 'source': 'test'}
        store1.save_context('session_1', context, version=1)
        
        store2 = ContextStore(storage_dir=temp_storage)
        loaded = store2.load_latest_context('session_1')
        
        assert loaded is not None
        assert loaded['summary'] == 'persistent'
