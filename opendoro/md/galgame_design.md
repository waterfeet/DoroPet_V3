# Galgame 功能设计方案

## 一、功能概述

### 1.1 功能定位
Galgame模块是一个基于AI大语言模型的互动式视觉小说游戏系统。玩家可以通过配置角色、世界观和提示词，由AI动态生成故事情节，并通过选择分支来影响故事走向。系统支持好感度系统、货币体系和商品系统，提供沉浸式的互动体验。

### 1.2 核心特性
- **动态故事生成**：基于AI实时生成故事内容，每次游戏体验都独一无二
- **分支选择系统**：AI智能生成2-6个选择分支，玩家选择影响故事走向
- **好感度系统**：追踪玩家与各角色的关系进展
- **经济系统**：货币获取与消费机制，增加游戏深度
- **商品系统**：可购买道具影响游戏进程
- **配置灵活**：支持自定义主角、角色、世界观和语言模型

---

## 二、UI设计

### 2.1 页面入口
在主窗口左侧导航栏添加新的菜单项：
- 图标：`FluentIcon.GAME` 或 `FluentIcon.BOOK`
- 名称：`Galgame`
- 位置：在"音乐播放"和"模型配置"之间

### 2.2 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    顶部功能区 (固定)                   │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │
│  │  │ 主角配置  │ │ 角色配置  │ │ 世界观   │ │ 模型   │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │
│  │                                          ┌────────┐  │    │
│  │                                          │ 开始   │  │    │
│  │                                          └────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                      │    │
│  │                                                      │    │
│  │                  故事消息流区域                        │    │
│  │                   (可滚动)                            │    │
│  │                                                      │    │
│  │  ┌────────────────────────────────────────────────┐ │    │
│  │  │ [角色名] 故事文本内容...                         │ │    │
│  │  │ 好感度变化提示 / 获得货币提示                    │ │    │
│  │  └────────────────────────────────────────────────┘ │    │
│  │                                                      │    │
│  │  ┌────────────────────────────────────────────────┐ │    │
│  │  │ [选择按钮区域]                                  │ │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐       │ │    │
│  │  │  │ 选择1    │ │ 选择2    │ │ 选择3    │       │ │    │
│  │  │  └──────────┘ └──────────┘ └──────────┘       │ │    │
│  │  └────────────────────────────────────────────────┘ │    │
│  │                                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  底部状态栏: 好感度 | 货币 | 当前章节                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 组件详细设计

#### 2.3.1 顶部功能区 (TopConfigPanel)

```python
class TopConfigPanel(QFrame):
    """
    顶部配置面板，包含：
    - 主角提示词配置按钮
    - 角色提示词配置按钮  
    - 世界观背景配置按钮
    - 模型选择下拉框
    - 开始按钮
    """
```

**配置弹窗设计**：

1. **主角配置弹窗 (ProtagonistConfigDialog)**
   - 主角名称输入
   - 主角性格描述
   - 主角背景故事
   - 主角特殊能力/特点

2. **角色配置弹窗 (CharacterConfigDialog)**
   - 角色列表（可添加多个角色）
   - 每个角色包含：
     - 角色名称
     - 角色头像（可选）
     - 性格特点
     - 背景故事
     - 初始好感度
     - 与主角的关系

3. **世界观配置弹窗 (WorldConfigDialog)**
   - 世界观名称
   - 时代背景
   - 世界规则/设定
   - 特殊元素（魔法、科技等）

4. **模型选择**
   - 下拉框选择已配置的LLM模型
   - 复用现有的ProviderManager

#### 2.3.2 故事消息流区域 (StoryFlowArea)

```python
class StoryFlowArea(ScrollArea):
    """
    可滚动的故事内容显示区域
    """
```

**消息卡片设计 (StoryMessageCard)**：
```
┌────────────────────────────────────────────┐
│ [角色头像] [角色名]                    时间 │
├────────────────────────────────────────────┤
│                                            │
│ 故事文本内容...                            │
│ 支持Markdown渲染                           │
│                                            │
├────────────────────────────────────────────┤
│ 💝 好感度 +5  |  💰 获得 100 金币          │
└────────────────────────────────────────────┘
```

**选择按钮区域 (ChoiceButtonsPanel)**：
```python
class ChoiceButtonsPanel(QFrame):
    """
    AI生成的选择按钮组
    - 动态生成2-6个按钮
    - 按钮样式统一
    - 点击后触发后续剧情生成
    """
```

#### 2.3.3 底部状态栏 (StatusBar)

```python
class GalgameStatusBar(QFrame):
    """
    显示当前游戏状态：
    - 各角色好感度（可展开查看详情）
    - 当前货币数量
    - 当前章节/场景
    """
```

### 2.4 主题适配
- 支持深色/浅色主题切换
- 复用项目现有的主题系统
- 消息卡片根据角色类型使用不同颜色

---

## 三、数据管理

### 3.1 数据库设计

#### 3.1.1 新增数据库表

在现有数据库基础上，新增 `GalgameDatabase`：

