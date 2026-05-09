"""
AI 驱动的智能记忆管理系统
"""
import json
from datetime import datetime
from typing import List, Dict, Optional
from PyQt5.QtCore import QEventLoop, QThread, pyqtSignal
from src.core.database import ChatDatabase


class MemoryAnalyzeWorker(QThread):
    """后台异步分析消息记忆的 Worker 线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, model, messages, parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._messages = messages

    def run(self):
        try:
            from src.services.llm_service import LLMWorker

            loop = QEventLoop()
            result = [None]

            worker = LLMWorker(
                api_key=self._api_key,
                base_url=self._base_url,
                messages=self._messages,
                model=self._model,
                db=None,
                is_thinking=0,
                enabled_plugins=[],
                skip_tools_and_max_tokens=True,
            )

            def on_finished(content, reasoning, tool_calls, images):
                result[0] = content
                loop.quit()

            def on_error(error_msg):
                loop.quit()

            worker.finished.connect(on_finished)
            worker.error.connect(on_error)
            worker.start()

            loop.exec_()

            if result[0]:
                analysis = json.loads(result[0].strip())
                self.finished.emit(analysis)
            else:
                self.error.emit("analysis returned empty")
        except Exception as e:
            self.error.emit(str(e))


class MemoryManager:
    """智能记忆管理器"""

    def __init__(self, chat_db):
        self.db = chat_db
        self.short_term_messages = []
        self.max_short_term = 15
        self._active_model_config = None

    def set_model_config(self, api_key, base_url, model):
        self._active_model_config = (api_key, base_url, model)

    def _get_active_model_config(self):
        if self._active_model_config:
            return self._active_model_config
        try:
            models = self.db.get_models()
            for m in models:
                if len(m) >= 6 and m[6]:
                    api_key = m[3] or ""
                    base_url = m[4] or ""
                    model_name = m[5] or ""
                    if api_key and base_url and model_name:
                        self._active_model_config = (api_key, base_url, model_name)
                        return self._active_model_config
        except Exception as e:
            print(f"[MemoryManager] 获取模型配置失败：{e}")
        return None

    def analyze_message_importance(self, content: str, role: str) -> Dict:
        prompt = f"""
你是一个智能记忆分析助手。请分析以下对话内容，判断其重要性和类型。

【分析标准】
- 事实信息（5 分）：用户的个人信息、名字、年龄、职业、住址等
- 偏好设定（4 分）：用户的喜好、厌恶、习惯、偏好等
- 重要事件（3 分）：用户提到的重要事情、计划、决定等
- 情绪表达（2 分）：用户的情绪状态、感受等
- 日常对话（1 分）：普通问候、闲聊等

【输出格式】
请严格按照以下 JSON 格式输出：
{{
    "importance": 数字 (1-5),
    "category": "fact|preference|event|emotion|normal",
    "should_remember": true/false,
    "summary": "如果是重要信息，用一句话概括（20 字以内）",
    "keywords": ["关键词 1", "关键词 2"],
    "reason": "简要说明判断理由"
}}

【待分析的对话】
角色：{role}
内容：{content}

请分析："""
        return self.simple_analyze(content, role)

    def analyze_async(self, content: str, role: str, callback=None):
        model_config = self._get_active_model_config()
        if not model_config:
            analysis = self.simple_analyze(content, role)
            if callback:
                callback(analysis)
            return

        api_key, base_url, model_name = model_config

        prompt = f"""
你是一个智能记忆分析助手。请分析以下对话内容，判断其重要性和类型。

【分析标准】
- 事实信息（5 分）：用户的个人信息、名字、年龄、职业、住址等
- 偏好设定（4 分）：用户的喜好、厌恶、习惯、偏好等
- 重要事件（3 分）：用户提到的重要事情、计划、决定等
- 情绪表达（2 分）：用户的情绪状态、感受等
- 日常对话（1 分）：普通问候、闲聊等

【输出格式】
请严格按照以下 JSON 格式输出：
{{
    "importance": 数字 (1-5),
    "category": "fact|preference|event|emotion|normal",
    "should_remember": true/false,
    "summary": "如果是重要信息，用一句话概括（20 字以内）",
    "keywords": ["关键词 1", "关键词 2"],
    "reason": "简要说明判断理由"
}}

【待分析的对话】
角色：{role}
内容：{content}

