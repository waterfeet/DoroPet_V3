from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from enum import Enum
import json


class MessageRole(Enum):
    NARRATOR = "narrator"
    SYSTEM = "system"
    CHARACTER = "character"


@dataclass
class Protagonist:
    name: str = "主角"
    personality: str = ""
    background: str = ""
    traits: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Protagonist':
        return cls(
            name=data.get('name', '主角'),
            personality=data.get('personality', ''),
            background=data.get('background', ''),
            traits=data.get('traits', [])
        )


@dataclass
class Character:
    name: str
    personality: str = ""
    background: str = ""
    avatar: Optional[str] = None
    initial_affection: int = 10  # 初始好感度设为 10，让玩家有明显的成长体验
    relationship: str = "陌生人"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        return cls(
            name=data.get('name', ''),
            personality=data.get('personality', ''),
            background=data.get('background', ''),
            avatar=data.get('avatar'),
            initial_affection=data.get('initial_affection', 10),
            relationship=data.get('relationship', '陌生人')
        )


@dataclass
class WorldSetting:
    name: str = "现代都市"
    era: str = "现代"
    rules: str = ""
    special_elements: List[str] = field(default_factory=list)
    writing_style: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorldSetting':
        return cls(
            name=data.get('name', '现代都市'),
            era=data.get('era', '现代'),
            rules=data.get('rules', ''),
            special_elements=data.get('special_elements', []),
            writing_style=data.get('writing_style', '')
        )


@dataclass
class AffectionState:
    character_name: str
    affection: int = 10  # 初始好感度 10
    relationship: str = "陌生人"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AffectionState':
        return cls(
            character_name=data.get('character_name', ''),
            affection=data.get('affection', 10),
            relationship=data.get('relationship', '陌生人')
        )


@dataclass
class GameChoice:
    id: int
    text: str
    affection_effects: Dict[str, int] = field(default_factory=dict)
    currency_effect: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameChoice':
        return cls(
            id=data.get('id', 0),
            text=data.get('text', ''),
            affection_effects=data.get('affection_effects', {}),
            currency_effect=data.get('currency_effect', 0)
        )


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
    chapter_number: int = 1
    chapter_name: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'role': self.role.value,
            'character_name': self.character_name,
            'content': self.content,
            'choices': [c.to_dict() for c in self.choices],
            'selected_choice': self.selected_choice,
            'affection_changes': self.affection_changes,
            'currency_change': self.currency_change,
            'timestamp': self.timestamp,
            'chapter_number': self.chapter_number,
            'chapter_name': self.chapter_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StoryMessage':
        return cls(
            id=data.get('id', 0),
            role=MessageRole(data.get('role', 'narrator')),
            character_name=data.get('character_name'),
            content=data.get('content', ''),
            choices=[GameChoice.from_dict(c) for c in data.get('choices', [])],
            selected_choice=data.get('selected_choice'),
            affection_changes=data.get('affection_changes', {}),
            currency_change=data.get('currency_change', 0),
            timestamp=data.get('timestamp', ''),
            chapter_number=data.get('chapter_number', 1),
            chapter_name=data.get('chapter_name', '')
        )


@dataclass
class ChapterData:
    chapter_number: int = 1
    chapter_name: str = ""
    chapter_outline: str = ""
    opening_setting: str = ""
    response_count: int = 0
    is_completed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            'chapter_number': self.chapter_number,
            'chapter_name': self.chapter_name,
            'chapter_outline': self.chapter_outline,
            'opening_setting': self.opening_setting,
            'response_count': self.response_count,
            'is_completed': self.is_completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChapterData':
        return cls(
            chapter_number=data.get('chapter_number', 1),
            chapter_name=data.get('chapter_name', ''),
            chapter_outline=data.get('chapter_outline', ''),
            opening_setting=data.get('opening_setting', ''),
            response_count=data.get('response_count', 0),
            is_completed=data.get('is_completed', False)
        )


