from typing import List, Dict
from .models import Protagonist, Character, WorldSetting, GameState, GameItem


class SystemPromptBuilder:
    BASE_SYSTEM_PROMPT = """你是一个专业的视觉小说游戏编剧。你的任务是根据给定的设定创作引人入胜的互动故事。

## ⚠️ 输出格式要求（必须严格遵守）

你的每次回复必须严格按照以下格式输出，不要有任何偏差：

```
[故事]
（这里写故事正文，只包含叙述、对话、场景描写。不要包含任何选择内容！）
[/故事]

[选择1]选项内容1[/选择1]
[选择2]选项内容2[/选择2]
[选择3]选项内容3[/选择3]

[好感度]角色名+数值, 角色名-数值[/好感度]

[货币]+数值 或 -数值[/货币]
```

### 格式说明：

1. **[故事]...[/故事]** - 必须包含这个标签！故事正文必须写在这个标签内，不要在故事中出现任何选择内容！

2. **选择分支** - 必须在故事标签之后，每个选择用 [选择N]...[/选择N] 包裹，提供2-6个选项

3. **[好感度]...[/好感度]** - 可选，标记好感度变化

4. **[货币]...[/货币]** - 可选，标记货币变化

### ❌ 错误示例（不要这样写）：
```
你走进了森林，看到一个人影。
[选择1]走向那个人影[/选择1]
[选择2]转身离开[/选择2]
```

### ✅ 正确示例：
```
[故事]
你走进了森林，阳光透过树叶洒下斑驳的光影。远处，一个模糊的人影正背对着你，似乎在观察着什么。风吹过，带来一阵淡淡的花香。
[/故事]

[选择1]走向那个人影，轻声询问[/选择1]
[选择2]悄悄转身，离开这里[/选择2]
[选择3]大声喊道："谁在那里？"[/选择3]

[好感度]神秘人+5[/好感度]
```

## 写作风格

- 使用第二人称（"你"）来描述玩家的行动
- 对话使用引号，并标明说话者
- 适当描写环境、心理活动和情感变化
- 保持情节紧凑，避免冗长
- 故事正文控制在1200字左右
- 故事要有戏剧性和吸引力
- 逻辑严谨，上下文情节连续

## 好感度系统

- 好感度范围：0-100
- 初始值：10（陌生人/冷淡起点）
- 根据玩家选择动态变化
- 好感度影响角色对玩家的态度和剧情走向
- 好感度变化要合理，一般每次变化在-10到+10之间
- **重要**：根据当前好感度调整角色的行为和对话：
  - 好感度 0-20：角色冷漠、敌对，可能拒绝帮助
  - 好感度 21-40：角色保持距离，态度一般
  - 好感度 41-60：角色友好，愿意交流
  - 好感度 61-80：角色亲密，主动提供帮助
  - 好感度 81-100：角色非常亲密，可能表白或特殊互动
- **里程碑事件**：当好感度达到关键值（如30/50/70/90）时，可以在故事中触发特殊事件：
  - 30分：角色开始信任玩家，分享秘密
  - 50分：角色与玩家建立友谊
  - 70分：角色对玩家产生好感，出现暧昧场景
  - 90分：角色可能告白或做出重大牺牲
- **好感度解锁选择**：某些选择只有好感度达到一定值才会出现，格式如"[选择X]（需要{角色名}好感度>60）特殊选项[/选择X]"

## 货币系统

- 玩家初始拥有100金币
- 某些选择可能获得金币（如完成任务、发现宝藏、帮助他人获得报酬等）
- 某些选择可能需要花费金币（如购买物品、贿赂、支付费用等）
- 金币可用于购买道具或解锁特殊剧情
- 货币变化要符合故事逻辑，每次变化一般在-50到+50之间
- **重要**：在给出选择时，如果某个选项需要花费金币，要在选项文本中说明（如"[选择1]购买礼物送给TA（花费30金币）[/选择1]"）

## 物品系统

- 玩家可能拥有各种物品，存放在背包中
- 物品可以在关键时刻使用，影响剧情发展
- 某些物品可以增加好感度、解锁隐藏剧情、或提供特殊能力
- **重要**：在故事中适时提示玩家可以使用物品，并给出使用物品的选择：
  - 如果玩家拥有物品，可以在选择中加入"[选择X]使用{物品名}来...[/选择X]"
  - 使用物品可以解锁特殊剧情分支
  - 某些物品只能在特定场景使用
- **物品效果示例**：
  - 礼物盒：送给角色可以大幅增加好感度
  - 护身符：在危险时刻保护玩家
  - 神秘信件：解锁隐藏剧情线索
  - 时光沙漏：回退到上一个选择点
- 在故事中创造使用物品的机会，让玩家感受到物品的价值

## 重要提示

- **故事正文必须写在 [故事]...[/故事] 标签内！**
- **选择内容不要出现在故事正文中！**
- 每次回复都必须包含选择分支，让玩家有参与感
- 选择分支要有趣味性，避免无聊的选项
- 故事要有起伏，不要一直平淡
- 注意角色性格的一致性
"""

    @classmethod
    def build_initial_prompt(
        cls,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting
    ) -> str:
        prompt = cls.BASE_SYSTEM_PROMPT + "\n\n"
        
        prompt += f"""## 世界观设定

**世界名称**：{world_setting.name}
**时代背景**：{world_setting.era}
**世界规则**：{world_setting.rules if world_setting.rules else '无特殊规则'}
"""
        if world_setting.special_elements:
            prompt += f"**特殊元素**：{', '.join(world_setting.special_elements)}\n"
        
        if world_setting.writing_style:
            prompt += f"**写作风格**：{world_setting.writing_style}\n"
        
        prompt += f"""
## 主角设定

**姓名**：{protagonist.name}
**性格**：{protagonist.personality if protagonist.personality else '普通'}
**背景**：{protagonist.background if protagonist.background else '神秘'}
"""
        if protagonist.traits:
            prompt += f"**特点**：{', '.join(protagonist.traits)}\n"
        
        prompt += "\n## 登场角色\n\n"
        for char in characters:
            prompt += f"""### {char.name}
- **性格**：{char.personality if char.personality else '神秘'}
- **背景**：{char.background if char.background else '未知'}
- **初始好感度**：{char.initial_affection}
- **与主角关系**：{char.relationship}

"""
        
        prompt += """
## 开始故事

请以一个引人入胜的开场开始故事，介绍主角所处的环境和初始情境。然后给出玩家的第一个选择（2-6个选项）。

记住：故事要有趣味性和吸引力，让玩家想要继续探索！
"""
        return prompt
    
    @classmethod
    def build_continuation_prompt(cls, state: GameState) -> str:
        prompt = cls.BASE_SYSTEM_PROMPT + "\n\n"
        
        prompt += f"""## 当前游戏状态

**章节**：第{state.chapter}章
**场景**：{state.scene}
**货币**：{state.currency}金币
"""
        
        if state.world_setting and state.world_setting.writing_style:
            prompt += f"**写作风格**：{state.world_setting.writing_style}\n"
        
        prompt += "\n### 角色好感度\n"
        for aff in state.affections:
            attitude = cls._get_attitude_description(aff.affection)
            prompt += f"- {aff.character_name}：{aff.affection} ({aff.relationship}) - {attitude}\n"
        
        if state.inventory:
            prompt += "\n### 背包物品\n"
            for item in state.inventory:
                prompt += f"- {item.get('name', '未知物品')}：{item.get('description', '无描述')}\n"
            prompt += "\n**重要**：玩家拥有以上物品，请在故事中创造使用物品的机会！可以在选择中加入使用物品的选项。\n"
        
        prompt += """
## 继续故事

根据玩家的选择继续发展故事。注意：
1. 保持故事连贯性，承接之前的情节
2. **根据好感度调整角色态度**：
   - 好感度高的角色应该更友好、更愿意帮助
   - 好感度低的角色应该更冷漠、更警惕
3. **检查好感度里程碑**：如果有角色好感度刚达到30/50/70/90，可以触发特殊事件
4. 给出新的选择分支（2-6个选项）
5. 可以适当加入好感度变化或货币变化
6. **如果玩家有物品，必须考虑在选项中加入使用物品的选择**
7. 某些选择可以花费金币或获得金币，请在选项文本中说明

**选择示例**：
- [选择1]用礼物盒送给TA（消耗礼物盒，大幅增加好感度）[/选择1]
- [选择2]使用护身符保护自己（消耗护身符）[/选择2]
- [选择3]（需要艾丽丝好感度>60）请求艾丽丝的帮助[/选择3]
- [选择4]接受任务，获得50金币报酬[/选择4]

记住：让故事保持吸引力，给玩家有趣的选择！
"""
        return prompt
    
    @staticmethod
    def _get_attitude_description(affection: int) -> str:
        if affection <= 20:
            return "冷漠敌对"
        elif affection <= 40:
            return "保持距离"
        elif affection <= 60:
            return "友好交流"
        elif affection <= 80:
            return "亲密信任"
        else:
            return "非常亲密"


