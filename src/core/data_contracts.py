"""
Data Contracts - 数据契约与验证规则
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class DataContract:
    """数据契约基类"""
    name: str
    version: int
    fields: Dict[str, Dict[str, Any]]
    
    def validate(self, data: dict) -> tuple[bool, List[str]]:
        """验证数据是否符合契约"""
        errors = []
        
        for field_name, field_spec in self.fields.items():
            if field_spec.get('required', False) and field_name not in data:
                errors.append(f"Required field '{field_name}' is missing")
            
            if field_name in data:
                value = data[field_name]
                expected_type = field_spec.get('type')
                
                if expected_type and not isinstance(value, expected_type):
                    errors.append(f"Field '{field_name}' has wrong type: expected {expected_type}, got {type(value)}")
                
                if 'min_value' in field_spec and value < field_spec['min_value']:
                    errors.append(f"Field '{field_name}' is below minimum: {field_spec['min_value']}")
                
                if 'max_value' in field_spec and value > field_spec['max_value']:
                    errors.append(f"Field '{field_name}' exceeds maximum: {field_spec['max_value']}")
                
                if 'enum' in field_spec and value not in field_spec['enum']:
                    errors.append(f"Field '{field_name}' has invalid value: {value}")
        
        return len(errors) == 0, errors


class ContextSnapshotContract(DataContract):
    """ContextSnapshot 数据契约"""
    def __init__(self):
        super().__init__(
            name="ContextSnapshot",
            version=1,
            fields={
                'session_id': {'type': str, 'required': True},
                'version': {'type': int, 'required': True, 'min_value': 0},
                'summary': {'type': str, 'required': True},
                'tokens': {'type': int, 'required': True, 'min_value': 0},
                'created_at': {'type': str, 'required': True},
                'source': {'type': str, 'required': True},
                'metadata': {'type': dict, 'required': False}
            }
        )


class MemoryEntryContract(DataContract):
    """MemoryEntry 数据契约"""
    def __init__(self):
        super().__init__(
            name="MemoryEntry",
            version=1,
            fields={
                'id': {'type': str, 'required': True},
                'session_id': {'type': str, 'required': True},
                'card_id': {'type': str, 'required': True},
                'dimension': {'type': str, 'required': True},
                'value': {'required': True},
                'timestamp': {'type': str, 'required': True},
                'decay': {'type': float, 'required': False, 'min_value': 0.0, 'max_value': 1.0},
                'source': {'type': str, 'required': False},
                'confidence': {'type': float, 'required': False, 'min_value': 0.0, 'max_value': 1.0}
            }
        )


class RetrievalResultContract(DataContract):
    """RetrievalResult 数据契约"""
    def __init__(self):
        super().__init__(
            name="RetrievalResult",
            version=1,
            fields={
                'card_id': {'type': str, 'required': True},
                'score': {'type': float, 'required': True, 'min_value': 0.0, 'max_value': 1.0},
                'source': {'type': str, 'required': True},
                'metadata': {'type': dict, 'required': False},
                'rationale': {'type': str, 'required': False},
                'path_contributions': {'type': dict, 'required': False}
            }
        )


class ExperimentLogContract(DataContract):
    """ExperimentLog 数据契约"""
    def __init__(self):
        super().__init__(
            name="ExperimentLog",
            version=1,
            fields={
                'run_id': {'type': str, 'required': True},
                'parameters': {'type': dict, 'required': True},
                'metrics': {'type': dict, 'required': True},
                'seed': {'type': int, 'required': True},
                'data_version': {'type': str, 'required': True},
                'timestamp': {'type': str, 'required': True}
            }
        )


class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.contracts = {
            'ContextSnapshot': ContextSnapshotContract(),
            'MemoryEntry': MemoryEntryContract(),
            'RetrievalResult': RetrievalResultContract(),
            'ExperimentLog': ExperimentLogContract()
        }
    
    def validate(self, contract_name: str, data: dict) -> tuple[bool, List[str]]:
        """验证数据"""
        if contract_name not in self.contracts:
            return False, [f"Unknown contract: {contract_name}"]
        
        contract = self.contracts[contract_name]
        is_valid, errors = contract.validate(data)
        
        if not is_valid:
            self.logger.warning(f"Validation failed for {contract_name}: {errors}")
        
        return is_valid, errors
    
    def register_contract(self, name: str, contract: DataContract) -> None:
        """注册自定义契约"""
        self.contracts[name] = contract
        self.logger.info(f"Contract registered: {name}")


class SchemaMigration:
    """模式迁移管理"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.migrations: Dict[str, List[Dict[str, Any]]] = {}
    
    def register_migration(self, contract_name: str, from_version: int, to_version: int, 
                          migration_func) -> None:
        """注册迁移函数"""
        key = f"{contract_name}_{from_version}_to_{to_version}"
        if contract_name not in self.migrations:
            self.migrations[contract_name] = []
        
        self.migrations[contract_name].append({
            'from_version': from_version,
            'to_version': to_version,
            'func': migration_func
        })
        self.logger.info(f"Migration registered: {key}")
    
    def migrate(self, contract_name: str, data: dict, from_version: int, to_version: int) -> dict:
        """执行迁移"""
        if contract_name not in self.migrations:
            self.logger.warning(f"No migrations found for {contract_name}")
            return data
        
        current_version = from_version
        current_data = data
        
        while current_version < to_version:
            migration_found = False
            for migration in self.migrations[contract_name]:
                if migration['from_version'] == current_version and migration['to_version'] == current_version + 1:
                    current_data = migration['func'](current_data)
                    current_version += 1
                    migration_found = True
                    break
            
            if not migration_found:
                self.logger.error(f"No migration path from version {current_version} to {to_version}")
                break
        
        return current_data