@dataclass
class StoryCache:
    story_synopsis: str = ""
    world_analysis: str = ""
    character_analysis: str = ""
    previous_chapter_summaries: List[str] = field(default_factory=list)
    current_chapter: ChapterData = field(default_factory=ChapterData)
    key_plot_points: List[str] = field(default_factory=list)
    foreshadowing: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'story_synopsis': self.story_synopsis,
            'world_analysis': self.world_analysis,
            'character_analysis': self.character_analysis,
            'previous_chapter_summaries': self.previous_chapter_summaries,
            'current_chapter': self.current_chapter.to_dict(),
            'key_plot_points': self.key_plot_points,
            'foreshadowing': self.foreshadowing
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StoryCache':
        return cls(
            story_synopsis=data.get('story_synopsis', ''),
            world_analysis=data.get('world_analysis', ''),
            character_analysis=data.get('character_analysis', ''),
            previous_chapter_summaries=data.get('previous_chapter_summaries', []),
            current_chapter=ChapterData.from_dict(data.get('current_chapter', {})),
            key_plot_points=data.get('key_plot_points', []),
            foreshadowing=data.get('foreshadowing', [])
        )


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
    story_cache: Optional[StoryCache] = None
    protagonist: Optional['Protagonist'] = None
    characters: List['Character'] = field(default_factory=list)
    world_setting: Optional['WorldSetting'] = None
    
    def to_dict(self) -> Dict:
        return {
            'save_id': self.save_id,
            'config_id': self.config_id,
            'chapter': self.chapter,
            'scene': self.scene,
            'currency': self.currency,
            'inventory': self.inventory,
            'affections': [a.to_dict() for a in self.affections],
            'messages': [m.to_dict() for m in self.messages],
            'story_context': self.story_context,
            'story_cache': self.story_cache.to_dict() if self.story_cache else None,
            'protagonist': self.protagonist.to_dict() if self.protagonist else None,
            'characters': [c.to_dict() for c in self.characters],
            'world_setting': self.world_setting.to_dict() if self.world_setting else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameState':
        story_cache_data = data.get('story_cache')
        protagonist_data = data.get('protagonist')
        world_setting_data = data.get('world_setting')
        return cls(
            save_id=data.get('save_id', 0),
            config_id=data.get('config_id', 0),
            chapter=data.get('chapter', 1),
            scene=data.get('scene', '开场'),
            currency=data.get('currency', 100),
            inventory=data.get('inventory', []),
            affections=[AffectionState.from_dict(a) for a in data.get('affections', [])],
            messages=[StoryMessage.from_dict(m) for m in data.get('messages', [])],
            story_context=data.get('story_context', []),
            story_cache=StoryCache.from_dict(story_cache_data) if story_cache_data else None,
            protagonist=Protagonist.from_dict(protagonist_data) if protagonist_data else None,
            characters=[Character.from_dict(c) for c in data.get('characters', [])],
            world_setting=WorldSetting.from_dict(world_setting_data) if world_setting_data else None
        )
    
    def get_affection(self, character_name: str) -> int:
        for aff in self.affections:
            if aff.character_name == character_name:
                return aff.affection
        return 50
    
    def update_affection(self, character_name: str, change: int) -> int:
        for aff in self.affections:
            if aff.character_name == character_name:
                aff.affection = max(0, min(100, aff.affection + change))
                return aff.affection
        new_aff = AffectionState(
            character_name=character_name,
            affection=max(0, min(100, 50 + change)),
            relationship="陌生人"
        )
        self.affections.append(new_aff)
        return new_aff.affection


@dataclass
class GameItem:
    id: int
    name: str
    description: str
    price: int
    effect: Dict
    category: str
    icon: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameItem':
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            description=data.get('description', ''),
            price=data.get('price', 0),
            effect=data.get('effect', {}),
            category=data.get('category', ''),
            icon=data.get('icon')
        )


@dataclass
class GameConfig:
    id: int
    name: str
    protagonist: Protagonist
    characters: List[Character]
    world_setting: WorldSetting
    model_id: str
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'protagonist': self.protagonist.to_dict(),
            'characters': [c.to_dict() for c in self.characters],
            'world_setting': self.world_setting.to_dict(),
            'model_id': self.model_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameConfig':
        return cls(
            id=data.get('id', 0),
            name=data.get('name', ''),
            protagonist=Protagonist.from_dict(data.get('protagonist', {})),
            characters=[Character.from_dict(c) for c in data.get('characters', [])],
            world_setting=WorldSetting.from_dict(data.get('world_setting', {})),
            model_id=data.get('model_id', '')
        )


RELATIONSHIP_LEVELS = [
    (0, "陌生人"),
    (20, "认识"),
    (40, "朋友"),
    (60, "好友"),
    (80, "亲密"),
    (95, "挚爱"),
]


def get_relationship_name(affection: int) -> str:
    for threshold, name in reversed(RELATIONSHIP_LEVELS):
        if affection >= threshold:
            return name
    return "陌生人"


class MemoryType(Enum):
    INTERACTION = "interaction"
    PROMISE = "promise"
    GIFT = "gift"
    CONFLICT = "conflict"
    SPECIAL = "special"


class EventType(Enum):
    RANDOM = "random"
    CONTEXTUAL = "contextual"
    SCHEDULED = "scheduled"
    REACTIVE = "reactive"
    CHAIN = "chain"
    EXCLUSIVE = "exclusive"


@dataclass
class CharacterMemory:
    id: int
    character_name: str
    memory_type: str
    content: str
    importance: int
    timestamp: str
    context: Dict
    is_remembered: bool = True
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterMemory':
        return cls(
            id=data.get('id', 0),
            character_name=data.get('character_name', ''),
            memory_type=data.get('memory_type', 'interaction'),
            content=data.get('content', ''),
            importance=data.get('importance', 5),
            timestamp=data.get('timestamp', ''),
            context=data.get('context', {}),
            is_remembered=data.get('is_remembered', True)
        )