```sql
-- 游戏存档表
CREATE TABLE IF NOT EXISTS galgame_saves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 存档名称
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 游戏配置表
CREATE TABLE IF NOT EXISTS galgame_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 配置名称
    protagonist TEXT,                      -- 主角配置 (JSON)
    characters TEXT,                       -- 角色配置 (JSON)
    world_setting TEXT,                    -- 世界观配置 (JSON)
    model_id TEXT,                         -- 使用的模型ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 游戏状态表
CREATE TABLE IF NOT EXISTS galgame_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id INTEGER,                       -- 关联存档
    chapter INTEGER DEFAULT 1,             -- 当前章节
    scene TEXT,                            -- 当前场景
    currency INTEGER DEFAULT 0,            -- 货币数量
    inventory TEXT,                        -- 背包物品 (JSON)
    story_context TEXT,                    -- 故事上下文 (JSON)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(save_id) REFERENCES galgame_saves(id)
);

-- 角色好感度表
CREATE TABLE IF NOT EXISTS galgame_affections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER,                      -- 关联游戏状态
    character_name TEXT NOT NULL,          -- 角色名称
    affection INTEGER DEFAULT 50,          -- 好感度 (0-100)
    relationship TEXT,                     -- 关系描述
    FOREIGN KEY(state_id) REFERENCES galgame_states(id)
);

-- 故事消息表
CREATE TABLE IF NOT EXISTS galgame_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER,                      -- 关联游戏状态
    role TEXT NOT NULL,                    -- narrator/character_name
    content TEXT NOT NULL,                 -- 消息内容
    choices TEXT,                          -- 选择项 (JSON)
    selected_choice INTEGER,               -- 玩家选择
    affection_changes TEXT,                -- 好感度变化 (JSON)
    currency_change INTEGER DEFAULT 0,     -- 货币变化
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(state_id) REFERENCES galgame_states(id)
);

-- 商品表
CREATE TABLE IF NOT EXISTS galgame_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 商品名称
    description TEXT,                      -- 商品描述
    price INTEGER NOT NULL,                -- 价格
    effect TEXT,                           -- 效果描述 (JSON)
    category TEXT,                         -- 分类
    icon TEXT                              -- 图标路径
);
```

### 3.2 数据模型设计

```python
# src/ui/galgame/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class MessageRole(Enum):
    NARRATOR = "narrator"      # 旁白
    SYSTEM = "system"          # 系统消息
    CHARACTER = "character"    # 角色对话

@dataclass
class Protagonist:
    name: str = "主角"
    personality: str = ""
    background: str = ""
    traits: List[str] = field(default_factory=list)

@dataclass
class Character:
    name: str
    personality: str = ""
    background: str = ""
    avatar: Optional[str] = None
    initial_affection: int = 50
    relationship: str = "陌生人"

@dataclass
class WorldSetting:
    name: str = "现代都市"
    era: str = "现代"
    rules: str = ""
    special_elements: List[str] = field(default_factory=list)

@dataclass
class AffectionState:
    character_name: str
    affection: int  # 0-100
    relationship: str

@dataclass
class GameChoice:
    id: int
    text: str
    affection_effects: Dict[str, int] = field(default_factory=dict)
    currency_effect: int = 0

@dataclass
class StoryMessage:
    id: int
    role: MessageRole
    character_name: Optional[str]
    content: str
    choices: List[GameChoice] = field(default_factory=list)
    selected_choice: Optional[int] = None
    affection_changes: Dict[str, int] = field(default_factory=dict)
    currency_change: int = 0
    timestamp: str = ""

@dataclass
class GameState:
    save_id: int
    config_id: int
    chapter: int = 1
    scene: str = "开场"
    currency: int = 100
    inventory: List[Dict] = field(default_factory=list)
    affections: List[AffectionState] = field(default_factory=list)
    messages: List[StoryMessage] = field(default_factory=list)
    story_context: List[Dict] = field(default_factory=list)

@dataclass
class GameItem:
    id: int
    name: str
    description: str
    price: int
    effect: Dict
    category: str
    icon: Optional[str] = None
```

### 3.3 数据库管理类

```python
# src/ui/galgame/database.py

from src.core.database import BaseDatabase

class GalgameDatabase(BaseDatabase):
    def __init__(self):
        super().__init__("galgame.db")
    
    def create_tables(self):
        # 创建上述所有表
        pass
    
    def migrate(self):
        # 数据库迁移逻辑
        pass
    
    # 存档管理
    def create_save(self, name: str) -> int: pass
    def get_saves(self) -> List: pass
    def delete_save(self, save_id: int): pass
    
    # 配置管理
    def save_config(self, config: Dict) -> int: pass
    def get_config(self, config_id: int) -> Dict: pass
    def get_configs(self) -> List: pass
    
    # 状态管理
    def save_state(self, state: GameState): pass
    def load_state(self, save_id: int) -> GameState: pass
    
    # 消息管理
    def add_message(self, message: StoryMessage): pass
    def get_messages(self, state_id: int) -> List[StoryMessage]: pass
    
    # 好感度管理
    def update_affection(self, state_id: int, character_name: str, change: int): pass
    def get_affections(self, state_id: int) -> List[AffectionState]: pass
    
    # 商品管理
    def get_items(self) -> List[GameItem]: pass
    def add_item(self, item: GameItem): pass
```

---

## 四、AI调用架构

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    GalgameInterface                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   StoryGenerator                             │
│  - 构建故事生成提示词                                         │
│  - 调用LLM API                                               │
│  - 解析AI响应                                                 │
│  - 提取选择分支                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ProviderManager                            │
│  (复用现有架构)                                               │
│  - 获取LLM Provider                                          │
│  - 管理API调用                                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLMProvider                                │
│  - chat_stream() 流式生成                                    │
│  - 支持多种模型                                               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 核心类设计

```python
# src/ui/galgame/story_generator.py

from typing import Generator, Dict, List, Optional
from src.provider.manager import ProviderManager
from src.core.logger import logger

class StoryGenerator:
    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        self.system_prompt_builder = SystemPromptBuilder()
    
    def generate_story_start(
        self,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        """
        生成故事开头
        返回生成器，支持流式输出
        """
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        system_prompt = self.system_prompt_builder.build_initial_prompt(
            protagonist, characters, world_setting
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始故事的开场，并给出玩家的选择。"}
        ]
        
        full_response = ""
        for response in provider.chat_stream(messages, temperature=0.8):
            if response.content:
                full_response += response.content
                yield response.content
        
        return self._parse_response(full_response)
    
    def generate_next_scene(
        self,
        context: List[Dict],
        choice: str,
        current_state: GameState,
        model_id: Optional[str] = None
    ) -> Generator[str, None, Dict]:
        """
        根据玩家选择生成后续情节
        """
        provider = self.provider_manager.get_llm_provider(model_id)
        if not provider:
            raise ValueError("No LLM provider available")
        
        system_prompt = self.system_prompt_builder.build_continuation_prompt(
            current_state
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(context)
        messages.append({"role": "user", "content": f"玩家选择：{choice}\n请继续故事，并给出新的选择。"})
        
        full_response = ""
        for response in provider.chat_stream(messages, temperature=0.8):
            if response.content:
                full_response += response.content
                yield response.content
        
        return self._parse_response(full_response)
    
    def _parse_response(self, response: str) -> Dict:
        """
        解析AI响应，提取：
        - 故事内容
        - 选择分支
        - 好感度变化
        - 货币变化
        """
        return ResponseParser.parse(response)
```

