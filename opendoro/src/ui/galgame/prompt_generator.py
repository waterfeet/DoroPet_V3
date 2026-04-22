import json
import re
from typing import Dict, Optional, Callable
from PyQt5.QtCore import QThread, pyqtSignal

from .models import Protagonist, Character, WorldSetting
from src.core.logger import logger


GENRE_CATEGORIES = {
    "fantasy": {
        "name": "东方玄幻",
        "description": "基于东方元素的奇幻世界，有独立的修炼体系",
        "elements": ["修炼体系", "特殊体质", "炼丹", "符咒", "炼器", "秘境", "宗门", "家族"],
        "character_archetypes": ["炼药师", "家族成员", "符咒", "宗门长老", "仇敌"]
    },
    "urban": {
        "name": "都市",
        "description": "现代都市生活，贴近现实的故事",
        "elements": ["职场", "日常生活", "人际关系", "现代科技"],
        "character_archetypes": ["上班族", "学生", "企业家", "艺术家"]
    },
    "school": {
        "name": "校园",
        "description": "学校环境中的青春故事",
        "elements": ["青春", "考试", "社团活动", "恋爱", "友情"],
        "character_archetypes": ["优等生", "不良少年", "图书委员", "学生会主席", "转学生"]
    },
    "isekai": {
        "name": "异世界",
        "description": "从现实世界穿越到异世界",
        "elements": ["穿越", "异世界", "转生", "冒险", "新世界"],
        "character_archetypes": ["勇者", "魔王", "女神", "公主", "冒险者"]
    },
    "scifi": {
        "name": "科幻",
        "description": "未来科技与宇宙探索",
        "elements": ["太空", "机器人", "AI", "未来城市", "外星文明"],
        "character_archetypes": ["宇航员", "科学家", "AI助手", "外星人", "赛博朋克"]
    },
    "historical": {
        "name": "历史",
        "description": "基于历史背景的故事",
        "elements": ["古代", "宫廷", "战争", "武侠", "朝堂"],
        "character_archetypes": ["将军", "谋士", "皇帝", "江湖侠客", "宫女"]
    },
    "horror": {
        "name": "恐怖",
        "description": "惊悚与恐怖的氛围",
        "elements": ["幽灵", "诅咒", "密室", "悬疑", "超自然"],
        "character_archetypes": ["侦探", "灵媒", "幸存者", "诅咒者"]
    },
    "romance": {
        "name": "恋爱",
        "description": "以浪漫恋爱为主线",
        "elements": ["约会", "告白", "误会", "重逢", "甜蜜"],
        "character_archetypes": ["青梅竹马", "天降系", "傲娇", "温柔系"]
    },
    "mystery": {
        "name": "推理",
        "description": "解谜与推理的故事",
        "elements": ["案件", "线索", "推理", "反转", "真相"],
        "character_archetypes": ["侦探", "助手", "嫌疑人", "幕后黑手"]
    },
    "adventure": {
        "name": "冒险",
        "description": "充满未知的冒险旅程",
        "elements": ["探索", "寻宝", "解谜", "战斗", "成长"],
        "character_archetypes": ["冒险家", "向导", "商人", "反派", "神秘人"]
    }
}


