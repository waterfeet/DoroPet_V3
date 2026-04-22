from datetime import datetime
from typing import List, Optional, Dict
from .models import GameState, AffectionState, GameEnding, EndingType, EndingCondition
from .database import GalgameDatabase
from src.provider.manager import ProviderManager
from src.core.logger import logger


class EndingManager:
    def __init__(self, db: GalgameDatabase, provider_manager: ProviderManager = None):
        self._db = db
        self._provider_manager = provider_manager
        self._ending_conditions = self._init_ending_conditions()
    
    def _init_ending_conditions(self) -> List[EndingCondition]:
        return [
            EndingCondition(
                ending_type="perfect",
                condition_name="完美结局",
                condition_description="与某位角色达成完美结局，好感度达到100且专一"
            ),
            EndingCondition(
                ending_type="harem",
                condition_name="后宫结局",
                condition_description="与多位角色保持亲密关系，好感度达到100"
            ),
            EndingCondition(
                ending_type="normal",
                condition_name="普通结局",
                condition_description="游戏超过10章，最高好感度达到70以上"
            ),
            EndingCondition(
                ending_type="lonely",
                condition_name="孤独结局",
                condition_description="游戏超过10章，最高好感度低于70"
            ),
        ]
    
    def check_ending_trigger(self, state: GameState) -> Optional[str]:
        if not state.affections:
            return None
        
        max_affection = max(a.affection for a in state.affections)
        
        if max_affection >= 100:
            high_aff_count = sum(1 for a in state.affections if a.affection >= 50)
            if high_aff_count == 1:
                return "perfect"
            else:
                return "harem"
        
        if state.chapter >= 10:
            if max_affection >= 70:
                return "normal"
            else:
                return "lonely"
        
        return None
    
    def get_ending_character(self, state: GameState, ending_type: str) -> Optional[str]:
        if ending_type == "perfect":
            for aff in state.affections:
                if aff.affection >= 100:
                    return aff.character_name
        elif ending_type == "harem":
            high_aff_chars = [a.character_name for a in state.affections if a.affection >= 80]
            return "、".join(high_aff_chars[:3])
        return None
    
    def generate_ending(
        self,
        state: GameState,
        ending_type: str,
        character_name: str = None,
        model_id: str = None
    ) -> GameEnding:
        ending_titles = {
            "perfect": {
                "prefix": "💕 完美结局：",
                "titles": [
                    "永恒的誓言",
                    "命中注定的相遇",
                    "幸福的终点",
                    "爱的告白",
                    "携手共度余生"
                ]
            },
            "harem": {
                "prefix": "🌸 后宫结局：",
                "titles": [
                    "众星捧月",
                    "幸福的烦恼",
                    "难以抉择的心",
                    "被爱包围的日子"
                ]
            },
            "normal": {
                "prefix": "📖 普通结局：",
                "titles": [
                    "未完的故事",
                    "新的开始",
                    "继续前行",
                    "平凡的日子"
                ]
            },
            "lonely": {
                "prefix": "💔 孤独结局：",
                "titles": [
                    "独自一人",
                    "错过的缘分",
                    "孤独的旅程",
                    "无人相伴"
                ]
            }
        }
        
        import random
        ending_info = ending_titles.get(ending_type, ending_titles["normal"])
        ending_title = ending_info["prefix"] + random.choice(ending_info["titles"])
        
        ending_story = self._generate_ending_story(state, ending_type, character_name, model_id)
        
        play_time = self._calculate_play_time(state)
        
        ending = GameEnding(
            id=0,
            ending_type=ending_type,
            character_name=character_name or "",
            ending_title=ending_title,
            ending_description=self._get_ending_description(ending_type, character_name),
            ending_story=ending_story,
            final_affection=max(a.affection for a in state.affections) if state.affections else 0,
            total_chapters=state.chapter,
            play_time=play_time,
            timestamp=datetime.now().isoformat()
        )
        
        return ending
    
    def _generate_ending_story(
        self,
        state: GameState,
        ending_type: str,
        character_name: str,
        model_id: str = None
    ) -> str:
        if not self._provider_manager:
            return self._get_default_ending_story(ending_type, character_name)
        
        try:
            provider = self._provider_manager.get_llm_provider(model_id)
            if not provider:
                return self._get_default_ending_story(ending_type, character_name)
            
            prompt = self._build_ending_prompt(state, ending_type, character_name)
            
            response = provider.chat([{"role": "user", "content": prompt}], temperature=0.9, max_tokens=1500)
            
            if response and response.content:
                return response.content
        except Exception as e:
            logger.error(f"Error generating ending story: {e}")
        
        return self._get_default_ending_story(ending_type, character_name)
    
    def _build_ending_prompt(self, state: GameState, ending_type: str, character_name: str) -> str:
        ending_prompts = {
            "perfect": f"""
请为以下视觉小说游戏创作一个完美的结局故事：

**主角**：{state.protagonist.name if state.protagonist else '玩家'}
**达成结局的角色**：{character_name}
**好感度**：100（挚爱）
**故事背景**：{state.world_setting.name if state.world_setting else '现代都市'}
**经历章节**：{state.chapter}章

请创作一个温馨、感人的结局故事（300-500字），包含：
1. 最后的告白或承诺场景
2. 两人未来的展望
3. 给玩家一个圆满的结局感

注意：故事要温馨感人，体现两人从陌生到相爱的过程。
""",
            "harem": f"""
请为以下视觉小说游戏创作一个后宫结局故事：

**主角**：{state.protagonist.name if state.protagonist else '玩家'}
**亲密角色**：{character_name}
**故事背景**：{state.world_setting.name if state.world_setting else '现代都市'}

请创作一个轻松、有趣的结局故事（300-500字），体现主角被多人爱慕的"幸福烦恼"。
""",
            "normal": f"""
请为以下视觉小说游戏创作一个普通结局故事：

**主角**：{state.protagonist.name if state.protagonist else '玩家'}
**最高好感度**：{max(a.affection for a in state.affections) if state.affections else 0}
**故事背景**：{state.world_setting.name if state.world_setting else '现代都市'}

请创作一个开放式的结局故事（300-500字），暗示故事还在继续，未来还有可能。
""",
            "lonely": f"""
请为以下视觉小说游戏创作一个孤独结局故事：

**主角**：{state.protagonist.name if state.protagonist else '玩家'}
**故事背景**：{state.world_setting.name if state.world_setting else '现代都市'}

请创作一个略带遗憾但仍有希望的结局故事（300-500字），暗示主角需要改变自己。
"""
        }
        
        return ending_prompts.get(ending_type, ending_prompts["normal"])
    
    def _get_default_ending_story(self, ending_type: str, character_name: str) -> str:
        default_stories = {
            "perfect": f"""
时光荏苒，经历了无数的冒险与挑战，你与{character_name}终于走到了一起。

在那个特别的日子里，{character_name}微笑着对你说："谢谢你一直以来的陪伴，我愿意与你一起，走过未来的每一天。"

阳光洒在你们的身上，温暖而美好。这是属于你们的完美结局，也是新故事的开始。

💕 **恭喜达成完美结局！**
""",
            "harem": f"""
在这个充满可能性的世界里，你与{character_name}都建立了深厚的感情。

虽然这样的状况让你有些困扰，但每个人都在用自己的方式关心着你。或许，这就是所谓的"幸福的烦恼"吧。

未来的路还很长，你会如何选择呢？

🌸 **达成后宫结局**
""",
            "normal": """
故事似乎还没有结束。虽然你与角色们的关系还在发展中，但这正是生活的常态。

每一天都是新的开始，每一次相遇都可能改变命运。也许在未来的某一天，你会找到真正属于自己的幸福。

📖 **达成普通结局**
""",
            "lonely": """
独自走在熟悉的街道上，你开始思考：是不是应该更主动地去了解身边的人？

孤独并不可怕，可怕的是放弃改变的机会。也许，下一个转角，就会有新的相遇在等着你。

💔 **达成孤独结局**
"""
        }
        
        return default_stories.get(ending_type, default_stories["normal"])
    
    def _get_ending_description(self, ending_type: str, character_name: str) -> str:
        descriptions = {
            "perfect": f"与{character_name}达成了完美结局，两人携手共度余生。",
            "harem": "与多位角色保持了亲密的关系，享受着被爱包围的幸福。",
            "normal": "故事暂时告一段落，但未来还有无限可能。",
            "lonely": "未能与任何角色建立深厚的关系，需要重新审视自己。"
        }
        return descriptions.get(ending_type, "故事结束。")
    
    def _calculate_play_time(self, state: GameState) -> str:
        total_messages = len(state.messages)
        estimated_minutes = total_messages * 2
        
        if estimated_minutes < 60:
            return f"{estimated_minutes}分钟"
        else:
            hours = estimated_minutes // 60
            minutes = estimated_minutes % 60
            return f"{hours}小时{minutes}分钟"
    
    def save_ending(self, ending: GameEnding, save_id: int = 0) -> int:
        ending.save_id = save_id
        return self._db.save_ending(ending)
    
    def get_ending_statistics(self) -> Dict:
        all_endings = self._db.get_all_endings()
        
        stats = {
            "total": len(all_endings),
            "perfect": 0,
            "harem": 0,
            "normal": 0,
            "lonely": 0,
            "characters": {}
        }
        
        for ending in all_endings:
            stats[ending.ending_type] = stats.get(ending.ending_type, 0) + 1
            if ending.character_name:
                if ending.character_name not in stats["characters"]:
                    stats["characters"][ending.character_name] = 0
                stats["characters"][ending.character_name] += 1
        
        return stats