### 4.3 响应解析器

```python
# src/ui/galgame/response_parser.py

import re
import json
from typing import Dict, List

class ResponseParser:
    """
    解析AI生成的响应内容
    """
    
    CHOICE_PATTERN = r'\[选择(\d+)\](.*?)(?=\[选择\d+\]|\[好感度\]|\[货币\]|$)'
    AFFECTION_PATTERN = r'\[好感度\]\s*(.*?)(?=\[货币\]|$)'
    CURRENCY_PATTERN = r'\[货币\]\s*(.*?)(?=$)'
    
    @classmethod
    def parse(cls, response: str) -> Dict:
        result = {
            "story": "",
            "choices": [],
            "affection_changes": {},
            "currency_change": 0
        }
        
        # 提取故事内容（去除标记部分）
        story = response
        for pattern in [cls.CHOICE_PATTERN, cls.AFFECTION_PATTERN, cls.CURRENCY_PATTERN]:
            story = re.sub(pattern, '', story, flags=re.DOTALL)
        result["story"] = story.strip()
        
        # 提取选择分支
        choices = re.findall(cls.CHOICE_PATTERN, response, re.DOTALL)
        for idx, choice_text in choices:
            result["choices"].append({
                "id": int(idx),
                "text": choice_text.strip()
            })
        
        # 提取好感度变化
        affection_text = re.search(cls.AFFECTION_PATTERN, response, re.DOTALL)
        if affection_text:
            result["affection_changes"] = cls._parse_affection(affection_text.group(1))
        
        # 提取货币变化
        currency_text = re.search(cls.CURRENCY_PATTERN, response, re.DOTALL)
        if currency_text:
            result["currency_change"] = cls._parse_currency(currency_text.group(1))
        
        return result
    
    @classmethod
    def _parse_affection(cls, text: str) -> Dict[str, int]:
        """解析好感度变化，如 '艾丽丝+5, 贝拉-3' """
        changes = {}
        pattern = r'(\w+)\s*([+-]\d+)'
        matches = re.findall(pattern, text)
        for name, change in matches:
            changes[name] = int(change)
        return changes
    
    @classmethod
    def _parse_currency(cls, text: str) -> int:
        """解析货币变化"""
        match = re.search(r'([+-]?\d+)', text)
        return int(match.group(1)) if match else 0
```

### 4.4 异步处理

```python
# src/ui/galgame/story_worker.py

from PyQt5.QtCore import QThread, pyqtSignal

class StoryGenerationWorker(QThread):
    """
    后台线程执行故事生成
    """
    text_generated = pyqtSignal(str)      # 流式输出文本
    generation_complete = pyqtSignal(dict)  # 生成完成，返回解析结果
    error_occurred = pyqtSignal(str)       # 发生错误
    
    def __init__(self, generator, method_name, *args, **kwargs):
        super().__init__()
        self.generator = generator
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs
        self._is_stopped = False
    
    def run(self):
        try:
            method = getattr(self.generator, self.method_name)
            gen = method(*self.args, **self.kwargs)
            
            full_text = ""
            result = None
            
            for text in gen:
                if self._is_stopped:
                    break
                full_text += text
                self.text_generated.emit(text)
            
            if not self._is_stopped and isinstance(result, dict):
                self.generation_complete.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True
```

---

## 五、故事生成提示词设计

### 5.1 系统提示词模板

```python
# src/ui/galgame/prompts.py

class SystemPromptBuilder:
    
    BASE_SYSTEM_PROMPT = """你是一个专业的视觉小说游戏编剧。你的任务是根据给定的设定创作引人入胜的互动故事。

## 输出格式要求

你的每次回复必须包含以下部分：

1. **故事内容**：描述当前场景和情节发展，使用生动的语言
2. **选择分支**：提供2-6个玩家可选的行动，格式为 [选择1]内容[/选择1]
3. **好感度变化**（可选）：标记某些选择对角色好感度的影响，格式为 [好感度]角色名+数值, 角色名-数值[/好感度]
4. **货币变化**（可选）：标记某些选择对货币的影响，格式为 [货币]+数值 或 [货币]-数值[/货币]

## 写作风格

- 使用第二人称（"你"）来描述玩家的行动
- 对话使用引号，并标明说话者
- 适当描写环境、心理活动和情感变化
- 保持情节紧凑，避免冗长
- 每次回复控制在200-400字

## 好感度系统

- 好感度范围：0-100
- 初始值：50
- 根据玩家选择动态变化
- 好感度影响角色对玩家的态度和剧情走向

## 货币系统

- 玩家初始拥有100金币
- 某些选择可能获得或失去金币
- 金币可用于购买道具或解锁特殊剧情
"""

    @classmethod
    def build_initial_prompt(
        cls,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting
    ) -> str:
        prompt = cls.BASE_SYSTEM_PROMPT + "\n\n"
        
        # 添加世界观设定
        prompt += f"""## 世界观设定

**世界名称**：{world_setting.name}
**时代背景**：{world_setting.era}
**世界规则**：{world_setting.rules}
"""
        if world_setting.special_elements:
            prompt += f"**特殊元素**：{', '.join(world_setting.special_elements)}\n"
        
        # 添加主角设定
        prompt += f"""
## 主角设定

**姓名**：{protagonist.name}
**性格**：{protagonist.personality}
**背景**：{protagonist.background}
"""
        if protagonist.traits:
            prompt += f"**特点**：{', '.join(protagonist.traits)}\n"
        
        # 添加角色设定
        prompt += "\n## 登场角色\n\n"
        for char in characters:
            prompt += f"""### {char.name}
- **性格**：{char.personality}
- **背景**：{char.background}
- **初始好感度**：{char.initial_affection}
- **与主角关系**：{char.relationship}

"""
        
        prompt += """
## 开始故事

请以一个引人入胜的开场开始故事，介绍主角所处的环境和初始情境。然后给出玩家的第一个选择。
"""
        return prompt
    
    @classmethod
    def build_continuation_prompt(cls, state: GameState) -> str:
        prompt = cls.BASE_SYSTEM_PROMPT + "\n\n"
        
        # 添加当前状态
        prompt += f"""## 当前游戏状态

**章节**：第{state.chapter}章
**场景**：{state.scene}
**货币**：{state.currency}金币

### 角色好感度
"""
        for aff in state.affections:
            prompt += f"- {aff.character_name}：{aff.affection} ({aff.relationship})\n"
        
        if state.inventory:
            prompt += "\n### 背包物品\n"
            for item in state.inventory:
                prompt += f"- {item['name']}：{item['description']}\n"
        
        prompt += """
## 继续故事

根据玩家的选择继续发展故事。注意：
1. 保持故事连贯性
2. 根据好感度调整角色态度
3. 适时引入新的情节或角色
4. 给出新的选择分支
"""
        return prompt
```

