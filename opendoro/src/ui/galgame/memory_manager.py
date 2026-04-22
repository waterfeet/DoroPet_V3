import random
from datetime import datetime
from typing import List, Dict, Optional, Set
from .models import CharacterMemory, MemoryType
from .database import GalgameDatabase


class CharacterMemoryManager:
    def __init__(self, db: GalgameDatabase):
        self._db = db
        self._memory_cache: Dict[str, List[CharacterMemory]] = {}
        self._state_id: Optional[int] = None
    
    def set_state_id(self, state_id: int):
        self._state_id = state_id
        self._load_cache()
    
    def _load_cache(self):
        if self._state_id is None:
            return
        self._memory_cache.clear()
        all_memories = self._db.get_memories(self._state_id)
        for memory in all_memories:
            if memory.character_name not in self._memory_cache:
                self._memory_cache[memory.character_name] = []
            self._memory_cache[memory.character_name].append(memory)
    
    def add_memory(
        self,
        character_name: str,
        memory_type: str,
        content: str,
        importance: int = 5,
        context: Dict = None,
        auto_save: bool = True
    ) -> CharacterMemory:
        memory = CharacterMemory(
            id=0,
            character_name=character_name,
            memory_type=memory_type,
            content=content,
            importance=min(10, max(1, importance)),
            timestamp=datetime.now().isoformat(),
            context=context or {},
            is_remembered=True
        )
        
        if auto_save and self._state_id:
            memory_id = self._db.save_memory(self._state_id, memory)
            memory = CharacterMemory(
                id=memory_id,
                character_name=memory.character_name,
                memory_type=memory.memory_type,
                content=memory.content,
                importance=memory.importance,
                timestamp=memory.timestamp,
                context=memory.context,
                is_remembered=memory.is_remembered
            )
        
        if character_name not in self._memory_cache:
            self._memory_cache[character_name] = []
        self._memory_cache[character_name].append(memory)
        
        return memory
    
    def get_relevant_memories(
        self,
        character_name: str,
        current_context: str = "",
        limit: int = 3
    ) -> List[CharacterMemory]:
        memories = self._memory_cache.get(character_name, [])
        if not memories:
            return []
        
        scored_memories = []
        for memory in memories:
            if not memory.is_remembered:
                continue
            score = self._calculate_relevance(memory, current_context)
            scored_memories.append((memory, score))
        
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in scored_memories[:limit]]
    
    def get_all_memories(self, character_name: str = None) -> List[CharacterMemory]:
        if character_name:
            return self._memory_cache.get(character_name, [])
        all_memories = []
        for memories in self._memory_cache.values():
            all_memories.extend(memories)
        return sorted(all_memories, key=lambda x: x.timestamp, reverse=True)
    
    def _calculate_relevance(self, memory: CharacterMemory, context: str) -> float:
        score = memory.importance * 10
        
        memory_words = set(memory.content.lower().split())
        context_words = set(context.lower().split()) if context else set()
        common_words = memory_words & context_words
        score += len(common_words) * 5
        
        try:
            memory_time = datetime.fromisoformat(memory.timestamp)
            days_ago = (datetime.now() - memory_time).days
            score -= days_ago * 0.5
        except:
            pass
        
        return max(0, score)
    
    def has_memory_type(self, character_name: str, memory_type: str, keyword: str = None) -> bool:
        memories = self._memory_cache.get(character_name, [])
        for memory in memories:
            if memory.memory_type == memory_type:
                if keyword is None or keyword in memory.content:
                    return True
        return False
    
    def forget_memory(self, character_name: str, memory_id: int):
        if character_name in self._memory_cache:
            for memory in self._memory_cache[character_name]:
                if memory.id == memory_id:
                    memory.is_remembered = False
                    break
    
    def build_memory_prompt(self, character_name: str, current_context: str = "") -> str:
        memories = self.get_relevant_memories(character_name, current_context, limit=3)
        if not memories:
            return ""
        
        memory_texts = []
        for memory in memories:
            prefix_map = {
                "interaction": "💭",
                "promise": "🤝",
                "gift": "🎁",
                "conflict": "⚡",
                "special": "⭐"
            }
            prefix = prefix_map.get(memory.memory_type, "•")
            memory_texts.append(f"{prefix} {memory.content}")
        
        return f"""
## {character_name}记得的事情

{chr(10).join(memory_texts)}

请在对话中自然地体现这些记忆，让角色展现出对过去事件的回忆和情感反应。
"""

    def extract_memories_from_text(self, text: str, character_name: str) -> List[Dict]:
        memories_to_add = []
        
        gift_keywords = ["送", "送给", "礼物", "赠送", "给了"]
        for keyword in gift_keywords:
            if keyword in text:
                memories_to_add.append({
                    "type": "gift",
                    "content": f"收到了来自主角的礼物",
                    "importance": 6
                })
                break
        
        promise_keywords = ["答应", "承诺", "保证", "一定", "说好了"]
        for keyword in promise_keywords:
            if keyword in text:
                memories_to_add.append({
                    "type": "promise",
                    "content": f"与主角做出了约定",
                    "importance": 7
                })
                break
        
        conflict_keywords = ["争吵", "争执", "生气", "不满", "讨厌"]
        for keyword in conflict_keywords:
            if keyword in text:
                memories_to_add.append({
                    "type": "conflict",
                    "content": f"与主角发生了争执",
                    "importance": 5
                })
                break
        
        help_keywords = ["帮助", "帮忙", "协助", "拯救"]
        for keyword in help_keywords:
            if keyword in text:
                memories_to_add.append({
                    "type": "interaction",
                    "content": f"得到了主角的帮助",
                    "importance": 6
                })
                break
        
        return memories_to_add

    def get_memory_summary(self, character_name: str) -> Dict[str, int]:
        memories = self._memory_cache.get(character_name, [])
        summary = {
            "total": len(memories),
            "interaction": 0,
            "promise": 0,
            "gift": 0,
            "conflict": 0,
            "special": 0
        }
        for memory in memories:
            if memory.memory_type in summary:
                summary[memory.memory_type] += 1
        return summary