请分析："""

        self._analysis_worker = MemoryAnalyzeWorker(
            api_key=api_key,
            base_url=base_url,
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )

        def on_finished(analysis):
            if callback:
                callback(analysis)

        def on_error(err):
            print(f"[MemoryManager] 异步分析失败：{err}")
            analysis = self.simple_analyze(content, role)
            if callback:
                callback(analysis)

        self._analysis_worker.finished.connect(on_finished)
        self._analysis_worker.error.connect(on_error)
        self._analysis_worker.start()
    
    def compress_conversation(self, messages: List[Dict]) -> str:
        """
        使用 AI 压缩一段对话，生成摘要
        
        参数：
        messages: [{"role": "user/assistant", "content": "..."}]
        
        返回：
        摘要文本
        """
        from src.services.llm_service import LLMWorker
        
        model_config = self._get_active_model_config()
        if not model_config:
            print("[MemoryManager] 无有效模型配置，跳过压缩")
            return "对话摘要（跳过AI压缩）"
        
        api_key, base_url, model_name = model_config
        
        formatted = "\n".join([
            f"{m['role']}: {m['content']}" for m in messages
        ])
        
        prompt = f"""
请总结以下对话，提取关键信息：

【要求】
1. 提取用户的个人信息（名字、喜好、设定等）
2. 记录重要事件和决定
3. 概括对话主题
4. 保持在 100 字以内
5. 使用简洁的中文

【对话内容】
{formatted}