### 5.2 特殊场景提示词

```python
class SpecialScenePrompts:
    """特殊场景的提示词模板"""
    
    @staticmethod
    def shop_scene(items: List[GameItem], currency: int) -> str:
        return f"""
## 商店场景

玩家进入了一家商店。当前金币：{currency}

### 可购买物品
{chr(10).join([f"- {item.name}：{item.price}金币 - {item.description}" for item in items])}

请描述商店环境，并让玩家选择是否购买物品。如果玩家选择购买，使用 [货币]-价格 来扣款。
"""

    @staticmethod
    def affection_milestone(character: str, new_affection: int, relationship: str) -> str:
        return f"""
## 好感度里程碑

{character}对玩家的好感度达到了{new_affection}！
你们的关系升级为：{relationship}

请创作一个特别的场景来展现这个关系变化，可以是：
- 一次深入的对话
- 一个温馨的时刻
- 一个意外的事件

然后继续故事发展。
"""

    @staticmethod
    def chapter_transition(chapter: int, title: str) -> str:
        return f"""
## 章节过渡

故事进入第{chapter}章：{title}

请创作一个章节过渡场景：
- 可以是时间跳跃
- 可以是场景转换
- 可以是新的故事线索

然后开始新章节的内容。
"""
```

---

## 六、文件结构规划

```
src/ui/galgame/
├── __init__.py
├── galgame_interface.py      # 主界面
├── models.py                  # 数据模型
├── database.py                # 数据库管理
├── story_generator.py         # 故事生成器
├── story_worker.py            # 后台生成线程
├── response_parser.py         # 响应解析器
├── prompts.py                 # 提示词模板
│
├── widgets/                   # UI组件
│   ├── __init__.py
│   ├── top_config_panel.py    # 顶部配置面板
│   ├── story_flow_area.py     # 故事流区域
│   ├── story_message_card.py  # 消息卡片
│   ├── choice_buttons.py      # 选择按钮
│   ├── status_bar.py          # 状态栏
│   └── affection_display.py   # 好感度显示
│
└── dialogs/                   # 弹窗
    ├── __init__.py
    ├── protagonist_dialog.py  # 主角配置弹窗
    ├── character_dialog.py    # 角色配置弹窗
    ├── world_dialog.py        # 世界观配置弹窗
    ├── save_dialog.py         # 存档弹窗
    └── shop_dialog.py         # 商店弹窗
```

---

## 七、与现有系统的集成

### 7.1 主窗口集成

在 `main_window.py` 中添加：

```python
from .galgame.galgame_interface import GalgameInterface

class MainWindow(FluentWindow):
    def __init__(self, version_manager=None):
        # ... 现有代码 ...
        
        # 创建Galgame界面
        self.galgame_interface = GalgameInterface(self.db, self)
        
        # 在init_navigation中添加
    def init_navigation(self):
        # ... 现有代码 ...
        self.addSubInterface(self.galgame_interface, FIF.GAME, "Galgame")
        # ... 
```

### 7.2 数据库集成

在 `database.py` 中添加：

```python
from src.ui.galgame.database import GalgameDatabase

class DatabaseManager:
    def __init__(self):
        # ... 现有代码 ...
        self.galgame = GalgameDatabase()
```

### 7.3 主题系统集成

Galgame界面实现 `update_theme()` 方法：

```python
class GalgameInterface(QWidget):
    def update_theme(self):
        is_dark = isDarkTheme()
        # 更新所有组件的样式
        self.story_flow_area.update_theme(is_dark)
        self.status_bar.update_theme(is_dark)
        # ...
```

---

## 八、开发计划

### Phase 1: 基础框架 (预计3天)
- [ ] 创建文件结构
- [ ] 实现数据模型
- [ ] 实现数据库管理
- [ ] 创建基础UI框架

### Phase 2: 核心功能 (预计5天)
- [ ] 实现故事生成器
- [ ] 实现响应解析器
- [ ] 实现提示词系统
- [ ] 实现流式输出

### Phase 3: UI完善 (预计4天)
- [ ] 实现顶部配置面板
- [ ] 实现故事流区域
- [ ] 实现选择按钮
- [ ] 实现状态栏

### Phase 4: 系统完善 (预计3天)
- [ ] 实现好感度系统
- [ ] 实现货币系统
- [ ] 实现商品系统
- [ ] 实现存档/读档

### Phase 5: 测试与优化 (预计2天)
- [ ] 功能测试
- [ ] 性能优化
- [ ] UI美化
- [ ] 文档完善

---

## 九、注意事项

1. **AI响应稳定性**：需要处理AI可能不按格式输出响应的情况，添加重试机制
2. **上下文管理**：随着故事进行，上下文会越来越长，需要实现上下文压缩或摘要机制
3. **用户体验**：生成过程中显示加载动画，避免界面卡顿
4. **数据安全**：存档数据定期备份，防止数据丢失
5. **扩展性**：设计时考虑未来可能添加的功能，如成就系统、多结局等

