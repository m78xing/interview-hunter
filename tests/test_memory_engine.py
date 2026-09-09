"""
MemoryEngine 单元测试
"""
import tempfile
import shutil
from pathlib import Path
from src.core.memory_engine import MemoryEngine, MemoryEntry, MemoryProfile, MemoryDimension


class TestMemoryEntry:
    def test_entry_creation(self):
        entry = MemoryEntry(
            id="entry_1",
            session_id="session_1",
            card_id="card_1",
            dimension="recency",
            value=0.8,
            timestamp="2024-01-01T00:00:00"
        )
        assert entry.id == "entry_1"
        assert entry.value == 0.8
    
    def test_entry_to_dict(self):
        entry = MemoryEntry(
            id="entry_1",
            session_id="session_1",
            card_id="card_1",
            dimension="recency",
            value=0.8,
            timestamp="2024-01-01T00:00:00"
        )
        data = entry.to_dict()
        assert data['id'] == "entry_1"
        assert data['value'] == 0.8


class TestMemoryProfile:
    def test_profile_creation(self):
        profile = MemoryProfile(session_id="session_1")
        assert profile.session_id == "session_1"
        assert len(profile.weights) > 0
        assert profile.decay_rate == 0.95
    
    def test_profile_weights(self):
        profile = MemoryProfile(session_id="session_1")
        assert profile.weights[MemoryDimension.RECENCY.value] == 0.25
        assert profile.weights[MemoryDimension.FREQUENCY.value] == 0.20


class TestMemoryEngine:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.engine = MemoryEngine(storage_dir=self.temp_dir)
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir)
    
    def test_engine_creation(self):
        assert self.engine.storage_dir.exists()
    
    def test_update_memory(self):
        self.engine.update_memory(
            session_id="session_1",
            card_id="card_1",
            dimension="recency",
            value=0.9,
            source="user"
        )
        
        entries = self.engine.get_memory("session_1", "card_1")
        assert len(entries) == 1
        assert entries[0].value == 0.9
    
    def test_get_memory_by_dimension(self):
        self.engine.update_memory("session_1", "card_1", "recency", 0.9)
        self.engine.update_memory("session_1", "card_2", "recency", 0.8)
        self.engine.update_memory("session_1", "card_3", "frequency", 0.7)
        
        recency_entries = self.engine.get_memory_by_dimension("session_1", "recency")
        assert len(recency_entries) == 2
    
    def test_summarize_memory(self):
        self.engine.update_memory("session_1", "card_1", "recency", 0.9)
        self.engine.update_memory("session_1", "card_2", "frequency", 0.8)
        
        summary = self.engine.summarize_memory("session_1")
        assert summary['session_id'] == "session_1"
        assert summary['total_entries'] == 2
        assert 'recency' in summary['dimensions']
    
    def test_export_import_memory(self):
        self.engine.update_memory("session_1", "card_1", "recency", 0.9)
        self.engine.update_memory("session_1", "card_2", "frequency", 0.8)
        
        exported = self.engine.export_memory("session_1")
        assert len(exported['entries']) == 2
        
        engine2 = MemoryEngine(storage_dir=self.temp_dir)
        engine2.import_memory("session_2", exported)
        
        entries = engine2.get_memory("session_2")
        assert len(entries) == 2
    
    def test_consolidate_memory(self):
        for i in range(150):
            self.engine.update_memory("session_1", f"card_{i}", "recency", 0.5)
        
        assert len(self.engine.get_memory("session_1")) == 150
        
        self.engine.consolidate_memory("session_1", keep_latest_n=100)
        assert len(self.engine.get_memory("session_1")) == 100
    
    def test_memory_weights(self):
        weights = self.engine.get_memory_weights("session_1")
        assert weights[MemoryDimension.RECENCY.value] == 0.25
        
        new_weights = {MemoryDimension.RECENCY.value: 0.35}
        self.engine.set_memory_weights("session_1", new_weights)
        
        updated_weights = self.engine.get_memory_weights("session_1")
        assert updated_weights[MemoryDimension.RECENCY.value] == 0.35
    
    def test_list_sessions(self):
        self.engine.update_memory("session_1", "card_1", "recency", 0.9)
        self.engine.update_memory("session_2", "card_1", "recency", 0.8)
        
        sessions = self.engine.list_sessions()
        assert "session_1" in sessions
        assert "session_2" in sessions
    
    def test_delete_session(self):
        self.engine.update_memory("session_1", "card_1", "recency", 0.9)
        assert "session_1" in self.engine.list_sessions()
        
        self.engine.delete_session("session_1")
        assert "session_1" not in self.engine.list_sessions()
    
    def test_persistence(self):
        self.engine.update_memory("session_1", "card_1", "recency", 0.9)
        
        engine2 = MemoryEngine(storage_dir=self.temp_dir)
        entries = engine2.get_memory("session_1")
        assert len(entries) == 1
        assert entries[0].value == 0.9
