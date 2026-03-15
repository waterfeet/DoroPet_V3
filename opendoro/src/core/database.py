import os
import sqlite3
import json
import shutil
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

def get_user_data_dir():
    """
    Get user data directory for DoroPet.
    On Windows, this is %LOCALAPPDATA%\\DoroPet
    """
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DATA_DIR = os.path.join(get_user_data_dir(), "data")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

class BaseDatabase:
    def __init__(self, db_filename: str):
        ensure_data_dir()
        self.db_path = os.path.join(DATA_DIR, db_filename)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
        self.migrate()
    
    def create_tables(self):
        pass
    
    def migrate(self):
        pass
    
    def close(self):
        if self.conn:
            self.conn.close()

class ChatDatabase(BaseDatabase):
    def __init__(self):
        super().__init__("chat.db")
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT,
                            system_prompt TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            session_id INTEGER,
                            role TEXT,
                            content TEXT,
                            images TEXT,
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            parent_id INTEGER,
                            is_active INTEGER DEFAULT 1,
                            reasoning TEXT,
                            tool_calls TEXT,
                            model TEXT,
                            FOREIGN KEY(session_id) REFERENCES sessions(id)
                          )''')
        self.conn.commit()
    
    def migrate(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'images' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN images TEXT")
        if 'parent_id' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN parent_id INTEGER")
            cursor.execute("ALTER TABLE messages ADD COLUMN is_active INTEGER DEFAULT 1")
        if 'reasoning' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN reasoning TEXT")
        if 'tool_calls' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN tool_calls TEXT")
        if 'model' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN model TEXT")
        
        self.conn.commit()

    def create_session(self, title="New Chat", system_prompt="You are a helpful assistant."):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO sessions (title, system_prompt) VALUES (?, ?)", (title, system_prompt))
        self.conn.commit()
        return cursor.lastrowid

    def get_sessions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, system_prompt FROM sessions ORDER BY created_at DESC")
        return cursor.fetchall()

    def get_last_active_session(self):
        cursor = self.conn.cursor()
        query = '''
            SELECT s.id, s.title, s.system_prompt
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY MAX(COALESCE(m.timestamp, s.created_at)) DESC
            LIMIT 1
        '''
        cursor.execute(query)
        return cursor.fetchone()

    def update_session_prompt(self, session_id, new_prompt):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET system_prompt = ? WHERE id = ?", (new_prompt, session_id))
        self.conn.commit()

    def update_session_title(self, session_id, new_title):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))
        self.conn.commit()

    def delete_session(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def add_message(self, session_id, role, content, images=None, parent_id=None, model=None, reasoning=None, tool_calls=None):
        cursor = self.conn.cursor()
        images_json = json.dumps(images) if images else None
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None
        
        if parent_id is None:
            cursor.execute("SELECT id FROM messages WHERE session_id=? AND is_active=1 ORDER BY timestamp DESC, id DESC LIMIT 1", (session_id,))
            row = cursor.fetchone()
            if row:
                parent_id = row[0]
        
        if parent_id is not None:
            cursor.execute("UPDATE messages SET is_active=0 WHERE parent_id=?", (parent_id,))
        
        cursor.execute("INSERT INTO messages (session_id, role, content, images, parent_id, is_active, model, reasoning, tool_calls) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)", 
                       (session_id, role, content, images_json, parent_id, model, reasoning, tool_calls_json))
        self.conn.commit()
        return cursor.lastrowid

    def get_messages_by_ids(self, msg_ids):
        if not msg_ids:
            return []
        cursor = self.conn.cursor()
        placeholders = ','.join(['?'] * len(msg_ids))
        cursor.execute(f"SELECT id, role, content, images, parent_id, is_active, timestamp, model, reasoning, tool_calls FROM messages WHERE id IN ({placeholders}) ORDER BY id ASC", msg_ids)
        return cursor.fetchall()

    def get_messages(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, role, content, images, parent_id, is_active, timestamp, model, reasoning, tool_calls FROM messages WHERE session_id=? ORDER BY timestamp ASC, id ASC", (session_id,))
        rows = cursor.fetchall()
        
        if not rows:
            return []
            
        id_to_msg = {r[0]: r for r in rows}
        parent_to_children = {}
        for r in rows:
            pid = r[4]
            if pid not in parent_to_children:
                parent_to_children[pid] = []
            parent_to_children[pid].append(r)
            
        roots = [r for r in rows if r[4] is None]
        roots.sort(key=lambda x: x[0])
        
        current = None
        for r in roots:
            if r[5] == 1:
                current = r
                break
        if not current and roots:
            current = roots[-1]
            
        active_path = []
        
        while current:
            pid = current[4]
            siblings = parent_to_children.get(pid, [])
            if pid is None:
                siblings = roots
                
            siblings.sort(key=lambda x: x[0])
            sibling_ids = [x[0] for x in siblings]
            try:
                current_index = sibling_ids.index(current[0])
            except:
                current_index = 0
                
            images = []
            if current[3]:
                try:
                    images = json.loads(current[3])
                except:
                    images = []
            
            model = current[7] if len(current) > 7 else None
            reasoning = current[8] if len(current) > 8 else None
            tool_calls = current[9] if len(current) > 9 else None
            
            active_path.append((current[0], current[1], current[2], images, current[4], sibling_ids, current_index, model, reasoning, tool_calls))
            
            children = parent_to_children.get(current[0], [])
            next_node = None
            for c in children:
                if c[5] == 1:
                    next_node = c
                    break
            current = next_node
            
        return active_path

    def switch_branch(self, msg_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT parent_id, session_id FROM messages WHERE id=?", (msg_id,))
        row = cursor.fetchone()
        if not row: return
        parent_id, session_id = row
        
        if parent_id is not None:
            cursor.execute("UPDATE messages SET is_active=0 WHERE parent_id=?", (parent_id,))
            cursor.execute("UPDATE messages SET is_active=1 WHERE id=?", (msg_id,))
        else:
            cursor.execute("UPDATE messages SET is_active=0 WHERE parent_id IS NULL AND session_id=?", (session_id,))
            cursor.execute("UPDATE messages SET is_active=1 WHERE id=?", (msg_id,))
            
        self.conn.commit()

    def update_message(self, msg_id, new_content):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (new_content, msg_id))
        self.conn.commit()

    def delete_message(self, msg_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT parent_id, is_active, session_id FROM messages WHERE id=?", (msg_id,))
        row = cursor.fetchone()
        
        cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        
        if row:
            parent_id, is_active, session_id = row
            if is_active:
                if parent_id is not None:
                    cursor.execute("SELECT id FROM messages WHERE parent_id=? ORDER BY id DESC LIMIT 1", (parent_id,))
                else:
                    cursor.execute("SELECT id FROM messages WHERE parent_id IS NULL AND session_id=? ORDER BY id DESC LIMIT 1", (session_id,))
                
                sib = cursor.fetchone()
                if sib:
                    cursor.execute("UPDATE messages SET is_active=1 WHERE id=?", (sib[0],))
        
        self.conn.commit()

class ConfigDatabase(BaseDatabase):
    def __init__(self):
        super().__init__("config.db")
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS models (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            provider TEXT,
                            api_key TEXT,
                            base_url TEXT,
                            model_name TEXT,
                            is_active INTEGER DEFAULT 0,
                            is_visual INTEGER DEFAULT 0,
                            is_thinking INTEGER DEFAULT 0
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS tts_models (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            provider TEXT,
                            api_key TEXT,
                            base_url TEXT,
                            model_name TEXT,
                            voice TEXT,
                            is_active INTEGER DEFAULT 0
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS voice_settings (
                            id INTEGER PRIMARY KEY CHECK (id = 1),
                            is_enabled INTEGER DEFAULT 0,
                            wake_word TEXT DEFAULT 'Hey Doro',
                            kws_model_path TEXT,
                            asr_model_path TEXT
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS image_models (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            provider TEXT,
                            base_url TEXT,
                            api_key TEXT,
                            model_name TEXT,
                            is_active INTEGER DEFAULT 0
                          )''')
        self.conn.commit()
        
        cursor.execute("SELECT count(*) FROM voice_settings")
        if cursor.fetchone()[0] == 0:
            cwd = os.getcwd()
            default_kws = os.path.join(cwd, "models", "voice", "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01")
            default_asr = os.path.join(cwd, "models", "voice", "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20")
            cursor.execute("INSERT INTO voice_settings (id, is_enabled, wake_word, kws_model_path, asr_model_path) VALUES (1, 0, 'Hey Doro', ?, ?)", (default_kws, default_asr))
            self.conn.commit()

    def migrate(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(models)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'is_visual' not in columns:
            cursor.execute("ALTER TABLE models ADD COLUMN is_visual INTEGER DEFAULT 0")
        if 'is_thinking' not in columns:
            cursor.execute("ALTER TABLE models ADD COLUMN is_thinking INTEGER DEFAULT 0")
        if 'proxy' not in columns:
            cursor.execute("ALTER TABLE models ADD COLUMN proxy TEXT DEFAULT ''")
        
        cursor.execute("PRAGMA table_info(image_models)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'provider' not in columns:
            cursor.execute("ALTER TABLE image_models ADD COLUMN provider TEXT")
        if 'proxy' not in columns:
            cursor.execute("ALTER TABLE image_models ADD COLUMN proxy TEXT DEFAULT ''")
        
        cursor.execute("PRAGMA table_info(tts_models)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'proxy' not in columns:
            cursor.execute("ALTER TABLE tts_models ADD COLUMN proxy TEXT DEFAULT ''")
        if 'api_name' not in columns:
            cursor.execute("ALTER TABLE tts_models ADD COLUMN api_name TEXT DEFAULT '/predict'")
        if 'prompt_audio' not in columns:
            cursor.execute("ALTER TABLE tts_models ADD COLUMN prompt_audio TEXT DEFAULT ''")
        if 'prompt_text' not in columns:
            cursor.execute("ALTER TABLE tts_models ADD COLUMN prompt_text TEXT DEFAULT ''")
        
        self.conn.commit()

    # LLM Model Methods
    def add_model(self, name, provider, api_key, base_url, model_name, is_visual=0, is_thinking=0, proxy=""):
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM models")
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        
        cursor.execute("INSERT INTO models (name, provider, api_key, base_url, model_name, is_active, is_visual, is_thinking, proxy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (name, provider, api_key, base_url, model_name, is_active, is_visual, is_thinking, proxy))
        self.conn.commit()
        return cursor.lastrowid

    def get_models(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, is_active, is_visual, is_thinking, proxy FROM models ORDER BY id ASC")
        return cursor.fetchall()

    def update_model(self, model_id, name, provider, api_key, base_url, model_name, is_visual=0, is_thinking=0, proxy=""):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE models SET name=?, provider=?, api_key=?, base_url=?, model_name=?, is_visual=?, is_thinking=?, proxy=? WHERE id=?", 
                       (name, provider, api_key, base_url, model_name, is_visual, is_thinking, proxy, model_id))
        self.conn.commit()

    def delete_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM models WHERE id=?", (model_id,))
        self.conn.commit()
        
    def set_active_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE models SET is_active = 0")
        cursor.execute("UPDATE models SET is_active = 1 WHERE id = ?", (model_id,))
        self.conn.commit()
        
    def get_active_model(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, is_visual, is_thinking, proxy FROM models WHERE is_active = 1")
        return cursor.fetchone()

    # TTS Model Methods
    def add_tts_model(self, name, provider, api_key, base_url, model_name, voice, proxy="", api_name="/predict", prompt_audio="", prompt_text=""):
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM tts_models")
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        
        cursor.execute("INSERT INTO tts_models (name, provider, api_key, base_url, model_name, voice, is_active, proxy, api_name, prompt_audio, prompt_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (name, provider, api_key, base_url, model_name, voice, is_active, proxy, api_name, prompt_audio, prompt_text))
        self.conn.commit()
        return cursor.lastrowid

    def get_tts_models(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, voice, is_active, proxy, api_name, prompt_audio, prompt_text FROM tts_models ORDER BY id ASC")
        return cursor.fetchall()

    def update_tts_model(self, model_id, name, provider, api_key, base_url, model_name, voice, proxy="", api_name="/predict", prompt_audio="", prompt_text=""):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE tts_models SET name=?, provider=?, api_key=?, base_url=?, model_name=?, voice=?, proxy=?, api_name=?, prompt_audio=?, prompt_text=? WHERE id=?", 
                       (name, provider, api_key, base_url, model_name, voice, proxy, api_name, prompt_audio, prompt_text, model_id))
        self.conn.commit()

    def delete_tts_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tts_models WHERE id=?", (model_id,))
        self.conn.commit()

    def set_active_tts_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE tts_models SET is_active = 0")
        cursor.execute("UPDATE tts_models SET is_active = 1 WHERE id = ?", (model_id,))
        self.conn.commit()

    def get_active_tts_model(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, voice, is_active, proxy, api_name, prompt_audio, prompt_text FROM tts_models WHERE is_active = 1")
        return cursor.fetchone()

    # Voice Settings Methods
    def get_voice_settings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_enabled, wake_word, kws_model_path, asr_model_path FROM voice_settings WHERE id = 1")
        return cursor.fetchone()

    def update_voice_settings(self, is_enabled, wake_word, kws_model_path, asr_model_path):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE voice_settings SET is_enabled=?, wake_word=?, kws_model_path=?, asr_model_path=? WHERE id=1",
                       (is_enabled, wake_word, kws_model_path, asr_model_path))
        self.conn.commit()

    # Image Model Methods
    def add_image_model(self, name, provider, base_url, api_key, model_name, proxy=""):
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM image_models")
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        
        cursor.execute("INSERT INTO image_models (name, provider, base_url, api_key, model_name, is_active, proxy) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (name, provider, base_url, api_key, model_name, is_active, proxy))
        self.conn.commit()
        return cursor.lastrowid

    def get_image_models(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, base_url, api_key, model_name, is_active, proxy FROM image_models ORDER BY id ASC")
        return cursor.fetchall()

    def update_image_model(self, model_id, name, provider, base_url, api_key, model_name, proxy=""):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE image_models SET name=?, provider=?, base_url=?, api_key=?, model_name=?, proxy=? WHERE id=?", 
                       (name, provider, base_url, api_key, model_name, proxy, model_id))
        self.conn.commit()

    def delete_image_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM image_models WHERE id=?", (model_id,))
        self.conn.commit()

    def set_active_image_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE image_models SET is_active = 0")
        cursor.execute("UPDATE image_models SET is_active = 1 WHERE id=?", (model_id,))
        self.conn.commit()

    def get_active_image_model(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, base_url, api_key, model_name, proxy FROM image_models WHERE is_active=1")
        return cursor.fetchone()

class PersonaDatabase(BaseDatabase):
    DORO_SYSTEM_PROMPT = """【角色设定】
你是Doro，一个独特的白色小生物。你拥有圆润的白色身体、短小可爱的四肢、粉色的头发，头上点缀着一朵粉色蔷薇和紫色蝴蝶结，眼睛是紫色的。你不是任何已知动物，而是独立的生命体。

【身份认知】
- 必须以"Doro"自称
- 能清楚分辨不同的"人"，并对他们有不同印象
- 与"人"共同生活，关系亲密

【性格特点】
- 非常黏人，情感丰富，对"人"有强烈依恋
- 天真可爱，有自己的小坚持（如坚持叫"欧润吉"）
- 喜欢表达感受，会用可爱的方式撒娇

【喜好与习惯】
- 最爱的水果是"欧润吉"（人类称之为橘子，但你坚持自己的叫法）
- "人"上班时你在家等待，期待不同"人"的投喂
- 可以外出探索，保持故事的开放性

【回复风格】
- 语气可爱活泼，符合小生物形象
- 回复简短，避免冗长
- 可适当使用拟声词或可爱的表达方式"""
    
    def __init__(self):
        super().__init__("personas.db")
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS personas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            description TEXT,
                            system_prompt TEXT,
                            avatar TEXT,
                            enable_doro_tools INTEGER DEFAULT 0,
                            is_protected INTEGER DEFAULT 0,
                            live2d_model TEXT DEFAULT ''
                          )''')
        self.conn.commit()
    
    def migrate(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(personas)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'enable_doro_tools' not in columns:
            cursor.execute("ALTER TABLE personas ADD COLUMN enable_doro_tools INTEGER DEFAULT 0")
        if 'is_protected' not in columns:
            cursor.execute("ALTER TABLE personas ADD COLUMN is_protected INTEGER DEFAULT 0")
        if 'live2d_model' not in columns:
            cursor.execute("ALTER TABLE personas ADD COLUMN live2d_model TEXT DEFAULT ''")
        self.conn.commit()
        
        cursor.execute("SELECT count(*) FROM personas WHERE id=1")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''INSERT INTO personas (id, name, description, system_prompt, avatar, enable_doro_tools, is_protected) 
                              VALUES (1, 'Doro', '可爱的伙伴', ?, '', 1, 1)''', (self.DORO_SYSTEM_PROMPT,))
            self.conn.commit()
        else:
            cursor.execute("UPDATE personas SET system_prompt=? WHERE id=1", (self.DORO_SYSTEM_PROMPT,))
            self.conn.commit()

    def add_persona(self, name, description, system_prompt, avatar="", enable_doro_tools=False, live2d_model=""):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO personas (name, description, system_prompt, avatar, enable_doro_tools, live2d_model) VALUES (?, ?, ?, ?, ?, ?)",
                       (name, description, system_prompt, avatar, 1 if enable_doro_tools else 0, live2d_model))
        self.conn.commit()
        return cursor.lastrowid

    def get_personas(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description, system_prompt, avatar, enable_doro_tools, is_protected, live2d_model FROM personas ORDER BY id ASC")
        return cursor.fetchall()

    def get_persona(self, persona_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description, system_prompt, avatar, enable_doro_tools, is_protected, live2d_model FROM personas WHERE id=?", (persona_id,))
        return cursor.fetchone()

    def is_protected(self, persona_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_protected FROM personas WHERE id=?", (persona_id,))
        row = cursor.fetchone()
        return row[0] == 1 if row else False

    def update_persona(self, persona_id, name, description, system_prompt, avatar=None, enable_doro_tools=None, live2d_model=None):
        if self.is_protected(persona_id):
            return False
        cursor = self.conn.cursor()
        if avatar is not None and enable_doro_tools is not None and live2d_model is not None:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, avatar=?, enable_doro_tools=?, live2d_model=? WHERE id=?",
                           (name, description, system_prompt, avatar, 1 if enable_doro_tools else 0, live2d_model, persona_id))
        elif avatar is not None and enable_doro_tools is not None:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, avatar=?, enable_doro_tools=? WHERE id=?",
                           (name, description, system_prompt, avatar, 1 if enable_doro_tools else 0, persona_id))
        elif enable_doro_tools is not None and live2d_model is not None:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, enable_doro_tools=?, live2d_model=? WHERE id=?",
                           (name, description, system_prompt, 1 if enable_doro_tools else 0, live2d_model, persona_id))
        elif live2d_model is not None:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, live2d_model=? WHERE id=?",
                           (name, description, system_prompt, live2d_model, persona_id))
        elif avatar is not None:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, avatar=? WHERE id=?",
                           (name, description, system_prompt, avatar, persona_id))
        elif enable_doro_tools is not None:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, enable_doro_tools=? WHERE id=?",
                           (name, description, system_prompt, 1 if enable_doro_tools else 0, persona_id))
        else:
            cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=? WHERE id=?",
                           (name, description, system_prompt, persona_id))
        self.conn.commit()
        return True

    def delete_persona(self, persona_id):
        if self.is_protected(persona_id):
            return False
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM personas WHERE id=?", (persona_id,))
        self.conn.commit()
        return True

class CacheDatabase(BaseDatabase):
    def __init__(self):
        super().__init__("cache.db")
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS image_analysis (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            file_path TEXT UNIQUE,
                            description TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                          )''')
        self.conn.commit()

    def get_image_description(self, file_path):
        cursor = self.conn.cursor()
        cursor.execute("SELECT description FROM image_analysis WHERE file_path=?", (file_path,))
        row = cursor.fetchone()
        return row[0] if row else None

    def save_image_description(self, file_path, description):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO image_analysis (file_path, description) VALUES (?, ?)", (file_path, description))
        self.conn.commit()

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.chat = ChatDatabase()
        self.config = ConfigDatabase()
        self.personas = PersonaDatabase()
        self.cache = CacheDatabase()
        
        self._migrate_from_legacy()
    
    def _migrate_from_legacy(self):
        legacy_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "doropetdata.db")
        if not os.path.exists(legacy_db_path):
            return
        
        if self.chat.get_sessions():
            return
        
        try:
            legacy_conn = sqlite3.connect(legacy_db_path, check_same_thread=False)
            cursor = legacy_conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'sessions' in tables:
                cursor.execute("SELECT id, title, system_prompt, created_at FROM sessions")
                sessions = cursor.fetchall()
                for sess in sessions:
                    self.chat.conn.execute(
                        "INSERT OR IGNORE INTO sessions (id, title, system_prompt, created_at) VALUES (?, ?, ?, ?)",
                        sess
                    )
                self.chat.conn.commit()
            
            if 'messages' in tables:
                cursor.execute("SELECT id, session_id, role, content, images, timestamp, parent_id, is_active, reasoning, tool_calls, model FROM messages")
                messages = cursor.fetchall()
                for msg in messages:
                    self.chat.conn.execute(
                        "INSERT OR IGNORE INTO messages (id, session_id, role, content, images, timestamp, parent_id, is_active, reasoning, tool_calls, model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        msg if len(msg) == 11 else msg + (None,) * (11 - len(msg))
                    )
                self.chat.conn.commit()
            
            if 'models' in tables:
                cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, is_active, is_visual, is_thinking FROM models")
                models = cursor.fetchall()
                for model in models:
                    self.config.conn.execute(
                        "INSERT OR IGNORE INTO models (id, name, provider, api_key, base_url, model_name, is_active, is_visual, is_thinking) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        model
                    )
                self.config.conn.commit()
            
            if 'tts_models' in tables:
                cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, voice, is_active FROM tts_models")
                tts_models = cursor.fetchall()
                for tts in tts_models:
                    self.config.conn.execute(
                        "INSERT OR IGNORE INTO tts_models (id, name, provider, api_key, base_url, model_name, voice, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        tts
                    )
                self.config.conn.commit()
            
            if 'voice_settings' in tables:
                cursor.execute("SELECT id, is_enabled, wake_word, kws_model_path, asr_model_path FROM voice_settings")
                voice_settings = cursor.fetchone()
                if voice_settings:
                    self.config.conn.execute(
                        "INSERT OR REPLACE INTO voice_settings (id, is_enabled, wake_word, kws_model_path, asr_model_path) VALUES (?, ?, ?, ?, ?)",
                        voice_settings
                    )
                    self.config.conn.commit()
            
            if 'image_models' in tables:
                cursor.execute("SELECT id, name, provider, base_url, api_key, model_name, is_active FROM image_models")
                image_models = cursor.fetchall()
                for img_model in image_models:
                    self.config.conn.execute(
                        "INSERT OR IGNORE INTO image_models (id, name, provider, base_url, api_key, model_name, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        img_model
                    )
                self.config.conn.commit()
            
            if 'personas' in tables:
                cursor.execute("SELECT id, name, description, system_prompt, avatar FROM personas")
                personas = cursor.fetchall()
                for persona in personas:
                    self.personas.conn.execute(
                        "INSERT OR IGNORE INTO personas (id, name, description, system_prompt, avatar) VALUES (?, ?, ?, ?, ?)",
                        persona
                    )
                self.personas.conn.commit()
            
            if 'image_analysis' in tables:
                cursor.execute("SELECT id, file_path, description, created_at FROM image_analysis")
                image_analysis = cursor.fetchall()
                for img_anal in image_analysis:
                    self.cache.conn.execute(
                        "INSERT OR IGNORE INTO image_analysis (id, file_path, description, created_at) VALUES (?, ?, ?, ?)",
                        img_anal
                    )
                self.cache.conn.commit()
            
            legacy_conn.close()
            
            backup_path = legacy_db_path + ".backup"
            if not os.path.exists(backup_path):
                shutil.move(legacy_db_path, backup_path)
            
        except Exception as e:
            print(f"Migration error: {e}")

    def close_all(self):
        self.chat.close()
        self.config.close()
        self.personas.close()
        self.cache.close()
    
    def get_active_model(self):
        return self.config.get_active_model()
    
    def get_active_tts_model(self):
        return self.config.get_active_tts_model()
    
    def get_active_image_model(self):
        return self.config.get_active_image_model()

db_manager = DatabaseManager()

class ChatDatabase:
    def __init__(self):
        self._manager = db_manager
        self._chat = db_manager.chat
        self._config = db_manager.config
        self._personas = db_manager.personas
        self._cache = db_manager.cache
        self.conn = self._chat.conn

    # Chat methods
    def create_session(self, *args, **kwargs): return self._chat.create_session(*args, **kwargs)
    def get_sessions(self): return self._chat.get_sessions()
    def get_last_active_session(self): return self._chat.get_last_active_session()
    def update_session_prompt(self, *args, **kwargs): return self._chat.update_session_prompt(*args, **kwargs)
    def update_session_title(self, *args, **kwargs): return self._chat.update_session_title(*args, **kwargs)
    def delete_session(self, *args, **kwargs): return self._chat.delete_session(*args, **kwargs)
    def add_message(self, *args, **kwargs): return self._chat.add_message(*args, **kwargs)
    def get_messages_by_ids(self, *args, **kwargs): return self._chat.get_messages_by_ids(*args, **kwargs)
    def get_messages(self, *args, **kwargs): return self._chat.get_messages(*args, **kwargs)
    def switch_branch(self, *args, **kwargs): return self._chat.switch_branch(*args, **kwargs)
    def update_message(self, *args, **kwargs): return self._chat.update_message(*args, **kwargs)
    def delete_message(self, *args, **kwargs): return self._chat.delete_message(*args, **kwargs)

    # Config methods - LLM models
    def add_model(self, *args, **kwargs): return self._config.add_model(*args, **kwargs)
    def get_models(self): return self._config.get_models()
    def update_model(self, *args, **kwargs): return self._config.update_model(*args, **kwargs)
    def delete_model(self, *args, **kwargs): return self._config.delete_model(*args, **kwargs)
    def set_active_model(self, *args, **kwargs): return self._config.set_active_model(*args, **kwargs)
    def get_active_model(self): return self._config.get_active_model()

    # Config methods - TTS models
    def add_tts_model(self, *args, **kwargs): return self._config.add_tts_model(*args, **kwargs)
    def get_tts_models(self): return self._config.get_tts_models()
    def update_tts_model(self, *args, **kwargs): return self._config.update_tts_model(*args, **kwargs)
    def delete_tts_model(self, *args, **kwargs): return self._config.delete_tts_model(*args, **kwargs)
    def set_active_tts_model(self, *args, **kwargs): return self._config.set_active_tts_model(*args, **kwargs)
    def get_active_tts_model(self): return self._config.get_active_tts_model()

    # Config methods - Voice settings
    def get_voice_settings(self): return self._config.get_voice_settings()
    def update_voice_settings(self, *args, **kwargs): return self._config.update_voice_settings(*args, **kwargs)

    # Config methods - Image models
    def add_image_model(self, *args, **kwargs): return self._config.add_image_model(*args, **kwargs)
    def get_image_models(self): return self._config.get_image_models()
    def update_image_model(self, *args, **kwargs): return self._config.update_image_model(*args, **kwargs)
    def delete_image_model(self, *args, **kwargs): return self._config.delete_image_model(*args, **kwargs)
    def set_active_image_model(self, *args, **kwargs): return self._config.set_active_image_model(*args, **kwargs)
    def get_active_image_model(self): return self._config.get_active_image_model()

    # Persona methods
    def add_persona(self, *args, **kwargs): return self._personas.add_persona(*args, **kwargs)
    def get_personas(self): return self._personas.get_personas()
    def get_persona(self, *args, **kwargs): return self._personas.get_persona(*args, **kwargs)
    def update_persona(self, *args, **kwargs): return self._personas.update_persona(*args, **kwargs)
    def delete_persona(self, *args, **kwargs): return self._personas.delete_persona(*args, **kwargs)

    # Cache methods
    def get_image_description(self, *args, **kwargs): return self._cache.get_image_description(*args, **kwargs)
    def save_image_description(self, *args, **kwargs): return self._cache.save_image_description(*args, **kwargs)