---

## 十一、一键生成提示词功能

### 11.1 功能概述

提供一个"智能生成配置"按钮，用户点击后可以选择小说分类和写作风格，AI将自动生成：
- 主角完整设定（名称、性格、背景、特点）
- 配角完整设定（名称、性格、背景、初始好感度、关系）
- 世界观设定（名称、时代背景、规则、特殊元素）

### 11.2 小说分类体系

#### 11.2.1 题材分类 (Genre)

```python
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
```

#### 11.2.2 写作风格 (Writing Style)

```python
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
```

### 11.3 UI设计

#### 11.3.1 一键生成按钮

在顶部配置面板添加"✨ 智能生成"按钮，位于开始按钮旁边。

```
┌─────────────────────────────────────────────────────┐
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ 主角配置  │ │ 角色配置  │ │ 世界观   │ │ 模型   │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘  │
│                                          ┌────────┐  │
│                                          │ ✨ 智能│  │
│                                          └────────┘  │
│                                          ┌────────┐  │
│                                          │ 开始   │  │
│                                          └────────┘  │
└─────────────────────────────────────────────────────┘
```

#### 11.3.2 智能生成对话框 (PromptGeneratorDialog)

```python
class PromptGeneratorDialog(QDialog):
    """
    智能生成配置对话框
    
    包含以下组件：
    1. 题材分类选择区 - 下拉框或卡片选择
    2. 写作风格选择区 - 下拉框或卡片选择
    3. 自定义要求 - 可选的文本输入框，让用户补充额外要求
    4. 生成按钮 - 开始AI生成
    5. 预览区域 - 显示AI生成的结果
    6. 应用按钮 - 将生成结果应用到配置
    """
```

```
┌─────────────────────────────────────────────────────┐
│              ✨ 智能生成 Galgame 配置                 │
├─────────────────────────────────────────────────────┤
│  📚 选择题材分类：                                    │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐           │
│  │ 玄幻 │ │ 都市 │ │ 校园 │ │异世界│ │ 科幻 │ ...     │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘           │
│                                                     │
│  ✒️ 选择写作风格：                                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐      │
│  │轻松诙谐│ │悲情沉重│ │浪漫甜蜜│ │黑暗哥特│ │史诗宏大│      │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                │
│  │悬疑神秘│ │日常治愈│ │动作热血│ │纯随机 │            │
│  └──────┘ └──────┘ └──────┘ └──────┘                │
│                                                     │
│  💡 额外要求（可选）：                                 │
│  ┌─────────────────────────────────────────────┐    │
│  │ 例如：主角应该是女性，包含魔法战斗，有3个角色... │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│              ┌──────────┐ ┌──────────┐              │
│              │   取消   │ │ 开始生成  │              │
│              └──────────┘ └──────────┘              │
└─────────────────────────────────────────────────────┘
```

**生成后预览界面**：

```
┌─────────────────────────────────────────────────────┐
│              ✨ 智能生成 Galgame 配置                 │
├─────────────────────────────────────────────────────┤
│  📖 生成结果预览：                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ 题材：校园                                   │    │
│  │ 风格：轻松诙谐                               │    │
│  ├─────────────────────────────────────────────┤    │
│  │ 【主角设定】                                 │    │
│  │ 名称：林小悠                                │    │
│  │ 性格：开朗活泼，有点天然呆                    │    │
│  │ 背景：高二转学生，因为父亲工作调动来到新城市   │    │
│  │ 特点：超强的运动神经，路痴                    │    │
│  ├─────────────────────────────────────────────┤    │
│  │ 【角色1：苏晓晓】                            │    │
│  │ 性格：温柔体贴，班长                          │    │
│  │ 背景：本地长大的优等生                        │    │
│  │ 初始好感度：50 | 关系：同学                   │    │
│  ├─────────────────────────────────────────────┤    │
│  │ 【角色2：陆子轩】                            │    │
│  │ 性格：高冷学霸，外冷内热                      │    │
│  │ 背景：学生会长，成绩优异                      │    │
│  │ 初始好感度：40 | 关系：同班同学               │    │
│  ├─────────────────────────────────────────────┤    │
│  │ 【世界观设定】                               │    │
│  │ 名称：樱花高校物语                          │    │
│  │ 时代：现代                                   │    │
│  │ 规则：普通日本高中，注重校园生活               │    │
│  │ 特殊元素：文化祭、社团活动、学园祭             │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│              ┌──────────┐ ┌──────────┐              │
│              │  重新生成 │ │ 应用配置  │              │
│              └──────────┘ └──────────┘              │
└─────────────────────────────────────────────────────┘
```

### 11.4 AI生成提示词设计

#### 11.4.1 系统提示词

```python
PROMPT_GENERATOR_SYSTEM = """你是一个专业的视觉小说游戏设定师。你的任务是根据给定的题材和风格，创作完整的游戏角色和世界观设定。

## 输出格式要求

你的回复必须严格按照以下JSON格式：

```json
{
    "protagonist": {
        "name": "主角名称",
        "personality": "主角性格描述",
        "background": "主角背景故事",
        "traits": ["特点1", "特点2", "特点3"]
    },
    "characters": [
        {
            "name": "角色名称",
            "personality": "性格描述",
            "background": "背景故事",
            "initial_affection": 50,
            "relationship": "与主角的关系"
        }
    ],
    "world_setting": {
        "name": "世界观名称",
        "era": "时代背景",
        "rules": "世界规则描述",
        "special_elements": ["元素1", "元素2", "元素3"]
    }
}
```

## 创作要求

1. **角色数量**：生成3-5个配角
2. **名称风格**：根据题材选择符合风格的名称
3. **性格多样**：每个角色应该有独特的性格特点
4. **背景合理**：背景故事要与世界观相符
5. **好感度合理**：根据关系设置合理的初始好感度（30-70之间）
6. **世界观完整**：包含足够的设定元素来支撑故事

## 注意事项

- 确保JSON格式正确，可以被解析
- 所有内容使用中文
- 角色名称要有创意且符合题材
- 避免过于模板化的设定
"""
```