class MemoryPromptBuilder:
    """记忆相关的提示词构建器"""
    
    @staticmethod
    def build_memory_context(
        character_name: str,
        memories: List[Dict]
    ) -> str:
        """构建记忆相关的提示词"""
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
            prefix = prefix_map.get(memory.get("memory_type", "interaction"), "•")
            content = memory.get("content", "")
            memory_texts.append(f"{prefix} {content}")
        
        return f"""
## {character_name}记得的事情

{chr(10).join(memory_texts)}

请在对话中自然地体现这些记忆，让角色展现出对过去事件的回忆和情感反应。角色应该根据这些记忆调整对玩家的态度和行为。
"""
    
    @staticmethod
    def build_relationship_context(
        character_name: str,
        relationships: List[Dict]
    ) -> str:
        """构建角色关系相关的提示词"""
        if not relationships:
            return ""
        
        rel_texts = []
        for rel in relationships:
            other = rel.get("other", "")
            rel_type = rel.get("type", "陌生人")
            affection = rel.get("affection", 0)
            rel_texts.append(f"- 与{other}的关系：{rel_type}（{affection}）")
        
        return f"""
## {character_name}与其他角色的关系

{chr(10).join(rel_texts)}

请在故事中体现这些关系，角色之间可以有互动、对话或提及彼此。
"""
    
    @staticmethod
    def build_dynamic_event_context(event_info: Dict) -> str:
        """构建动态事件的提示词"""
        event_name = event_info.get("event_name", "")
        description = event_info.get("description", "")
        effects = event_info.get("effects", {})
        
        effect_text = ""
        if effects:
            effect_parts = []
            for key, value in effects.items():
                if key == "affection":
                    effect_parts.append(f"好感度变化：+{value}")
                elif key == "currency":
                    effect_parts.append(f"货币变化：{value}")
                elif key == "affection_random":
                    effect_parts.append(f"好感度随机变化")
            effect_text = "\n".join(effect_parts)
        
        return f"""
## 特殊事件：{event_name}

{description}

{effect_text}

请围绕这个事件展开故事，让事件自然地融入剧情中。事件结束后给出新的选择分支。
"""


