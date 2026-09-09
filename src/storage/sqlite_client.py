"""
SQLite 存储客户端
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Card:
    id: str
    question: str
    answer: str
    company: str
    position: str
    tags: List[str]
    difficulty: str
    source_url: str
    source_platform: str
    created_at: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Card':
        return cls(**data)


@dataclass
class ReviewLog:
    id: int
    card_id: str
    reviewed_at: str
    quality: int
    time_taken: int
    
    def to_dict(self) -> dict:
        return asdict(self)


class SQLiteClient:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                company TEXT DEFAULT '',
                position TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                difficulty TEXT DEFAULT 'medium',
                source_url TEXT DEFAULT '',
                source_platform TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                quality INTEGER NOT NULL,
                time_taken INTEGER DEFAULT 0,
                FOREIGN KEY (card_id) REFERENCES cards(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_stats (
                card_id TEXT PRIMARY KEY,
                total_reviews INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                last_reviewed_at TEXT,
                ease_factor REAL DEFAULT 2.5,
                interval_days INTEGER DEFAULT 0,
                consecutive_correct INTEGER DEFAULT 0,
                due TEXT,
                FOREIGN KEY (card_id) REFERENCES cards(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tag_stats (
                tag TEXT PRIMARY KEY,
                total_reviews INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                mastery_level REAL DEFAULT 0.0
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_review_logs_card_id ON review_logs(card_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_review_logs_reviewed_at ON review_logs(reviewed_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def _connect(self):
        return sqlite3.connect(self.db_path)
    
    def insert_card(self, card: Card) -> bool:
        """插入卡片"""
        conn = self._connect()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO cards (id, question, answer, company, position, tags, 
                                   difficulty, source_url, source_platform, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                card.id, card.question, card.answer, card.company, card.position,
                json.dumps(card.tags, ensure_ascii=False), card.difficulty,
                card.source_url, card.source_platform, card.created_at
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """获取卡片"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Card(
                id=row[0], question=row[1], answer=row[2], company=row[3],
                position=row[4], tags=json.loads(row[5]), difficulty=row[6],
                source_url=row[7], source_platform=row[8], created_at=row[9]
            )
        return None
    
    def get_all_cards(self) -> List[Card]:
        """获取所有卡片"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cards ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        cards = []
        for row in rows:
            cards.append(Card(
                id=row[0], question=row[1], answer=row[2], company=row[3],
                position=row[4], tags=json.loads(row[5]), difficulty=row[6],
                source_url=row[7], source_platform=row[8], created_at=row[9]
            ))
        return cards
    
    def get_cards_by_company(self, company: str) -> List[Card]:
        """按公司获取卡片"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cards WHERE company = ?', (company,))
        rows = cursor.fetchall()
        conn.close()
        
        cards = []
        for row in rows:
            cards.append(Card(
                id=row[0], question=row[1], answer=row[2], company=row[3],
                position=row[4], tags=json.loads(row[5]), difficulty=row[6],
                source_url=row[7], source_platform=row[8], created_at=row[9]
            ))
        return cards
    
    def get_cards_by_tags(self, tags: List[str]) -> List[Card]:
        """按标签获取卡片"""
        conn = self._connect()
        cursor = conn.cursor()
        cards = []
        
        for tag in tags:
            cursor.execute('''
                SELECT * FROM cards WHERE tags LIKE ?
            ''', (f'%{tag}%',))
            rows = cursor.fetchall()
            for row in rows:
                cards.append(Card(
                    id=row[0], question=row[1], answer=row[2], company=row[3],
                    position=row[4], tags=json.loads(row[5]), difficulty=row[6],
                    source_url=row[7], source_platform=row[8], created_at=row[9]
                ))
        
        conn.close()
        return cards
    
    def add_review_log(self, card_id: str, quality: int, time_taken: int = 0) -> Optional[int]:
        """添加复习记录"""
        conn = self._connect()
        cursor = conn.cursor()
        reviewed_at = datetime.now().isoformat()
        is_correct = quality >= 3
        
        try:
            cursor.execute('''
                INSERT INTO review_logs (card_id, reviewed_at, quality, time_taken)
                VALUES (?, ?, ?, ?)
            ''', (card_id, reviewed_at, quality, time_taken))
            
            log_id = cursor.lastrowid
            
            # 获取当前卡片统计（单次查询）
            cursor.execute('SELECT total_reviews, correct_count, error_count FROM card_stats WHERE card_id = ?', (card_id,))
            row = cursor.fetchone()
            
            if row:
                total, correct, errors = row
                new_total = total + 1
                new_correct = correct + (1 if is_correct else 0)
                new_errors = errors + (0 if is_correct else 1)
                cursor.execute('''
                    UPDATE card_stats 
                    SET total_reviews = ?, correct_count = ?, error_count = ?, last_reviewed_at = ?
                    WHERE card_id = ?
                ''', (new_total, new_correct, new_errors, reviewed_at, card_id))
            else:
                cursor.execute('''
                    INSERT INTO card_stats (card_id, total_reviews, correct_count, error_count, last_reviewed_at)
                    VALUES (?, 1, ?, ?, ?)
                ''', (card_id, 1 if is_correct else 0, 0 if is_correct else 1, reviewed_at))
            
            # 更新标签统计（使用批量操作）
            card = self.get_card(card_id)
            if card and card.tags:
                # 批量获取现有标签统计
                placeholders = ','.join(['?' for _ in card.tags])
                cursor.execute(f'SELECT tag, total_reviews, correct_count, error_count FROM tag_stats WHERE tag IN ({placeholders})', card.tags)
                existing_stats = {row[0]: row[1:] for row in cursor.fetchall()}
                
                for tag in card.tags:
                    if tag in existing_stats:
                        total, correct, errors = existing_stats[tag]
                        new_total = total + 1
                        new_correct = correct + (1 if is_correct else 0)
                        new_errors = errors + (0 if is_correct else 1)
                        mastery = new_correct / new_total if new_total > 0 else 0
                        cursor.execute('''
                            UPDATE tag_stats 
                            SET total_reviews = ?, correct_count = ?, error_count = ?, mastery_level = ?
                            WHERE tag = ?
                        ''', (new_total, new_correct, new_errors, mastery, tag))
                    else:
                        cursor.execute('''
                            INSERT INTO tag_stats (tag, total_reviews, correct_count, error_count, mastery_level)
                            VALUES (?, 1, ?, ?, ?)
                        ''', (tag, 1 if is_correct else 0, 0 if is_correct else 1, 1.0 if is_correct else 0.0))
            
            conn.commit()
            return log_id
        finally:
            conn.close()
    
    def get_review_logs(self, card_id: str, limit: int = 10) -> List[ReviewLog]:
        """获取卡片的复习记录"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, card_id, reviewed_at, quality, time_taken 
            FROM review_logs 
            WHERE card_id = ? 
            ORDER BY reviewed_at DESC 
            LIMIT ?
        ''', (card_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [ReviewLog(id=r[0], card_id=r[1], reviewed_at=r[2], quality=r[3], time_taken=r[4]) for r in rows]
    
    def get_recent_review_logs(self, days: int = 1) -> List[ReviewLog]:
        """获取最近N天的复习记录"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, card_id, reviewed_at, quality, time_taken 
            FROM review_logs 
            WHERE reviewed_at >= datetime('now', ?)
            ORDER BY reviewed_at DESC
        ''', (f'-{days} days',))
        rows = cursor.fetchall()
        conn.close()
        
        return [ReviewLog(id=r[0], card_id=r[1], reviewed_at=r[2], quality=r[3], time_taken=r[4]) for r in rows]
    
    def get_tag_stats(self) -> Dict[str, dict]:
        """获取标签统计"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tag_stats')
        rows = cursor.fetchall()
        conn.close()
        
        stats = {}
        for row in rows:
            stats[row[0]] = {
                'tag': row[0],
                'total_reviews': row[1],
                'correct_count': row[2],
                'error_count': row[3],
                'mastery_level': row[4]
            }
        return stats
    
    def get_card_stats(self, card_id: str) -> Optional[dict]:
        """获取卡片统计"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM card_stats WHERE card_id = ?', (card_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'card_id': row[0],
                'total_reviews': row[1],
                'correct_count': row[2],
                'error_count': row[3],
                'last_reviewed_at': row[4],
                'ease_factor': row[5],
                'interval_days': row[6],
                'consecutive_correct': row[7] if len(row) > 7 else 0,
                'due': row[8] if len(row) > 8 else None
            }
        return None
    
    def get_consecutive_errors(self, tag: str, limit: int = 5) -> int:
        """获取某标签最近连续错误次数"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.quality, c.tags
            FROM review_logs r
            JOIN cards c ON r.card_id = c.id
            WHERE c.tags LIKE ?
            ORDER BY r.reviewed_at DESC
            LIMIT ?
        ''', (f'%{tag}%', limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        consecutive = 0
        for quality, _ in rows:
            if quality < 3:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def get_tag_error_rate(self, tag: str) -> float:
        """获取某标签的错误率"""
        stats = self.get_tag_stats()
        if tag in stats:
            s = stats[tag]
            if s['total_reviews'] > 0:
                return s['error_count'] / s['total_reviews']
        return 0.0
    
    def get_due_cards(self, limit: int = 20) -> List[str]:
        """获取待复习的卡片ID"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, COALESCE(cs.last_reviewed_at, c.created_at) as last_review,
                   COALESCE(cs.interval_days, 0) as interval_days
            FROM cards c
            LEFT JOIN card_stats cs ON c.id = cs.card_id
            ORDER BY last_review ASC, interval_days ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def get_total_cards(self) -> int:
        """获取卡片总数"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cards')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_today_review_count(self) -> int:
        """获取今日复习数量"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM review_logs 
            WHERE DATE(reviewed_at) = DATE('now')
        ''')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def update_ease_factor(self, card_id: str, quality: int):
        """更新 ease factor (SM-2 算法)"""
        conn = self._connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ease_factor, interval_days FROM card_stats WHERE card_id = ?
        ''', (card_id,))
        row = cursor.fetchone()
        
        if row:
            ef, interval = row
            ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            if ef < 1.3:
                ef = 1.3
            
            if quality < 3:
                new_interval = 1
            else:
                new_interval = max(1, int(interval * ef))
            
            cursor.execute('''
                UPDATE card_stats SET ease_factor = ?, interval_days = ? WHERE card_id = ?
            ''', (ef, new_interval, card_id))
            conn.commit()
        
        conn.close()

    def get_companies(self) -> List[str]:
        """获取所有公司列表"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT company FROM cards WHERE company != "" ORDER BY company')
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_positions(self) -> List[str]:
        """获取所有岗位列表"""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT position FROM cards WHERE position != "" ORDER BY position')
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    
    def get_sm2_card(self, card_id: str) -> Optional['SM2Card']:
        """获取 SM-2 格式的卡片 (需要 from sm_2 import Card as SM2Card)"""
        from sm_2 import Card as SM2Card
        from datetime import datetime, timezone
        
        card = self.get_card(card_id)
        if not card:
            return None
        
        stats = self.get_card_stats(card_id)
        
        # 构建 SM-2 Card
        due = None
        if stats and stats.get('due'):
            due = datetime.fromisoformat(stats['due'])
        else:
            due = datetime.now(timezone.utc)
        
        return SM2Card(
            card_id=int(card_id) if card_id.isdigit() else hash(card_id) % 1000000000000,
            n=stats.get('consecutive_correct', 0) if stats else 0,
            EF=stats.get('ease_factor', 2.5) if stats else 2.5,
            I=stats.get('interval_days', 0) if stats else 0,
            due=due,
            needs_extra_review=False
        )
    
    def update_card_from_sm2(self, card_id: str, sm2_card: 'SM2Card'):
        """从 SM-2 Card 更新数据库"""
        from datetime import datetime, timezone
        
        conn = self._connect()
        cursor = conn.cursor()
        
        # 如果没有 stats 记录，先插入
        cursor.execute('SELECT card_id FROM card_stats WHERE card_id = ?', (card_id,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO card_stats (card_id, ease_factor, interval_days, consecutive_correct, due)
                VALUES (?, ?, ?, ?, ?)
            ''', (card_id, 2.5, 0, 0, datetime.now(timezone.utc).isoformat()))
        
        # 更新所有 SM-2 字段
        cursor.execute('''
            UPDATE card_stats 
            SET ease_factor = ?, interval_days = ?, consecutive_correct = ?, due = ?
            WHERE card_id = ?
        ''', (
            sm2_card.EF,
            sm2_card.I,
            sm2_card.n,
            sm2_card.due.isoformat() if sm2_card.due else datetime.now(timezone.utc).isoformat(),
            card_id
        ))
        conn.commit()
        conn.close()