WRITING_STYLES = {
    "light_humorous": {
        "name": "轻松诙谐",
        "description": "幽默风趣，氛围轻松愉快",
        "keywords": ["搞笑", "吐槽", "轻松", "欢乐", "日常"],
        "tone": "轻快活泼，适当使用吐槽和玩笑"
    },
    "tragic_heavy": {
        "name": "悲情沉重",
        "description": "氛围沉重，情感深刻",
        "keywords": ["悲伤", "痛苦", "挣扎", "救赎", "命运"],
        "tone": "沉重严肃，注重情感描写"
    },
    "romantic_sweet": {
        "name": "浪漫甜蜜",
        "description": "充满浪漫气息，甜蜜温馨",
        "keywords": ["恋爱", "心动", "甜蜜", "温馨", "幸福"],
        "tone": "温柔甜美，注重心理描写"
    },
    "dark_gothic": {
        "name": "黑暗哥特",
        "description": "阴郁黑暗，充满神秘感",
        "keywords": ["黑暗", "死亡", "诅咒", "神秘", "禁忌"],
        "tone": "阴暗神秘，氛围压抑"
    },
    "epic_grand": {
        "name": "史诗宏大",
        "description": "格局宏大，气势磅礴",
        "keywords": ["命运", "宿命", "战争", "英雄", "传说"],
        "tone": "庄严宏大，注重世界观构建"
    },
    "comedic_parody": {
        "name": "喜剧恶搞",
        "description": "戏仿经典，充满梗和吐槽",
        "keywords": ["恶搞", "玩梗", "戏仿", "无厘头"],
        "tone": "荒诞搞笑，打破第四面墙"
    },
    "mysterious_suspense": {
        "name": "悬疑神秘",
        "description": "充满悬念，让人好奇",
        "keywords": ["谜团", "悬念", "反转", "阴谋"],
        "tone": "悬疑紧张，不断抛出疑问"
    },
    "slice_of_life": {
        "name": "日常治愈",
        "description": "温馨日常，治愈心灵",
        "keywords": ["日常", "治愈", "温暖", "平淡", "幸福"],
        "tone": "温暖治愈，注重细节描写"
    },
    "action_thriller": {
        "name": "动作热血",
        "description": "紧张刺激，热血沸腾",
        "keywords": ["战斗", "热血", "成长", "羁绊", "胜利"],
        "tone": "紧张刺激，充满激情"
    },
    "random": {
        "name": "纯随机",
        "description": "由AI自由发挥，不受限制",
        "keywords": ["随机", "创意", "未知"],
        "tone": "AI自由决定"
    }
}


PROMPT_GENERATOR_SYSTEM = """你是一个专业的视觉小说游戏设定师。你的任务是根据给定的题材，创作完整的游戏角色和世界观设定。

## 输出格式要求

你的回复必须严格按照以下 JSON 格式：

```json
{
    "protagonist": {
        "name": "主角名称",
        "personality": "主角性格描述（2-4 个特点）",
        "background": "主角背景故事（1-2 句话）",
        "traits": ["特点 1", "特点 2", "特点 3"]
    },
    "characters": [
        {
            "name": "角色名称",
            "personality": "性格描述（2-4 个特点）",
            "background": "背景故事（1-2 句话）",
            "initial_affection": 10,
            "relationship": "与主角的关系（如：同学、青梅竹马、对手等）"
        }
    ],
    "world_setting": {
        "name": "世界观名称",
        "era": "时代背景",
        "rules": "世界规则描述（2-3 句话）",
        "special_elements": ["元素 1", "元素 2", "元素 3"],
        "writing_style": "写作风格说明（描述故事叙述的语气和方式，如：轻松幽默、沉重悲伤、浪漫甜蜜等）"
    }
}
```

## 创作要求

1. **角色数量**：必须生成 3-5 个配角
2. **名称风格**：根据题材选择符合风格的名称
3. **性格多样**：每个角色应该有独特的性格特点，避免重复
4. **背景合理**：背景故事要与世界观相符，逻辑自洽
5. **好感度合理**：根据关系设置合理的初始好感度（**0-10 之间，从陌生人开始**）
6. **世界观完整**：包含足够的设定元素来支撑故事
7. **创意性**：避免过于模板化的设定，要有独特性

## 重要说明

- **题材**：决定世界观、角色类型、故事背景等核心设定
- **写作风格**：只影响故事叙述的语气和方式，不影响世界观和角色设定本身
- 例如：选择"搞笑"风格，世界观应该是正常的玄幻/都市等设定，只是叙述方式幽默；而不是创造一个"由搞笑能量驱动"的世界
- 例如：选择"黑暗哥特"风格，世界观依然可以是校园或都市，只是叙述氛围阴暗
- **writing_style 字段**：请在 world_setting 中填写写作风格说明，用于后续故事生成时参考

## 好感度设置指南

**重要：所有角色的初始好感度必须设置在 0-10 之间！**

- 0-5: 敌对关系（如：仇敌、竞争对手）
- 6-10: 陌生或普通关系（如：同学、同事、邻居）
- 不要设置超过 10 的好感度，让玩家有成长体验

## 注意事项

- 确保 JSON 格式正确，可以被解析
- 所有内容使用中文
- 角色名称要有创意且符合题材
- 性格和背景要有深度，不要过于简单
"""