#### 11.4.2 用户提示词

```python
def build_prompt_generator_user_prompt(
    genre: str,
    style: str,
    custom_requirements: str = ""
) -> str:
    """
    构建生成配置的用户提示词
    
    Args:
        genre: 题材分类
        style: 写作风格
        custom_requirements: 自定义要求
        
    Returns:
        完整的用户提示词
    """
    prompt = f"""请根据以下要求创作视觉小说游戏设定：

**题材分类**：{genre}
**写作风格**：{style}
"""
    
    if custom_requirements:
        prompt += f"\n**额外要求**：{custom_requirements}\n"
    
    prompt += """
请生成完整的主角设定、配角设定（3-5个）和世界观设定。
确保设定有趣、有创意，符合给定的题材和风格。

现在请开始创作。"""
    
    return prompt
```

### 11.5 核心类设计

```python
# src/ui/galgame/prompt_generator.py

import json
from typing import Dict, Optional, List
from PyQt5.QtCore import QThread, pyqtSignal

from .models import Protagonist, Character, WorldSetting
from ..prompts import PROMPT_GENERATOR_SYSTEM

class PromptGenerationWorker(QThread):
    """
    后台线程执行提示词生成
    """
    generation_complete = pyqtSignal(dict)  # 生成完成，返回解析结果
    error_occurred = pyqtSignal(str)       # 发生错误
    
    def __init__(self, provider_manager, genre: str, style: str, 
                 custom_requirements: str = "", model_id: str = None):
        super().__init__()
        self.provider_manager = provider_manager
        self.genre = genre
        self.style = style
        self.custom_requirements = custom_requirements
        self.model_id = model_id
    
    def run(self):
        try:
            provider = self.provider_manager.get_llm_provider(self.model_id)
            if not provider:
                self.error_occurred.emit("未找到可用的AI模型")
                return
            
            # 构建提示词
            system_prompt = PROMPT_GENERATOR_SYSTEM
            user_prompt = build_prompt_generator_user_prompt(
                self.genre, self.style, self.custom_requirements
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 调用AI生成（非流式，因为需要完整JSON）
            response = provider.chat(messages, temperature=0.9)
            
            if response and response.content:
                # 解析JSON
                result = self._parse_response(response.content)
                self.generation_complete.emit(result)
            else:
                self.error_occurred.emit("AI生成失败，未获得有效响应")
                
        except json.JSONDecodeError as e:
            self.error_occurred.emit(f"JSON解析失败：{str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"生成失败：{str(e)}")
    
    def _parse_response(self, response: str) -> Dict:
        """
        解析AI响应，提取JSON配置
        """
        # 尝试提取JSON块
        import re
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个响应
            json_str = response
        
        return json.loads(json_str)


class PromptGenerator:
    """
    提示词生成器管理类
    """
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
    
    def generate_config(
        self,
        genre: str,
        style: str,
        custom_requirements: str = "",
        model_id: str = None
    ) -> PromptGenerationWorker:
        """
        开始生成配置
        
        Returns:
            后台工作线程
        """
        worker = PromptGenerationWorker(
            self.provider_manager,
            genre,
            style,
            custom_requirements,
            model_id
        )
        return worker
```

### 11.6 数据流

```
1. 用户点击"智能生成"按钮
   ↓
2. 打开PromptGeneratorDialog
   ↓
3. 用户选择题材分类和写作风格
   ↓
4. 用户可输入额外要求
   ↓
5. 用户点击"开始生成"
   ↓
6. 创建PromptGenerationWorker
   ↓
7. 构建系统提示词和用户提示词
   ↓
8. 调用AI生成配置
   ↓
9. 解析AI返回的JSON
   ↓
10. 在预览区域显示结果
   ↓
11. 用户点击"应用配置"
   ↓
12. 将结果填充到主角、角色、世界观配置中
   ↓
13. 关闭对话框
```

### 11.7 错误处理

1. **AI响应格式错误**：
   - 尝试从响应中提取JSON块
   - 如果提取失败，显示错误并允许重新生成

2. **网络错误**：
   - 显示网络错误提示
   - 提供重试按钮

3. **JSON解析错误**：
   - 显示解析失败信息
   - 允许用户手动编辑生成的内容

### 11.8 扩展功能

1. **生成历史**：保存最近的生成结果，允许回溯
2. **混合生成**：允许用户选择只生成部分配置（如只生成角色）
3. **模板保存**：允许用户保存满意的生成结果作为模板
4. **批量生成**：一次生成多个方案供用户选择

---

## 十二、示例流程

```
1. 用户进入Galgame页面
2. 点击"✨ 智能生成"按钮
3. 在对话框中选择"校园"题材和"轻松诙谐"风格
4. 可选：输入额外要求，如"主角是女生，有3个可攻略角色"
5. 点击"开始生成"
6. AI生成完整配置并显示预览
7. 用户点击"应用配置"
8. 配置自动填充到主角、角色、世界观中
9. 用户可以进一步手动调整配置
10. 点击"开始"按钮开始游戏
11. 系统调用AI生成故事开头
12. 显示故事内容和选择按钮
13. 用户点击选择
14. 系统根据选择生成后续情节
15. 更新好感度、货币等状态
16. 循环12-15直到故事结束
```

---

## 十三、章节架构与故事引擎

### 13.1 架构概述

将故事生成从"单次生成"升级为"章节制"架构。每3次AI回答为一个章节，章节之间进行故事概括、前情提要和下一章规划。

**核心流程：**

