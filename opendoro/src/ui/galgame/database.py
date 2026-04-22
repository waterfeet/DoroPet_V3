import os
import sqlite3
import json
from typing import List, Optional, Dict
from src.core.database import BaseDatabase, get_user_data_dir, ensure_data_dir
from src.core.logger import logger
from .models import (
    GameState, GameConfig, GameItem, StoryMessage, AffectionState,
    Protagonist, Character, WorldSetting, GameChoice, MessageRole,
    get_relationship_name, StoryCache
)


DATA_DIR = os.path.join(get_user_data_dir(), "data")


class GalgameDatabase(BaseDatabase):
    def __init__(self):
        ensure_data_dir()
        self.db_path = os.path.join(DATA_DIR, "galgame.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.migrate()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS galgame_saves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS galgame_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protagonist TEXT,
            characters TEXT,
            world_setting TEXT,
            model_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS galgame_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER,
            config_id INTEGER,
            chapter INTEGER DEFAULT 1,
            scene TEXT,
            currency INTEGER DEFAULT 0,
            inventory TEXT,
            story_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(save_id) REFERENCES galgame_saves(id),
            FOREIGN KEY(config_id) REFERENCES galgame_configs(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS galgame_affections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            character_name TEXT NOT NULL,
            affection INTEGER DEFAULT 50,
            relationship TEXT,
            FOREIGN KEY(state_id) REFERENCES galgame_states(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS galgame_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            role TEXT NOT NULL,
            character_name TEXT,
            content TEXT NOT NULL,
            choices TEXT,
            selected_choice INTEGER,
            affection_changes TEXT,
            currency_change INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(state_id) REFERENCES galgame_states(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS galgame_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            effect TEXT,
            category TEXT,
            icon TEXT
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS character_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            character_name TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 5,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            context TEXT,
            is_remembered BOOLEAN DEFAULT 1,
            FOREIGN KEY(state_id) REFERENCES galgame_states(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS triggered_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            event_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            trigger_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            chapter_number INTEGER,
            FOREIGN KEY(state_id) REFERENCES galgame_states(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS character_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            character_a TEXT NOT NULL,
            character_b TEXT NOT NULL,
            affection INTEGER DEFAULT 0,
            relationship_type TEXT DEFAULT 'stranger',
            history TEXT,
            FOREIGN KEY(state_id) REFERENCES galgame_states(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS game_endings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            save_id INTEGER,
            ending_type TEXT NOT NULL,
            character_name TEXT,
            ending_title TEXT NOT NULL,
            ending_description TEXT,
            ending_story TEXT,
            final_affection INTEGER DEFAULT 0,
            total_chapters INTEGER DEFAULT 1,
            play_time TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(save_id) REFERENCES galgame_saves(id)
        )''')
        
        self.conn.commit()
    
    def migrate(self):
        cursor = self.conn.cursor()
        
        cursor.execute("PRAGMA table_info(galgame_states)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'config_id' not in columns:
            cursor.execute("ALTER TABLE galgame_states ADD COLUMN config_id INTEGER")
        if 'story_cache' not in columns:
            cursor.execute("ALTER TABLE galgame_states ADD COLUMN story_cache TEXT")
        if 'protagonist' not in columns:
            cursor.execute("ALTER TABLE galgame_states ADD COLUMN protagonist TEXT")
        if 'characters' not in columns:
            cursor.execute("ALTER TABLE galgame_states ADD COLUMN characters TEXT")
        if 'world_setting' not in columns:
            cursor.execute("ALTER TABLE galgame_states ADD COLUMN world_setting TEXT")
        
        cursor.execute("PRAGMA table_info(galgame_messages)")
        msg_columns = [info[1] for info in cursor.fetchall()]
        if 'chapter_number' not in msg_columns:
            cursor.execute("ALTER TABLE galgame_messages ADD COLUMN chapter_number INTEGER DEFAULT 1")
        if 'chapter_name' not in msg_columns:
            cursor.execute("ALTER TABLE galgame_messages ADD COLUMN chapter_name TEXT")
        
        self.conn.commit()
        self._init_default_items()
    
    def save_memory(self, state_id: int, memory) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO character_memories (state_id, character_name, memory_type, content, importance, context, is_remembered) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (state_id, memory.character_name, memory.memory_type, memory.content, memory.importance, json.dumps(memory.context), memory.is_remembered)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_memories(self, state_id: int, character_name: str = None) -> List:
        cursor = self.conn.cursor()
        if character_name:
            cursor.execute("SELECT * FROM character_memories WHERE state_id=? AND character_name=? ORDER BY timestamp DESC", (state_id, character_name))
        else:
            cursor.execute("SELECT * FROM character_memories WHERE state_id=? ORDER BY timestamp DESC", (state_id,))
        
        from .models import CharacterMemory
        memories = []
        for row in cursor.fetchall():
            memories.append(CharacterMemory(
                id=row['id'],
                character_name=row['character_name'],
                memory_type=row['memory_type'],
                content=row['content'],
                importance=row['importance'],
                timestamp=row['timestamp'],
                context=json.loads(row['context']) if row['context'] else {},
                is_remembered=bool(row['is_remembered'])
            ))
        return memories
    
    def save_triggered_event(self, state_id: int, event_id: str, event_type: str, chapter_number: int):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO triggered_events (state_id, event_id, event_type, chapter_number) VALUES (?, ?, ?, ?)",
            (state_id, event_id, event_type, chapter_number)
        )
        self.conn.commit()
    
    def get_triggered_events(self, state_id: int, event_id: str = None) -> List[Dict]:
        cursor = self.conn.cursor()
        if event_id:
            cursor.execute("SELECT * FROM triggered_events WHERE state_id=? AND event_id=?", (state_id, event_id))
        else:
            cursor.execute("SELECT * FROM triggered_events WHERE state_id=?", (state_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def save_relationship(self, state_id: int, relationship) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO character_relationships (state_id, character_a, character_b, affection, relationship_type, history) VALUES (?, ?, ?, ?, ?, ?)",
            (state_id, relationship.character_a, relationship.character_b, relationship.affection, relationship.relationship_type, json.dumps(relationship.history))
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_relationships(self, state_id: int) -> List:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM character_relationships WHERE state_id=?", (state_id,))
        
        from .models import CharacterRelationship
        relationships = []
        for row in cursor.fetchall():
            relationships.append(CharacterRelationship(
                character_a=row['character_a'],
                character_b=row['character_b'],
                affection=row['affection'],
                relationship_type=row['relationship_type'],
                history=json.loads(row['history']) if row['history'] else []
            ))
        return relationships
    
    def save_ending(self, ending) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO game_endings (save_id, ending_type, character_name, ending_title, ending_description, ending_story, final_affection, total_chapters, play_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ending.save_id if hasattr(ending, 'save_id') else 0, ending.ending_type, ending.character_name, ending.ending_title, ending.ending_description, ending.ending_story, ending.final_affection, ending.total_chapters, ending.play_time)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_endings(self, save_id: int = None) -> List:
        cursor = self.conn.cursor()
        if save_id:
            cursor.execute("SELECT * FROM game_endings WHERE save_id=? ORDER BY timestamp DESC", (save_id,))
        else:
            cursor.execute("SELECT * FROM game_endings ORDER BY timestamp DESC")
        
        from .models import GameEnding
        endings = []
        for row in cursor.fetchall():
            endings.append(GameEnding(
                id=row['id'],
                ending_type=row['ending_type'],
                character_name=row['character_name'],
                ending_title=row['ending_title'],
                ending_description=row['ending_description'],
                ending_story=row['ending_story'],
                final_affection=row['final_affection'],
                total_chapters=row['total_chapters'],
                play_time=row['play_time'],
                timestamp=row['timestamp']
            ))
        return endings
    
    def get_all_endings(self) -> List:
        return self.get_endings()
    
    def has_achieved_ending(self, character_name: str, ending_type: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM game_endings WHERE character_name=? AND ending_type=?", (character_name, ending_type))
        return cursor.fetchone()[0] > 0
    
    def _init_default_items(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM galgame_items")
        if cursor.fetchone()[0] == 0:
            default_items = [
                ("幸运草", "增加与所有角色的好感度", 50, json.dumps({"type": "affection_all", "value": 5}), "道具", None),
                ("时光沙漏", "回退到上一个选择点", 100, json.dumps({"type": "rollback"}), "道具", None),
                ("神秘信件", "解锁隐藏剧情线索", 200, json.dumps({"type": "unlock_story"}), "道具", None),
                ("礼物盒", "送给特定角色增加好感度", 80, json.dumps({"type": "affection_single", "value": 10}), "礼物", None),
                ("护身符", "防止一次好感度下降", 150, json.dumps({"type": "protect_affection"}), "道具", None),
            ]
            cursor.executemany(
                "INSERT INTO galgame_items (name, description, price, effect, category, icon) VALUES (?, ?, ?, ?, ?, ?)",
                default_items
            )
            self.conn.commit()
    
    def create_save(self, name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO galgame_saves (name) VALUES (?)", (name,))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_saves(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, created_at, updated_at FROM galgame_saves ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_save(self, save_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM galgame_states WHERE save_id=?", (save_id,))
        state_ids = [row[0] for row in cursor.fetchall()]
        
        for state_id in state_ids:
            cursor.execute("DELETE FROM galgame_messages WHERE state_id=?", (state_id,))
            cursor.execute("DELETE FROM galgame_affections WHERE state_id=?", (state_id,))
        
        cursor.execute("DELETE FROM galgame_states WHERE save_id=?", (save_id,))
        cursor.execute("DELETE FROM galgame_saves WHERE id=?", (save_id,))
        self.conn.commit()
    
    def save_config(self, config: GameConfig) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO galgame_configs (name, protagonist, characters, world_setting, model_id) VALUES (?, ?, ?, ?, ?)",
            (
                config.name,
                json.dumps(config.protagonist.to_dict()),
                json.dumps([c.to_dict() for c in config.characters]),
                json.dumps(config.world_setting.to_dict()),
                config.model_id
            )
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_config(self, config: GameConfig):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE galgame_configs SET name=?, protagonist=?, characters=?, world_setting=?, model_id=? WHERE id=?",
            (
                config.name,
                json.dumps(config.protagonist.to_dict()),
                json.dumps([c.to_dict() for c in config.characters]),
                json.dumps(config.world_setting.to_dict()),
                config.model_id,
                config.id
            )
        )
        self.conn.commit()
    
    def get_config(self, config_id: int) -> Optional[GameConfig]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM galgame_configs WHERE id=?", (config_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_config(row)
    
    def get_configs(self) -> List[GameConfig]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM galgame_configs ORDER BY created_at DESC")
        return [self._row_to_config(row) for row in cursor.fetchall()]
    
    def delete_config(self, config_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM galgame_configs WHERE id=?", (config_id,))
        self.conn.commit()
    
    def _row_to_config(self, row) -> GameConfig:
        return GameConfig(
            id=row['id'],
            name=row['name'],
            protagonist=Protagonist.from_dict(json.loads(row['protagonist'])),
            characters=[Character.from_dict(c) for c in json.loads(row['characters'])],
            world_setting=WorldSetting.from_dict(json.loads(row['world_setting'])),
            model_id=row['model_id']
        )
    
    def save_state(self, state: GameState) -> int:
        cursor = self.conn.cursor()
        
        story_cache_json = json.dumps(state.story_cache.to_dict()) if state.story_cache else None
        protagonist_json = json.dumps(state.protagonist.to_dict()) if state.protagonist else None
        characters_json = json.dumps([c.to_dict() for c in state.characters]) if state.characters else None
        world_setting_json = json.dumps(state.world_setting.to_dict()) if state.world_setting else None
        
        cursor.execute("SELECT id FROM galgame_states WHERE save_id=?", (state.save_id,))
        existing = cursor.fetchone()
        
        if existing:
            state_id = existing[0]
            cursor.execute(
                "UPDATE galgame_states SET chapter=?, scene=?, currency=?, inventory=?, story_context=?, story_cache=?, protagonist=?, characters=?, world_setting=? WHERE id=?",
                (
                    state.chapter,
                    state.scene,
                    state.currency,
                    json.dumps(state.inventory),
                    json.dumps(state.story_context),
                    story_cache_json,
                    protagonist_json,
                    characters_json,
                    world_setting_json,
                    state_id
                )
            )
            cursor.execute("DELETE FROM galgame_affections WHERE state_id=?", (state_id,))
            cursor.execute("DELETE FROM galgame_messages WHERE state_id=?", (state_id,))
        else:
            cursor.execute(
                "INSERT INTO galgame_states (save_id, config_id, chapter, scene, currency, inventory, story_context, story_cache, protagonist, characters, world_setting) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    state.save_id,
                    state.config_id,
                    state.chapter,
                    state.scene,
                    state.currency,
                    json.dumps(state.inventory),
                    json.dumps(state.story_context),
                    story_cache_json,
                    protagonist_json,
                    characters_json,
                    world_setting_json
                )
            )
            state_id = cursor.lastrowid
        
        for aff in state.affections:
            cursor.execute(
                "INSERT INTO galgame_affections (state_id, character_name, affection, relationship) VALUES (?, ?, ?, ?)",
                (state_id, aff.character_name, aff.affection, aff.relationship)
            )
        
        for msg in state.messages:
            cursor.execute(
                "INSERT INTO galgame_messages (state_id, role, character_name, content, choices, selected_choice, affection_changes, currency_change, chapter_number, chapter_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    state_id,
                    msg.role.value,
                    msg.character_name,
                    msg.content,
                    json.dumps([c.to_dict() for c in msg.choices]),
                    msg.selected_choice,
                    json.dumps(msg.affection_changes),
                    msg.currency_change,
                    msg.chapter_number,
                    msg.chapter_name
                )
            )
        
        cursor.execute("UPDATE galgame_saves SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (state.save_id,))
        self.conn.commit()
        return state_id
    
    def load_state(self, save_id: int) -> Optional[GameState]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM galgame_states WHERE save_id=?", (save_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        state_id = row['id']
        
        cursor.execute("SELECT * FROM galgame_affections WHERE state_id=?", (state_id,))
        affections = [
            AffectionState(
                character_name=r['character_name'],
                affection=r['affection'],
                relationship=r['relationship']
            ) for r in cursor.fetchall()
        ]
        
        cursor.execute("SELECT * FROM galgame_messages WHERE state_id=? ORDER BY timestamp ASC", (state_id,))
        messages = []
        for r in cursor.fetchall():
            msg = StoryMessage(
                id=r['id'],
                role=MessageRole(r['role']),
                character_name=r['character_name'],
                content=r['content'],
                choices=[GameChoice.from_dict(c) for c in json.loads(r['choices'])] if r['choices'] else [],
                selected_choice=r['selected_choice'],
                affection_changes=json.loads(r['affection_changes']) if r['affection_changes'] else {},
                currency_change=r['currency_change'],
                timestamp=r['timestamp'],
                chapter_number=r['chapter_number'] if 'chapter_number' in r.keys() else 1,
                chapter_name=r['chapter_name'] if 'chapter_name' in r.keys() else ""
            )
            messages.append(msg)
        
        protagonist = None
        if 'protagonist' in row.keys() and row['protagonist']:
            protagonist = Protagonist.from_dict(json.loads(row['protagonist']))
        
        characters = []
        if 'characters' in row.keys() and row['characters']:
            characters = [Character.from_dict(c) for c in json.loads(row['characters'])]
        
        world_setting = None
        if 'world_setting' in row.keys() and row['world_setting']:
            world_setting = WorldSetting.from_dict(json.loads(row['world_setting']))
        
        return GameState(
            save_id=save_id,
            config_id=row['config_id'],
            chapter=row['chapter'],
            scene=row['scene'],
            currency=row['currency'],
            inventory=json.loads(row['inventory']) if row['inventory'] else [],
            affections=affections,
            messages=messages,
            story_context=json.loads(row['story_context']) if row['story_context'] else [],
            story_cache=StoryCache.from_dict(json.loads(row['story_cache'])) if row['story_cache'] else None,
            protagonist=protagonist,
            characters=characters,
            world_setting=world_setting
        )
    
    def add_message(self, state_id: int, message: StoryMessage) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO galgame_messages (state_id, role, character_name, content, choices, selected_choice, affection_changes, currency_change) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                state_id,
                message.role.value,
                message.character_name,
                message.content,
                json.dumps([c.to_dict() for c in message.choices]),
                message.selected_choice,
                json.dumps(message.affection_changes),
                message.currency_change
            )
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_items(self) -> List[GameItem]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM galgame_items ORDER BY price ASC")
        return [
            GameItem(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                price=row['price'],
                effect=json.loads(row['effect']) if row['effect'] else {},
                category=row['category'],
                icon=row['icon']
            ) for row in cursor.fetchall()
        ]
    
    def add_item(self, item: GameItem) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO galgame_items (name, description, price, effect, category, icon) VALUES (?, ?, ?, ?, ?, ?)",
            (item.name, item.description, item.price, json.dumps(item.effect), item.category, item.icon)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def auto_save_state(self, state: GameState) -> int:
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT id FROM galgame_saves WHERE name='auto-save'")
        existing_save = cursor.fetchone()
        
        if existing_save:
            save_id = existing_save[0]
            logger.info(f"Auto-save: Found existing auto-save with id={save_id}")
        else:
            cursor.execute("INSERT INTO galgame_saves (name) VALUES (?)", ("auto-save",))
            self.conn.commit()
            save_id = cursor.lastrowid
            logger.info(f"Auto-save: Created new auto-save with id={save_id}")
        
        state.save_id = save_id
        result = self.save_state(state)
        logger.info(f"Auto-save: State saved successfully with save_id={save_id}, state_id={result}")
        return result
    
    def load_auto_save(self) -> Optional[GameState]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM galgame_saves WHERE name='auto-save'")
        save = cursor.fetchone()
        if not save:
            return None
        return self.load_state(save[0])

    def update_save_time(self, save_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE galgame_saves SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (save_id,))
        self.conn.commit()
    
    def save_current_config(
        self,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting,
        model_id: str
    ) -> int:
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT id FROM galgame_configs WHERE id = 0")
        existing = cursor.fetchone()
        
        config_data = (
            json.dumps(protagonist.to_dict()),
            json.dumps([c.to_dict() for c in characters]),
            json.dumps(world_setting.to_dict()),
            model_id
        )
        
        if existing:
            cursor.execute(
                "UPDATE galgame_configs SET name=?, protagonist=?, characters=?, world_setting=?, model_id=? WHERE id = 0",
                ("当前配置",) + config_data
            )
        else:
            cursor.execute(
                "INSERT INTO galgame_configs (id, name, protagonist, characters, world_setting, model_id) VALUES (0, ?, ?, ?, ?, ?)",
                ("当前配置",) + config_data
            )
        
        self.conn.commit()
        return 0
    
    def load_current_config(self) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM galgame_configs WHERE id = 0")
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'protagonist': Protagonist.from_dict(json.loads(row['protagonist'])) if row['protagonist'] else Protagonist(),
            'characters': [Character.from_dict(c) for c in json.loads(row['characters'])] if row['characters'] else [],
            'world_setting': WorldSetting.from_dict(json.loads(row['world_setting'])) if row['world_setting'] else WorldSetting(),
            'model_id': row['model_id']
        }
    
    def has_current_config(self) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM galgame_configs WHERE id = 0")
        return cursor.fetchone()[0] > 0