【总结】"""

        try:
            worker = LLMWorker(
                api_key=api_key,
                base_url=base_url,
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                db=None,
                is_thinking=0,
                enabled_plugins=[]
            )
            
            loop = QEventLoop()
            summary = [None]
            
            def on_finished(content, *args):
                summary[0] = content
                loop.quit()
            
            def on_error(error):
                summary[0] = "对话摘要失败"
                loop.quit()
            
            worker.finished.connect(on_finished)
            worker.error.connect(on_error)
            worker.start()
            
            loop.exec_()
            
            return summary[0].strip() if summary[0] else "对话摘要失败"
            
        except Exception as e:
            print(f"[MemoryManager] 压缩失败：{e}")
            return "对话摘要失败"
    
    def add_message(self, role: str, content: str, session_id: int):
        """
        添加消息并智能处理
        
        注意：为了避免阻塞主线程，这里只做简单的同步操作
        AI 分析和压缩应该在后台线程中进行
        """
        self.short_term_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        analysis = self.simple_analyze(content, role)
        
        if analysis.get("should_remember", False):
            self.save_to_long_term_memory(
                category=analysis.get("category", "normal"),
                content=analysis.get("summary", content),
                importance=analysis.get("importance", 3),
                keywords=analysis.get("keywords", []),
                original_content=content
            )
        
        if len(self.short_term_messages) > self.max_short_term:
            to_remove = len(self.short_term_messages) - self.max_short_term
            self.short_term_messages = self.short_term_messages[to_remove:]
    
    def simple_analyze(self, content: str, role: str) -> Dict:
        """
        简化版分析（使用规则，不调用 AI）
        
        后续可以替换为 AI 分析
        """
        # 简单规则判断
        if role != "user":
            return {"importance": 1, "category": "normal", "should_remember": False}
        
        # 检查是否包含关键信息
        keywords_to_remember = ['我叫', '我是', '我喜欢', '我讨厌', '记住', '我的名字', '今年', '住在']
        for keyword in keywords_to_remember:
            if keyword in content:
                return {
                    "importance": 4,
                    "category": "fact",
                    "should_remember": True,
                    "summary": content[:50],
                    "keywords": [keyword]
                }
        
        # 默认不记忆
        return {
            "importance": 1,
            "category": "normal",
            "should_remember": False
        }
    
    def _text_similarity(self, a: str, b: str) -> float:
        """计算两个文本的相似度 (0-1)，基于字符 bigram 的 Jaccard 系数"""
        if not a or not b:
            return 0.0
        a = a.strip().lower()
        b = b.strip().lower()

        def bigrams(s):
            return {s[i:i+2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}

        ba, bb = bigrams(a), bigrams(b)
        union = len(ba | bb)
        if union == 0:
            return 0.0
        return len(ba & bb) / union

    def _find_similar_memory(self, category: str, content: str, threshold: float = 0.55):
        """查找同类别中与 content 相似度超过阈值的第一条记忆，返回 (id, content, sim, keywords)"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT id, content, keywords FROM user_memories
            WHERE category=?
            ORDER BY importance DESC
        """, (category,))
        rows = cursor.fetchall()
        for row in rows:
            sim = self._text_similarity(content, row[1])
            if sim >= threshold:
                return (row[0], row[1], sim, row[2])
        return None

    def save_to_long_term_memory(self, category: str, content: str, 
                                  importance: int, keywords: List[str],
                                  original_content: str):
        """保存到长期记忆数据库"""
        if not content or len(content.strip()) < 2:
            return

        cursor = self.db.conn.cursor()

        similar = self._find_similar_memory(category, content)
        if similar:
            mem_id, existing_content, sim, existing_keywords = similar
            if sim >= 0.85:
                print(f"[MemoryManager] 记忆高度相似({sim:.2f})，跳过：{content} | 已有：{existing_content}")
                return
            else:
                existing_kws = json.loads(existing_keywords) if existing_keywords else []
                merged_kws = list(set(keywords + existing_kws))
                cursor.execute("""
                    UPDATE user_memories
                    SET content=?, importance=MAX(importance, ?), keywords=?,
                        original_content=?, last_accessed=datetime('now')
                    WHERE id=?
                """, (content, importance, json.dumps(merged_kws),
                      original_content, mem_id))
                self.db.conn.commit()
                print(f"[MemoryManager] 记忆合并更新({sim:.2f})：{content} ← 已有：{existing_content}")
                return

        cursor.execute("""
            INSERT INTO user_memories 
            (category, content, importance, keywords, original_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            category,
            content,
            importance,
            json.dumps(keywords),
            original_content,
            datetime.now()
        ))

        self.db.conn.commit()
        print(f"[MemoryManager] 保存长期记忆：{content}")
    
    def compress_old_messages(self, session_id: int):
        """压缩旧的短期记忆"""
        to_compress = self.short_term_messages[:-10]
        remaining = self.short_term_messages[-10:]
        
        if len(to_compress) < 3:
            return
        
        summary = self.compress_conversation(to_compress)
        
        if summary and summary != "对话摘要（跳过AI压缩）":
            cursor = self.db.conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_summaries 
                (session_id, summary, start_message_id, end_message_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                summary,
                0,
                0,
                datetime.now()
            ))
            self.db.conn.commit()
            print(f"[MemoryManager] 压缩了 {len(to_compress)} 条消息为摘要")
        
        self.short_term_messages = remaining
    
    def get_context(self, session_id: int, memory_limit: int = 10) -> List[Dict]:
        """
        构建发送给 AI 的完整上下文
        
        包括：
        1. 长期记忆（用户信息）
        2. 历史摘要
        3. 短期记忆（完整对话）
        """
        context = []
        
        # 1. 添加长期记忆
        long_term = self.get_long_term_memories(memory_limit)
        if long_term:
            facts = self.format_long_term_memories(long_term)
            context.append({
                "role": "system",
                "content": f"【用户记忆】\n{facts}"
            })
        
        # 2. 添加历史摘要
        summaries = self.get_recent_summaries(session_id)
        if summaries:
            context.append({
                "role": "system",
                "content": f"【历史对话摘要】\n{summaries}"
            })
        
        # 3. 添加短期记忆（完整对话）
        context.extend(self.short_term_messages)
        
        return context
    
    def get_long_term_memories(self, limit: int = 50) -> List[Dict]:
        """获取长期记忆"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT category, content, importance, keywords, created_at
            FROM user_memories
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """, (limit,))
        
        memories = []
        for row in cursor.fetchall():
            memories.append({
                "category": row[0],
                "content": row[1],
                "importance": row[2],
                "keywords": json.loads(row[3]) if row[3] else [],
                "created_at": row[4]
            })
        
        return memories
    
    def get_recent_summaries(self, session_id: int) -> str:
        """获取最近的历史摘要"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT summary FROM conversation_summaries
            WHERE session_id=?
            ORDER BY created_at DESC
            LIMIT 5
        """, (session_id,))
        
        summaries = [row[0] for row in cursor.fetchall()]
        return "\n".join(reversed(summaries))
    
    def format_long_term_memories(self, memories: List[Dict]) -> str:
        """格式化长期记忆"""
        lines = []
        
        # 按类别分组
        facts = [m for m in memories if m["category"] == "fact"]
        preferences = [m for m in memories if m["category"] == "preference"]
        events = [m for m in memories if m["category"] == "event"]
        
        if facts:
            lines.append("【用户信息】")
            for f in facts:
                lines.append(f"- {f['content']}")
        
        if preferences:
            lines.append("\n【用户偏好】")
            for p in preferences:
                lines.append(f"- {p['content']}")
        
        if events:
            lines.append("\n【重要事件】")
            for e in events:
                lines.append(f"- {e['content']}")
        
        return "\n".join(lines)


# 数据库初始化函数
def init_memory_database(chat_db):
    """初始化记忆数据库表"""
    cursor = chat_db.conn.cursor()
    
    # 用户记忆表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,  -- fact|preference|event|emotion
            content TEXT NOT NULL,
            importance INTEGER DEFAULT 3,
            keywords TEXT,
            original_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 对话摘要表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            start_message_id INTEGER,
            end_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_category 
        ON user_memories(category)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_importance 
        ON user_memories(importance DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_summaries_session 
        ON conversation_summaries(session_id)
    """)
    
    chat_db.conn.commit()
    print("[MemoryManager] 数据库表初始化完成")