```
游戏开始
  ↓
Phase 1: 故事初始化（一次性）
  - 分析世界观 + 角色 → 生成故事大纲 + 开头设定
  - 生成第一章名称
  - 缓存所有设定数据
  ↓
Phase 2: 章节内容生成（循环，每章3次回答）
  - 第1次回答：章节开头场景
  - 第2次回答：章节发展
  - 第3次回答：章节高潮/转折
  ↓
Phase 3: 章节过渡（每3次回答后触发）
  - 概括前3次回答的内容
  - 提炼前文关键情节和前情提要
  - 将概括加入缓存数据
  - 生成下一章大纲和章节名称
  ↓
回到 Phase 2（新章节的第1次回答）
```

### 13.2 数据结构设计

#### 13.2.1 章节数据模型

```python
@dataclass
class ChapterData:
    chapter_number: int = 1
    chapter_name: str = ""
    chapter_outline: str = ""       # 本章大纲/梗概
    opening_setting: str = ""       # 开场设定
    response_count: int = 0         # 当前章节已生成的回答次数（0-2，到3触发新章节）
    is_completed: bool = False      # 本章是否已完成

@dataclass
class StoryCache:
    story_synopsis: str = ""              # 故事总体大纲
    world_analysis: str = ""              # 世界观分析
    character_analysis: str = ""          # 角色关系分析
    previous_chapter_summaries: List[str] = field(default_factory=list)  # 历史章节摘要
    current_chapter: ChapterData = field(default_factory=ChapterData)
    key_plot_points: List[str] = field(default_factory=list)  # 关键情节节点
    foreshadowing: List[str] = field(default_factory=list)    # 伏笔列表
```

#### 13.2.2 数据库扩展

在 `galgame_states` 表中新增字段：

```sql
ALTER TABLE galgame_states ADD COLUMN story_cache TEXT;  -- JSON格式的StoryCache
```

### 13.3 故事引擎流程

#### 13.3.1 Phase 1: 故事初始化

当用户点击"开始游戏"时，执行两步AI调用：

**Step 1: 分析与规划（非流式调用）**

```python
def generate_story_plan(
    protagonist: Protagonist,
    characters: List[Character],
    world_setting: WorldSetting,
    model_id: str = None
) -> StoryCache:
    """
    分析世界观和角色，生成故事大纲和开头设定
    """
```

提示词模板：

```
你是一个专业的视觉小说游戏策划师。请根据以下世界观和角色设定，创作一个完整的故事框架。

## 世界观设定
{world_setting}

## 主角设定
{protagonist}

## 登场角色
{characters}

## 输出格式（严格JSON）

```json
{
    "story_synopsis": "故事总体大纲（200-300字，描述整个故事的主线、核心冲突和走向）",
    "world_analysis": "世界观深度分析（100-200字，挖掘世界观的潜在冲突和故事空间）",
    "character_analysis": "角色关系分析（100-200字，分析角色间的潜在互动和冲突）",
    "first_chapter": {
        "chapter_name": "第一章名称（4-8个字，要有文学感）",
        "chapter_outline": "第一章大纲（100-200字，描述本章的主要情节和冲突）",
        "opening_setting": "开场设定（100-150字，描述故事开场的具体场景、氛围和切入点）"
    },
    "key_plot_points": ["关键情节1", "关键情节2", "关键情节3"],
    "foreshadowing": ["伏笔1", "伏笔2"]
}
```

请确保大纲有足够的深度和张力，角色关系有发展空间。
```

**Step 2: 生成第一章开头（流式调用）**

使用规划好的大纲和开场设定，调用AI生成第一章的第一段故事内容。

提示词模板：

```
{BASE_SYSTEM_PROMPT}

## 故事大纲
{story_synopsis}

## 当前章节：第1章 - {chapter_name}
章节大纲：{chapter_outline}

## 开场设定
{opening_setting}

## 角色关系
{character_analysis}

请根据以上设定，创作第一章的开场。严格遵循开场设定中的场景和氛围，自然地引入主角和关键角色。
```

#### 13.3.2 Phase 2: 章节内容生成

每次玩家做出选择后，继续生成当前章节的下一段内容。

```python
def generate_chapter_content(
    context: List[Dict],
    choice: str,
    story_cache: StoryCache,
    current_state: GameState,
    model_id: str = None
) -> Generator[str, None, Dict]:
    """
    生成章节内容
    story_cache.current_chapter.response_count 会递增
    """
```

提示词模板：

```
{BASE_SYSTEM_PROMPT}

## 故事大纲
{story_synopsis}

## 当前章节：第{chapter_number}章 - {chapter_name}
章节大纲：{chapter_outline}

## 前情提要
{previous_chapter_summaries}

## 当前游戏状态
章节：第{chapter_number}章
货币：{currency}金币

### 角色好感度
{affections}

### 关键情节节点
{key_plot_points}

### 待回收伏笔
{foreshadowing}

## 玩家选择
{choice}

请继续创作当前章节的内容。注意：
1. 保持与章节大纲的一致性
2. 承接前文情节，逻辑连贯
3. 适当推进章节核心冲突
4. 给出新的选择分支
```

#### 13.3.3 Phase 3: 章节过渡

当 `response_count` 达到3时，触发章节过渡：

**Step 1: 概括前文（非流式调用）**

```python
def generate_chapter_summary(
    chapter_messages: List[str],  # 本章3次回答的故事内容
    story_cache: StoryCache,
    model_id: str = None
) -> Dict:
    """
    概括本章内容，提炼前情提要
    """
```

提示词模板：

```
你是一个专业的故事编辑。请对以下章节内容进行概括和提炼。

## 本章内容
{chapter_messages}

## 本章大纲
{chapter_outline}

## 输出格式（严格JSON）

```json
{
    "chapter_summary": "本章摘要（100-150字，概括本章核心事件和发展）",
    "key_events": ["关键事件1", "关键事件2", "关键事件3"],
    "character_developments": "角色发展变化（50-100字）",
    "cliffhanger": "本章结尾悬念/钩子（30-50字，为下一章铺垫）",
    "new_foreshadowing": ["新伏笔1", "新伏笔2"],
    "resolved_foreshadowing": ["已回收的伏笔1"]
}
```
```

**Step 2: 生成下一章规划（非流式调用）**

