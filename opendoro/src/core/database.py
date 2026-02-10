import sqlite3
import datetime

class ChatDatabase:
    def __init__(self, db_name="doropetdata.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
        self.migrate_db()

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
                            FOREIGN KEY(session_id) REFERENCES sessions(id)
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS personas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            description TEXT,
                            system_prompt TEXT,
                            avatar TEXT
                          )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS models (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT,
                            provider TEXT,
                            api_key TEXT,
                            base_url TEXT,
                            model_name TEXT,
                            is_active INTEGER DEFAULT 0
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
                            base_url TEXT,
                            api_key TEXT,
                            model_name TEXT,
                            is_active INTEGER DEFAULT 0
                          )''')
        self.conn.commit()
        
        # Initialize default voice settings if not exists
        cursor.execute("SELECT count(*) FROM voice_settings")
        if cursor.fetchone()[0] == 0:
            import os
            cwd = os.getcwd()
            default_kws = os.path.join(cwd, "models", "voice", "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01")
            default_asr = os.path.join(cwd, "models", "voice", "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20")
            cursor.execute("INSERT INTO voice_settings (id, is_enabled, wake_word, kws_model_path, asr_model_path) VALUES (1, 0, 'Hey Doro', ?, ?)", (default_kws, default_asr))
            self.conn.commit()

    def migrate_db(self):
        cursor = self.conn.cursor()
        # Check if 'images' column exists in 'messages' table
        cursor.execute("PRAGMA table_info(messages)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'images' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN images TEXT")
            self.conn.commit()
            
        # Check if 'provider' column exists in 'image_models' table
        cursor.execute("PRAGMA table_info(image_models)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'provider' not in columns:
            cursor.execute("ALTER TABLE image_models ADD COLUMN provider TEXT")
            self.conn.commit()

    # --- Model Methods ---
    def add_model(self, name, provider, api_key, base_url, model_name):
        cursor = self.conn.cursor()
        # If it's the first model, make it active
        cursor.execute("SELECT count(*) FROM models")
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        
        cursor.execute("INSERT INTO models (name, provider, api_key, base_url, model_name, is_active) VALUES (?, ?, ?, ?, ?, ?)", 
                       (name, provider, api_key, base_url, model_name, is_active))
        self.conn.commit()
        return cursor.lastrowid

    def get_models(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, is_active FROM models ORDER BY id ASC")
        return cursor.fetchall()

    def update_model(self, model_id, name, provider, api_key, base_url, model_name):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE models SET name=?, provider=?, api_key=?, base_url=?, model_name=? WHERE id=?", 
                       (name, provider, api_key, base_url, model_name, model_id))
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
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name FROM models WHERE is_active = 1")
        return cursor.fetchone()

    # --- Image Model Methods ---
    def add_image_model(self, name, provider, base_url, api_key, model_name):
        cursor = self.conn.cursor()
        # If it's the first model, make it active
        cursor.execute("SELECT count(*) FROM image_models")
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        
        cursor.execute("INSERT INTO image_models (name, provider, base_url, api_key, model_name, is_active) VALUES (?, ?, ?, ?, ?, ?)", 
                       (name, provider, base_url, api_key, model_name, is_active))
        self.conn.commit()
        return cursor.lastrowid

    def get_image_models(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, base_url, api_key, model_name, is_active FROM image_models ORDER BY id ASC")
        return cursor.fetchall()

    def update_image_model(self, model_id, name, provider, base_url, api_key, model_name):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE image_models SET name=?, provider=?, base_url=?, api_key=?, model_name=? WHERE id=?", 
                       (name, provider, base_url, api_key, model_name, model_id))
        self.conn.commit()

    def delete_image_model(self, model_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM image_models WHERE id=?", (model_id,))
        self.conn.commit()

    def set_active_image_model(self, model_id):
        cursor = self.conn.cursor()
        # Set all to inactive
        cursor.execute("UPDATE image_models SET is_active = 0")
        # Set selected to active
        cursor.execute("UPDATE image_models SET is_active = 1 WHERE id=?", (model_id,))
        self.conn.commit()

    def get_active_image_model(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, base_url, api_key, model_name FROM image_models WHERE is_active=1")
        return cursor.fetchone()

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

    def delete_session(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def add_message(self, session_id, role, content, images=None):
        cursor = self.conn.cursor()
        # images is a list of paths, convert to JSON string if needed, or just semicolon separated
        # For simplicity, let's use json
        import json
        images_json = json.dumps(images) if images else None
        
        cursor.execute("INSERT INTO messages (session_id, role, content, images) VALUES (?, ?, ?, ?)", 
                       (session_id, role, content, images_json))
        self.conn.commit()
        return cursor.lastrowid

    def get_messages(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, role, content, images FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        
        # Parse images JSON back to list
        import json
        result = []
        for r in rows:
            msg_id, role, content, images_json = r
            images = []
            if images_json:
                try:
                    images = json.loads(images_json)
                except:
                    images = []
            result.append((msg_id, role, content, images))
        return result

    def update_message(self, msg_id, new_content):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (new_content, msg_id))
        self.conn.commit()

    def delete_message(self, msg_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        self.conn.commit()

    # --- Persona Methods ---

    def add_persona(self, name, description, system_prompt, avatar=""):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO personas (name, description, system_prompt, avatar) VALUES (?, ?, ?, ?)", 
                       (name, description, system_prompt, avatar))
        self.conn.commit()
        return cursor.lastrowid

    def get_personas(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description, system_prompt, avatar FROM personas ORDER BY id DESC")
        return cursor.fetchall()

    def update_persona(self, persona_id, name, description, system_prompt, avatar=""):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE personas SET name=?, description=?, system_prompt=?, avatar=? WHERE id=?", 
                       (name, description, system_prompt, avatar, persona_id))
        self.conn.commit()

    def delete_persona(self, persona_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM personas WHERE id=?", (persona_id,))
        self.conn.commit()

    # --- TTS Model Methods ---
    def add_tts_model(self, name, provider, api_key, base_url, model_name, voice=""):
        cursor = self.conn.cursor()
        # If it's the first model, make it active
        cursor.execute("SELECT count(*) FROM tts_models")
        count = cursor.fetchone()[0]
        is_active = 1 if count == 0 else 0
        
        cursor.execute("INSERT INTO tts_models (name, provider, api_key, base_url, model_name, voice, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (name, provider, api_key, base_url, model_name, voice, is_active))
        self.conn.commit()
        return cursor.lastrowid

    def get_tts_models(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, voice, is_active FROM tts_models ORDER BY id ASC")
        return cursor.fetchall()

    def update_tts_model(self, model_id, name, provider, api_key, base_url, model_name, voice):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE tts_models SET name=?, provider=?, api_key=?, base_url=?, model_name=?, voice=? WHERE id=?", 
                       (name, provider, api_key, base_url, model_name, voice, model_id))
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
        cursor.execute("SELECT id, name, provider, api_key, base_url, model_name, voice, is_active FROM tts_models WHERE is_active = 1")
        return cursor.fetchone()

    # --- Voice Settings Methods ---
    def get_voice_settings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_enabled, wake_word, kws_model_path, asr_model_path FROM voice_settings WHERE id = 1")
        return cursor.fetchone()

    def update_voice_settings(self, is_enabled, wake_word, kws_model_path, asr_model_path):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE voice_settings SET is_enabled=?, wake_word=?, kws_model_path=?, asr_model_path=? WHERE id=1", 
                       (is_enabled, wake_word, kws_model_path, asr_model_path))
        self.conn.commit()