@dataclass
class CharacterExclusiveEvent:
    id: str
    character_name: str
    event_name: str
    trigger_conditions: Dict
    required_affection: int
    event_type: str
    scenes: List[Dict]
    is_repeatable: bool = False
    cooldown_chapters: int = 0
    
    def check_trigger(self, state: 'GameState', memories: List['CharacterMemory']) -> bool:
        if "affection_min" in self.trigger_conditions:
            current_affection = state.get_affection(self.character_name)
            if current_affection < self.trigger_conditions["affection_min"]:
                return False
        
        if "chapter_min" in self.trigger_conditions:
            if state.chapter < self.trigger_conditions["chapter_min"]:
                return False
        
        if "required_memories" in self.trigger_conditions:
            for required in self.trigger_conditions["required_memories"]:
                required_type, required_content = required.split(":", 1) if ":" in required else ("special", required)
                if not any(m.memory_type == required_type and required_content in m.content for m in memories):
                    return False
        
        return True
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterExclusiveEvent':
        return cls(
            id=data.get('id', ''),
            character_name=data.get('character_name', ''),
            event_name=data.get('event_name', ''),
            trigger_conditions=data.get('trigger_conditions', {}),
            required_affection=data.get('required_affection', 50),
            event_type=data.get('event_type', 'story'),
            scenes=data.get('scenes', []),
            is_repeatable=data.get('is_repeatable', False),
            cooldown_chapters=data.get('cooldown_chapters', 0)
        )


@dataclass
class CharacterRelationship:
    character_a: str
    character_b: str
    affection: int = 0
    relationship_type: str = "stranger"
    history: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CharacterRelationship':
        return cls(
            character_a=data.get('character_a', ''),
            character_b=data.get('character_b', ''),
            affection=data.get('affection', 0),
            relationship_type=data.get('relationship_type', 'stranger'),
            history=data.get('history', [])
        )


@dataclass
class DynamicEvent:
    id: str
    event_name: str
    description: str
    event_type: str
    trigger_conditions: List[Dict] = field(default_factory=list)
    base_probability: float = 0.1
    required_context: Dict = field(default_factory=dict)
    effects: Dict = field(default_factory=dict)
    next_events: List[str] = field(default_factory=list)
    chain_probability: float = 0.3
    max_triggers: int = 1
    cooldown_chapters: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DynamicEvent':
        return cls(
            id=data.get('id', ''),
            event_name=data.get('event_name', ''),
            description=data.get('description', ''),
            event_type=data.get('event_type', 'random'),
            trigger_conditions=data.get('trigger_conditions', []),
            base_probability=data.get('base_probability', 0.1),
            required_context=data.get('required_context', {}),
            effects=data.get('effects', {}),
            next_events=data.get('next_events', []),
            chain_probability=data.get('chain_probability', 0.3),
            max_triggers=data.get('max_triggers', 1),
            cooldown_chapters=data.get('cooldown_chapters', 0)
        )


@dataclass
class EventContext:
    current_scene: str = "未知场景"
    time_of_day: str = "afternoon"
    day_of_week: str = "weekday"
    weather: str = "sunny"
    season: str = "spring"
    special_date: Optional[str] = None
    nearby_characters: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EventContext':
        return cls(
            current_scene=data.get('current_scene', '未知场景'),
            time_of_day=data.get('time_of_day', 'afternoon'),
            day_of_week=data.get('day_of_week', 'weekday'),
            weather=data.get('weather', 'sunny'),
            season=data.get('season', 'spring'),
            special_date=data.get('special_date'),
            nearby_characters=data.get('nearby_characters', [])
        )


class EndingType(Enum):
    PERFECT = "perfect"
    HAREM = "harem"
    NORMAL = "normal"
    LONELY = "lonely"
    SECRET = "secret"


@dataclass
class GameEnding:
    id: int
    ending_type: str
    character_name: str
    ending_title: str
    ending_description: str
    ending_story: str
    final_affection: int
    total_chapters: int
    play_time: str
    timestamp: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GameEnding':
        return cls(
            id=data.get('id', 0),
            ending_type=data.get('ending_type', 'normal'),
            character_name=data.get('character_name', ''),
            ending_title=data.get('ending_title', ''),
            ending_description=data.get('ending_description', ''),
            ending_story=data.get('ending_story', ''),
            final_affection=data.get('final_affection', 0),
            total_chapters=data.get('total_chapters', 1),
            play_time=data.get('play_time', ''),
            timestamp=data.get('timestamp', '')
        )


@dataclass
class EndingCondition:
    ending_type: str
    condition_name: str
    condition_description: str
    min_affection: int = 0
    max_affection: int = 100
    required_characters: List[str] = field(default_factory=list)
    excluded_characters: List[str] = field(default_factory=list)
    
    def check(self, affections: List['AffectionState']) -> bool:
        if self.ending_type == "perfect":
            max_aff = max(a.affection for a in affections) if affections else 0
            if max_aff < 100:
                return False
            high_aff_count = sum(1 for a in affections if a.affection >= 50)
            return high_aff_count == 1
        
        elif self.ending_type == "harem":
            high_aff_count = sum(1 for a in affections if a.affection >= 80)
            return high_aff_count >= 2
        
        elif self.ending_type == "lonely":
            max_aff = max(a.affection for a in affections) if affections else 0
            return max_aff < 30
        
        elif self.ending_type == "normal":
            max_aff = max(a.affection for a in affections) if affections else 0
            return 30 <= max_aff < 100
        
        return False