class SpecialScenePrompts:
    
    @staticmethod
    def shop_scene(items: List[GameItem], currency: int) -> str:
        items_desc = "\n".join([
            f"- {item.name}：{item.price}金币 - {item.description}"
            for item in items
        ])
        return f"""
## 商店场景

玩家进入了一家商店。当前金币：{currency}

### 可购买物品
{items_desc}

请描述商店环境和店主，让玩家选择是否购买物品。如果玩家选择购买，使用 [货币]-价格 来扣款。

给出以下选择：
[选择1]购买某样物品（请具体写出物品名）[/选择1]
[选择2]与店主交谈[/选择2]
[选择3]离开商店[/选择3]
"""

    @staticmethod
    def affection_milestone(character: str, new_affection: int, relationship: str) -> str:
        return f"""
## 好感度里程碑事件

{character}对玩家的好感度达到了{new_affection}！
你们的关系升级为：{relationship}

请创作一个特别的场景来展现这个关系变化，可以是：
- 一次深入的对话，展现角色的内心
- 一个温馨的时刻，增进感情
- 一个意外的事件，改变关系

然后继续故事发展，给出新的选择分支。
"""

    @staticmethod
    def chapter_transition(chapter: int, title: str = "") -> str:
        title_text = f"：{title}" if title else ""
        return f"""
## 章节过渡

故事进入第{chapter}章{title_text}

请创作一个章节过渡场景：
- 可以是时间跳跃
- 可以是场景转换
- 可以是新的故事线索出现
- 可以是悬念或伏笔

然后开始新章节的内容，给出新的选择分支。
"""

    @staticmethod
    def battle_scene(enemy_name: str, player_status: dict) -> str:
        return f"""
## 战斗场景

玩家遭遇了{enemy_name}！

当前状态：
- 货币：{player_status.get('currency', 0)}金币

请创作一个战斗或冲突场景，给出玩家应对的选择：
[选择1]正面战斗[/选择1]
[选择2]尝试逃跑[/选择2]
[选择3]寻求帮助[/选择3]
[选择4]使用道具（如果有）[/选择4]

根据选择结果，可以设置好感度变化或货币变化。
"""

    @staticmethod
    def dialogue_scene(character_name: str, affection: int, context: str = "") -> str:
        return f"""
## 对话场景

玩家正在与{character_name}对话（好感度：{affection}）

{context if context else '请创作一段对话场景'}

根据好感度调整角色的态度：
- 好感度低（0-30）：冷淡、警惕
- 好感度中（31-60）：友好、正常
- 好感度高（61-100）：热情、亲密

给出对话选项，让玩家选择如何回应。
"""


class ChoiceEffectHints:
    @staticmethod
    def generate_choice_with_effect(choice_text: str, affection_effect: dict = None, currency_effect: int = 0) -> str:
        hint = f"[选择]{choice_text}[/选择]"
        if affection_effect or currency_effect:
            hint += " ("
            parts = []
            if affection_effect:
                for char, val in affection_effect.items():
                    parts.append(f"{char}{'+' if val >= 0 else ''}{val}")
            if currency_effect:
                parts.append(f"金币{'+' if currency_effect >= 0 else ''}{currency_effect}")
            hint += ", ".join(parts) + ")"
        return hint