def build_prompt_generator_user_prompt(
    genre: str,
    style: str,
    custom_requirements: str = ""
) -> str:
    genre_info = GENRE_CATEGORIES.get(genre, {})
    style_info = WRITING_STYLES.get(style, {})
    
    genre_name = genre_info.get('name', genre)
    genre_desc = genre_info.get('description', '')
    genre_elements = genre_info.get('elements', [])
    genre_archetypes = genre_info.get('character_archetypes', [])
    
    style_name = style_info.get('name', style)
    style_desc = style_info.get('description', '')
    
    prompt = f"""请根据以下要求创作视觉小说游戏设定：

## 题材信息（决定世界观和角色类型）
- **题材分类**：{genre_name}
- **题材描述**：{genre_desc}
- **典型元素**：{', '.join(genre_elements)}
- **常见角色原型**：{', '.join(genre_archetypes)}

## 写作风格（仅影响故事叙述方式，不影响世界观设定）
- **风格名称**：{style_name}
- **风格说明**：{style_desc}
- **注意**：此风格仅用于后续故事叙述的语气参考，当前生成世界观和角色设定时请忽略风格影响，专注于题材本身
"""
    
    if custom_requirements:
        prompt += f"\n## 额外要求\n{custom_requirements}\n"
    
    prompt += """
请生成完整的主角设定、配角设定（3-5个）和世界观设定。
确保设定有趣、有创意，严格基于题材而非写作风格来构建世界观。

现在请开始创作，返回JSON格式。"""
    
    return prompt


class PromptGenerationWorker(QThread):
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, provider_manager, genre: str, style: str,
                 custom_requirements: str = "", model_id: str = None):
        super().__init__()
        self.provider_manager = provider_manager
        self.genre = genre
        self.style = style
        self.custom_requirements = custom_requirements
        self.model_id = model_id
        self._is_stopped = False
    
    def run(self):
        try:
            provider = self.provider_manager.get_llm_provider(self.model_id)
            if not provider:
                self.error_occurred.emit("未找到可用的 AI 模型")
                return
            
            system_prompt = PROMPT_GENERATOR_SYSTEM
            user_prompt = build_prompt_generator_user_prompt(
                self.genre, self.style, self.custom_requirements
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            logger.info(f"Generating config with genre={self.genre}, style={self.style}")
            
            response = provider.chat(messages, temperature=0.9)
            
            if self._is_stopped:
                return
            
            if response and response.content:
                result = self._parse_response(response.content)
                self.generation_complete.emit(result)
            else:
                self.error_occurred.emit("AI生成失败，未获得有效响应")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            self.error_occurred.emit(f"JSON解析失败：{str(e)}")
        except Exception as e:
            logger.error(f"Generation error: {e}")
            self.error_occurred.emit(f"生成失败：{str(e)}")
    
    def _parse_response(self, response: str) -> Dict:
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response
        
        return json.loads(json_str)
    
    def stop(self):
        self._is_stopped = True


class PromptGenerator:
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
    
    def generate_config(
        self,
        genre: str,
        style: str,
        custom_requirements: str = "",
        model_id: str = None
    ) -> PromptGenerationWorker:
        worker = PromptGenerationWorker(
            self.provider_manager,
            genre,
            style,
            custom_requirements,
            model_id
        )
        return worker
    
    @staticmethod
    def parse_generated_config(data: Dict):
        protagonist = Protagonist.from_dict(data.get('protagonist', {}))
        
        characters_data = data.get('characters', [])
        characters = [Character.from_dict(c) for c in characters_data]
        
        world_setting = WorldSetting.from_dict(data.get('world_setting', {}))
        
        return protagonist, characters, world_setting