```python
def generate_next_chapter_plan(
    story_cache: StoryCache,
    current_state: GameState,
    model_id: str = None
) -> ChapterData:
    """
    生成下一章的大纲和名称
    """
```

提示词模板：

```
你是一个专业的视觉小说游戏策划师。请根据前文发展，规划下一章的内容。

## 故事总体大纲
{story_synopsis}

## 已完成章节摘要
{previous_chapter_summaries}

## 上一章结尾悬念
{cliffhanger}

## 当前角色状态
{affections}

## 关键情节节点
{key_plot_points}

## 待回收伏笔
{foreshadowing}

## 输出格式（严格JSON）

```json
{
    "chapter_name": "第{N}章名称（4-8个字，要有文学感）",
    "chapter_outline": "本章大纲（100-200字，描述本章的主要情节和冲突）",
    "opening_setting": "开场设定（100-150字，描述本章开场的具体场景和氛围）"
}
```

请确保新章节与故事大纲方向一致，承接上一章的悬念，推进核心冲突。
```

**Step 3: 生成新章节开头（流式调用）**

使用新章节的规划数据，生成新章节的第一段故事内容。

### 13.4 缓存数据管理

```python
class StoryCacheManager:
    """
    管理故事缓存数据的更新和持久化
    """
    
    def update_after_response(self, cache: StoryCache, response_text: str):
        """每次回答后更新缓存"""
        cache.current_chapter.response_count += 1
    
    def update_after_chapter_summary(self, cache: StoryCache, summary: Dict):
        """章节概括后更新缓存"""
        cache.previous_chapter_summaries.append(summary['chapter_summary'])
        cache.current_chapter.is_completed = True
        # 更新关键情节和伏笔
        for event in summary.get('key_events', []):
            cache.key_plot_points.append(event)
        for fs in summary.get('new_foreshadowing', []):
            cache.foreshadowing.append(fs)
        # 移除已回收的伏笔
        for resolved in summary.get('resolved_foreshadowing', []):
            if resolved in cache.foreshadowing:
                cache.foreshadowing.remove(resolved)
    
    def update_after_chapter_plan(self, cache: StoryCache, plan: Dict):
        """新章节规划后更新缓存"""
        cache.current_chapter = ChapterData(
            chapter_number=cache.current_chapter.chapter_number + 1,
            chapter_name=plan['chapter_name'],
            chapter_outline=plan['chapter_outline'],
            opening_setting=plan['opening_setting'],
            response_count=0,
            is_completed=False
        )
    
    def to_dict(self, cache: StoryCache) -> Dict:
        """序列化为字典"""
        return {
            'story_synopsis': cache.story_synopsis,
            'world_analysis': cache.world_analysis,
            'character_analysis': cache.character_analysis,
            'previous_chapter_summaries': cache.previous_chapter_summaries,
            'current_chapter': {
                'chapter_number': cache.current_chapter.chapter_number,
                'chapter_name': cache.current_chapter.chapter_name,
                'chapter_outline': cache.current_chapter.chapter_outline,
                'opening_setting': cache.current_chapter.opening_setting,
                'response_count': cache.current_chapter.response_count,
                'is_completed': cache.current_chapter.is_completed
            },
            'key_plot_points': cache.key_plot_points,
            'foreshadowing': cache.foreshadowing
        }
    
    def from_dict(self, data: Dict) -> StoryCache:
        """从字典反序列化"""
        # ...
```

### 13.5 主界面集成

```python
class GalgameInterface(QWidget):
    def _start_game(self):
        # Phase 1: 故事初始化
        # Step 1: 生成故事规划（非流式）
        self._story_cache = self._story_generator.generate_story_plan(
            self._protagonist, self._characters, self._world_setting, model_id
        )
        # Step 2: 生成第一章开头（流式）
        self._start_chapter_generation(self._story_cache.current_chapter)
    
    def _on_choice_selected(self, choice_id: int):
        # 检查是否需要触发章节过渡
        if self._story_cache.current_chapter.response_count >= 3:
            # Phase 3: 章节过渡
            self._transition_to_next_chapter()
        else:
            # Phase 2: 继续当前章节
            self._continue_chapter_generation(choice)
    
    def _transition_to_next_chapter(self):
        # Step 1: 概括前文（非流式）
        summary = self._story_generator.generate_chapter_summary(
            chapter_messages, self._story_cache, model_id
        )
        self._cache_manager.update_after_chapter_summary(self._story_cache, summary)
        
        # Step 2: 生成下一章规划（非流式）
        next_chapter = self._story_generator.generate_next_chapter_plan(
            self._story_cache, self._game_state, model_id
        )
        self._cache_manager.update_after_chapter_plan(self._story_cache, next_chapter)
        
        # Step 3: 生成新章节开头（流式）
        self._start_chapter_generation(self._story_cache.current_chapter)
```

### 13.6 UI 更新

- 在状态栏显示当前章节名称（如"第一章：初入秘境"）
- 章节过渡时显示过渡动画或提示
- 每次新章节开始时，在故事流中插入章节标题卡片

### 13.7 完整流程图

```
用户点击"开始"
  │
  ├─→ [AI调用1] 生成故事规划（大纲+第一章设定）
  │     ↓
  │   缓存 StoryCache
  │     ↓
  ├─→ [AI调用2] 生成第一章开头（流式）→ response_count=1
  │     ↓
  │   用户选择 → [AI调用3] 继续第一章 → response_count=2
  │     ↓
  │   用户选择 → [AI调用4] 继续第一章 → response_count=3
  │     ↓
  ├─→ [AI调用5] 概括第一章内容（非流式）
  │     ↓
  │   更新缓存（摘要、伏笔、关键情节）
  │     ↓
  ├─→ [AI调用6] 规划第二章（非流式）
  │     ↓
  │   更新缓存（新章节设定）
  │     ↓
  ├─→ [AI调用7] 生成第二章开头（流式）→ response_count=1
  │     ↓
  │   ... 循环 ...
```

---

*文档版本：v1.2*
*创建日期：2026-04-16*
*更新日期：2026-04-17*
*作者：AI Assistant*
