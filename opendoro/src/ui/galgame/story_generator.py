from typing import Generator, Dict, List, Optional
import json
import re
from src.provider.manager import ProviderManager
from src.core.logger import logger
from .models import Protagonist, Character, WorldSetting, GameState, StoryCache
from .prompts import SystemPromptBuilder
from .response_parser import ResponseParser
from .story_cache_manager import StoryCacheManager


class StoryGenerator:
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        self.prompt_builder = SystemPromptBuilder()
        self.max_context_messages = 20
    
    def generate_story_start(
        self,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        system_prompt = self.prompt_builder.build_initial_prompt(
            protagonist, characters, world_setting
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始故事的开场，并给出玩家的选择。"}
        ]
        
        logger.info("Starting story generation...")
        full_response = ""
        
        try:
            for response in provider.chat_stream(messages, temperature=0.8, max_tokens=2000):
                if response.content:
                    full_response += response.content
                    yield response.content
        except Exception as e:
            logger.error(f"Error during story generation: {e}")
            raise
        
        parsed = ResponseParser.parse(full_response)
        logger.info(f"Story generation complete. Generated {len(parsed['choices'])} choices.")
        return parsed
    
    def generate_next_scene(
        self,
        context: List[Dict],
        choice: str,
        current_state: GameState,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        system_prompt = self.prompt_builder.build_continuation_prompt(current_state)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        recent_context = context[-self.max_context_messages:] if len(context) > self.max_context_messages else context
        messages.extend(recent_context)
        
        messages.append({
            "role": "user", 
            "content": f"玩家选择：{choice}\n\n请继续故事发展，并给出新的选择。"
        })
        
        logger.info(f"Generating next scene for choice: {choice[:50]}...")
        full_response = ""
        
        try:
            for response in provider.chat_stream(messages, temperature=0.8, max_tokens=2000):
                if response.content:
                    full_response += response.content
                    yield response.content
        except Exception as e:
            logger.error(f"Error during scene generation: {e}")
            raise
        
        parsed = ResponseParser.parse(full_response)
        logger.info(f"Scene generation complete. Generated {len(parsed['choices'])} choices.")
        return parsed
    
    def generate_special_scene(
        self,
        scene_type: str,
        current_state: GameState,
        extra_params: Dict = None,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        from .prompts import SpecialScenePrompts
        
        extra_params = extra_params or {}
        
        if scene_type == "shop":
            from .database import GalgameDatabase
            db = GalgameDatabase()
            items = db.get_items()
            special_prompt = SpecialScenePrompts.shop_scene(items, current_state.currency)
        elif scene_type == "affection_milestone":
            special_prompt = SpecialScenePrompts.affection_milestone(
                extra_params.get('character', ''),
                extra_params.get('new_affection', 50),
                extra_params.get('relationship', '朋友')
            )
        elif scene_type == "chapter_transition":
            special_prompt = SpecialScenePrompts.chapter_transition(
                extra_params.get('chapter', 1),
                extra_params.get('title', '')
            )
        else:
            raise ValueError(f"Unknown scene type: {scene_type}")
        
        system_prompt = SystemPromptBuilder.BASE_SYSTEM_PROMPT + "\n\n" + special_prompt
        
        messages = [{"role": "system", "content": system_prompt}]
        
        logger.info(f"Generating special scene: {scene_type}")
        full_response = ""
        
        try:
            for response in provider.chat_stream(messages, temperature=0.8, max_tokens=2000):
                if response.content:
                    full_response += response.content
                    yield response.content
        except Exception as e:
            logger.error(f"Error during special scene generation: {e}")
            raise
        
        parsed = ResponseParser.parse(full_response)
        return parsed
    
    def build_context_from_messages(self, messages: List) -> List[Dict]:
        context = []
        for msg in messages:
            role = "assistant" if msg.role.value == "narrator" else "user"
            context.append({
                "role": role,
                "content": msg.content
            })
            if msg.selected_choice:
                for choice in msg.choices:
                    if choice.id == msg.selected_choice:
                        context.append({
                            "role": "user",
                            "content": f"玩家选择：{choice.text}"
                        })
                        break
        return context
    
    def generate_story_plan(
        self,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting,
        model_id: Optional[str] = None
    ) -> StoryCache:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        char_info = "\n".join([
            f"- {c.name}：{c.personality}，{c.background}"
            for c in characters
        ])
        
        prompt = f"""你是一个专业的视觉小说游戏策划师。请根据以下世界观和角色设定，创作一个完整的故事框架。

## 世界观设定
名称：{world_setting.name}
时代：{world_setting.era}
规则：{world_setting.rules}
特殊元素：{', '.join(world_setting.special_elements)}

## 主角设定
名称：{protagonist.name}
性格：{protagonist.personality}
背景：{protagonist.background}
特点：{', '.join(protagonist.traits)}

## 登场角色
{char_info}

## 输出格式（严格JSON）

```json
{{
    "story_synopsis": "故事总体大纲（200-300字，描述整个故事的主线、核心冲突和走向）",
    "world_analysis": "世界观深度分析（100-200字，挖掘世界观的潜在冲突和故事空间）",
    "character_analysis": "角色关系分析（100-200字，分析角色间的潜在互动和冲突）",
    "first_chapter": {{
        "chapter_name": "第一章名称（4-8个字，要有文学感）",
        "chapter_outline": "第一章大纲（100-200字，描述本章的主要情节和冲突）",
        "opening_setting": "开场设定（100-150字，描述故事开场的具体场景、氛围和切入点）"
    }},
    "key_plot_points": ["关键情节1", "关键情节2", "关键情节3"],
    "foreshadowing": ["伏笔1", "伏笔2"]
}}
```

请确保大纲有足够的深度和张力，角色关系有发展空间。只输出JSON，不要有其他内容。"""

        messages = [{"role": "user", "content": prompt}]
        
        logger.info("Generating story plan...")
        
        try:
            response = provider.chat(messages, temperature=0.9, max_tokens=2000)
            if not response or not response.content:
                raise ValueError("Empty response from AI")
            
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.content
            
            plan = json.loads(json_str)
            
            cache = StoryCacheManager.create_empty_cache()
            StoryCacheManager.update_after_story_plan(cache, plan)
            
            logger.info(f"Story plan generated. First chapter: {cache.current_chapter.chapter_name}")
            return cache
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError(f"Failed to parse story plan: {e}")
        except Exception as e:
            logger.error(f"Error during story plan generation: {e}")
            raise
    
    def generate_chapter_summary(
        self,
        chapter_messages: List[str],
        story_cache: StoryCache,
        model_id: Optional[str] = None
    ) -> Dict:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        chapter_content = "\n\n".join(chapter_messages)
        
        prompt = f"""你是一个专业的故事编辑。请对以下章节内容进行概括和提炼。

## 本章内容
{chapter_content}

## 本章大纲
{story_cache.current_chapter.chapter_outline}

## 输出格式（严格JSON）

```json
{{
    "chapter_summary": "本章摘要（100-150字，概括本章核心事件和发展）",
    "key_events": ["关键事件1", "关键事件2", "关键事件3"],
    "character_developments": "角色发展变化（50-100字）",
    "cliffhanger": "本章结尾悬念/钩子（30-50字，为下一章铺垫）",
    "new_foreshadowing": ["新伏笔1", "新伏笔2"],
    "resolved_foreshadowing": ["已回收的伏笔1"]
}}
```

只输出JSON，不要有其他内容。"""

        messages = [{"role": "user", "content": prompt}]
        
        logger.info(f"Generating chapter {story_cache.current_chapter.chapter_number} summary...")
        
        try:
            response = provider.chat(messages, temperature=0.7, max_tokens=1000)
            if not response or not response.content:
                raise ValueError("Empty response from AI")
            
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response.content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.content
            
            summary = json.loads(json_str)
            logger.info(f"Chapter summary generated.")
            return summary
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError(f"Failed to parse chapter summary: {e}")
        except Exception as e:
            logger.error(f"Error during chapter summary generation: {e}")
            raise
    
    def generate_next_chapter_plan(
        self,
        story_cache: StoryCache,
        current_state: GameState,
        model_id: Optional[str] = None
    ) -> Dict:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        prev_summaries = StoryCacheManager.get_previous_summaries_text(story_cache)
        key_plots = StoryCacheManager.get_key_plots_text(story_cache)
        foreshadowing = StoryCacheManager.get_foreshadowing_text(story_cache)
        
        aff_text = ""
        for aff in current_state.affections:
            aff_text += f"- {aff.character_name}：{aff.affection}（{aff.relationship}）\n"
        
        next_chapter_num = story_cache.current_chapter.chapter_number + 1
        
        prompt = f"""你是一个专业的视觉小说游戏策划师。请根据前文发展，规划下一章的内容。

## 故事总体大纲
{story_cache.story_synopsis}

## 已完成章节摘要
{prev_summaries}

## 当前角色状态
{aff_text if aff_text else "暂无角色好感度数据"}

## 关键情节节点
{key_plots}

## 待回收伏笔
{foreshadowing}

## 输出格式（严格 JSON，不要有其他内容）

{{
    "chapter_name": "第{next_chapter_num}章名称（4-8 个字，要有文学感）",
    "chapter_outline": "本章大纲（100-200 字，描述本章的主要情节和冲突）",
    "opening_setting": "开场设定（100-150 字，描述本章开场的具体场景和氛围）"
}}

请确保新章节与故事大纲方向一致，承接上一章的悬念，推进核心冲突。只输出 JSON 格式，不要用 markdown 代码块包裹。"""

        messages = [{"role": "user", "content": prompt}]
        
        logger.info(f"Generating chapter {next_chapter_num} plan...")
        
        try:
            response = provider.chat(messages, temperature=0.9, max_tokens=1000)
            if not response or not response.content:
                raise ValueError("Empty response from AI")
            
            # 尝试多种 JSON 提取方式
            json_str = response.content.strip()
            
            # 1. 尝试提取 markdown 代码块中的 JSON
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
            if json_match:
                json_str = json_match.group(1).strip()
            
            # 2. 如果还是包含非 JSON 内容，尝试找到第一个 { 和最后一个 }
            if not json_str.startswith('{'):
                start_idx = json_str.find('{')
                end_idx = json_str.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    json_str = json_str[start_idx:end_idx + 1]
            
            plan = json.loads(json_str)
            logger.info(f"Chapter {next_chapter_num} plan generated: {plan.get('chapter_name', '')}")
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError(f"Failed to parse chapter plan: {e}")
        except Exception as e:
            logger.error(f"Error during chapter plan generation: {e}")
            raise
    
    def generate_chapter_opening(
        self,
        story_cache: StoryCache,
        current_state: GameState,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        system_prompt = SystemPromptBuilder.BASE_SYSTEM_PROMPT
        
        prev_summaries = StoryCacheManager.get_previous_summaries_text(story_cache)
        key_plots = StoryCacheManager.get_key_plots_text(story_cache)
        foreshadowing = StoryCacheManager.get_foreshadowing_text(story_cache)
        
        chapter = story_cache.current_chapter
        
        user_prompt = f"""## 故事大纲
{story_cache.story_synopsis}

## 当前章节：第{chapter.chapter_number}章 - {chapter.chapter_name}
章节大纲：{chapter.chapter_outline}

## 开场设定
{chapter.opening_setting}

## 角色关系
{story_cache.character_analysis}

## 前情提要
{prev_summaries}

## 关键情节节点
{key_plots}

## 待回收伏笔
{foreshadowing}

请根据以上设定，创作第{chapter.chapter_number}章的开场。严格遵循开场设定中的场景和氛围，自然地引入主角和关键角色。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info(f"Generating chapter {chapter.chapter_number} opening...")
        full_response = ""
        
        try:
            for response in provider.chat_stream(messages, temperature=0.8, max_tokens=2000):
                if response.content:
                    full_response += response.content
                    yield response.content
        except Exception as e:
            logger.error(f"Error during chapter opening generation: {e}")
            raise
        
        parsed = ResponseParser.parse(full_response)
        logger.info(f"Chapter opening complete. Generated {len(parsed['choices'])} choices.")
        return parsed
    
    def generate_chapter_continuation(
        self,
        context: List[Dict],
        choice: str,
        story_cache: StoryCache,
        current_state: GameState,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        system_prompt = SystemPromptBuilder.BASE_SYSTEM_PROMPT
        
        chapter = story_cache.current_chapter
        prev_summaries = StoryCacheManager.get_previous_summaries_text(story_cache)
        key_plots = StoryCacheManager.get_key_plots_text(story_cache)
        foreshadowing = StoryCacheManager.get_foreshadowing_text(story_cache)
        
        aff_text = ""
        for aff in current_state.affections:
            aff_text += f"- {aff.character_name}：{aff.affection}（{aff.relationship}）\n"
        
        chapter_prompt = f"""## 故事大纲
{story_cache.story_synopsis}

## 当前章节：第{chapter.chapter_number}章 - {chapter.chapter_name}
章节大纲：{chapter.chapter_outline}

## 前情提要
{prev_summaries}

## 当前游戏状态
章节：第{chapter.chapter_number}章
货币：{current_state.currency}金币

### 角色好感度
{aff_text if aff_text else "暂无角色好感度数据"}

### 关键情节节点
{key_plots}

### 待回收伏笔
{foreshadowing}"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": chapter_prompt})
        
        recent_context = context[-self.max_context_messages:] if len(context) > self.max_context_messages else context
        messages.extend(recent_context)
        
        messages.append({
            "role": "user",
            "content": f"玩家选择：{choice}\n\n请继续创作当前章节的内容。注意：\n1. 保持与章节大纲的一致性\n2. 承接前文情节，逻辑连贯\n3. 适当推进章节核心冲突\n4. 给出新的选择分支"
        })
        
        logger.info(f"Generating chapter continuation for choice: {choice[:50]}...")
        full_response = ""
        
        try:
            for response in provider.chat_stream(messages, temperature=0.8, max_tokens=2000):
                if response.content:
                    full_response += response.content
                    yield response.content
        except Exception as e:
            logger.error(f"Error during chapter continuation generation: {e}")
            raise
        
        parsed = ResponseParser.parse(full_response)
        logger.info(f"Chapter continuation complete. Generated {len(parsed['choices'])} choices.")
        return parsed


class StoryContextManager:
    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self.context: List[Dict] = []
    
    def add_message(self, role: str, content: str):
        self.context.append({"role": role, "content": content})
        
        if len(self.context) > self.max_messages * 2:
            self._compress_context()
    
    def add_user_choice(self, choice: str):
        self.context.append({"role": "user", "content": f"玩家选择：{choice}"})
    
    def add_assistant_response(self, content: str):
        self.context.append({"role": "assistant", "content": content})
    
    def get_context(self) -> List[Dict]:
        return self.context[-self.max_messages:]
    
    def _compress_context(self):
        if len(self.context) <= self.max_messages:
            return
        
        keep_count = self.max_messages // 2
        self.context = self.context[-keep_count:]
        
        summary = "（之前的剧情已略过，故事继续...）"
        self.context.insert(0, {"role": "system", "content": summary})
    
    def clear(self):
        self.context = []
    
    def set_context(self, context: List[Dict]):
        self.context = context
