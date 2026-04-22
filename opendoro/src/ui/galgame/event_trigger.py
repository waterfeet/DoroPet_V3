import random
import json
import os
from typing import List, Dict, Optional, Set
from datetime import datetime
from .models import (
    GameState, CharacterMemory, CharacterExclusiveEvent,
    DynamicEvent, EventContext, CharacterRelationship
)
from .database import GalgameDatabase
from .memory_manager import CharacterMemoryManager


class ExclusiveEventTrigger:
    def __init__(self, db: GalgameDatabase, memory_manager: CharacterMemoryManager):
        self._db = db
        self._memory_manager = memory_manager
        self._event_configs: List[CharacterExclusiveEvent] = []
        self._triggered_events: Set[str] = set()
        self._state_id: Optional[int] = None
        self._load_default_events()
    
    def set_state_id(self, state_id: int):
        self._state_id = state_id
        self._load_triggered_events()
    
    def _load_triggered_events(self):
        if self._state_id is None:
            return
        self._triggered_events.clear()
        events = self._db.get_triggered_events(self._state_id)
        for event in events:
            self._triggered_events.add(event['event_id'])
    
    def _load_default_events(self):
        default_events = [
            CharacterExclusiveEvent(
                id="trust_confession",
                character_name="",
                event_name="信任的开始",
                trigger_conditions={"affection_min": 30, "chapter_min": 1},
                required_affection=30,
                event_type="story",
                scenes=[{
                    "scene_id": 1,
                    "description": "角色开始信任主角，分享了自己的秘密",
                    "choices": [
                        {"id": 1, "text": "认真倾听并给予安慰", "effect": {"affection": 5}},
                        {"id": 2, "text": "开玩笑转移话题", "effect": {"affection": -3}}
                    ]
                }],
                is_repeatable=False
            ),
            CharacterExclusiveEvent(
                id="friendship_bond",
                character_name="",
                event_name="友谊的羁绊",
                trigger_conditions={"affection_min": 50, "chapter_min": 2},
                required_affection=50,
                event_type="story",
                scenes=[{
                    "scene_id": 1,
                    "description": "角色与主角建立了深厚的友谊",
                    "choices": [
                        {"id": 1, "text": "邀请一起去某个地方", "effect": {"affection": 5}},
                        {"id": 2, "text": "送一份礼物", "effect": {"affection": 3, "currency": -20}}
                    ]
                }],
                is_repeatable=False
            ),
            CharacterExclusiveEvent(
                id="romantic_feeling",
                character_name="",
                event_name="心动时刻",
                trigger_conditions={"affection_min": 70, "chapter_min": 3},
                required_affection=70,
                event_type="story",
                scenes=[{
                    "scene_id": 1,
                    "description": "角色对主角产生了特别的好感",
                    "choices": [
                        {"id": 1, "text": "温柔地回应", "effect": {"affection": 5}},
                        {"id": 2, "text": "保持朋友关系", "effect": {"affection": -2}}
                    ]
                }],
                is_repeatable=False
            ),
            CharacterExclusiveEvent(
                id="deep_confession",
                character_name="",
                event_name="深情告白",
                trigger_conditions={"affection_min": 90, "chapter_min": 4},
                required_affection=90,
                event_type="confession",
                scenes=[{
                    "scene_id": 1,
                    "description": "角色向主角表白",
                    "choices": [
                        {"id": 1, "text": "接受告白", "effect": {"affection": 10}},
                        {"id": 2, "text": "需要更多时间", "effect": {"affection": -5}}
                    ]
                }],
                is_repeatable=False
            ),
            CharacterExclusiveEvent(
                id="weekend_date",
                character_name="",
                event_name="周末约会",
                trigger_conditions={"affection_min": 50, "chapter_min": 2},
                required_affection=50,
                event_type="date",
                scenes=[{
                    "scene_id": 1,
                    "description": "角色邀请主角周末一起出去玩",
                    "choices": [
                        {"id": 1, "text": "去公园散步", "effect": {"affection": 3}},
                        {"id": 2, "text": "去咖啡厅", "effect": {"affection": 3, "currency": -30}},
                        {"id": 3, "text": "去图书馆", "effect": {"affection": 2}}
                    ]
                }],
                is_repeatable=True,
                cooldown_chapters=2
            ),
        ]
        self._event_configs.extend(default_events)
    
    def check_triggers(self, state: GameState) -> Optional[CharacterExclusiveEvent]:
        if not state.characters:
            return None
        
        for character in state.characters:
            memories = self._memory_manager.get_all_memories(character.name)
            
            for event in self._event_configs:
                if event.character_name and event.character_name != character.name:
                    continue
                
                event_key = f"{event.id}_{character.name}"
                
                if not event.is_repeatable and event_key in self._triggered_events:
                    continue
                
                if self._is_in_cooldown(event_key, event, state):
                    continue
                
                event_copy = CharacterExclusiveEvent(
                    id=event_key,
                    character_name=character.name,
                    event_name=event.event_name,
                    trigger_conditions=event.trigger_conditions,
                    required_affection=event.required_affection,
                    event_type=event.event_type,
                    scenes=event.scenes,
                    is_repeatable=event.is_repeatable,
                    cooldown_chapters=event.cooldown_chapters
                )
                
                if event_copy.check_trigger(state, memories):
                    self._triggered_events.add(event_key)
                    if self._state_id:
                        self._db.save_triggered_event(
                            self._state_id, event_key, "exclusive", state.chapter
                        )
                    return event_copy
        
        return None
    
    def _is_in_cooldown(self, event_key: str, event: CharacterExclusiveEvent, state: GameState) -> bool:
        if event.cooldown_chapters <= 0:
            return False
        
        events = self._db.get_triggered_events(self._state_id, event_key) if self._state_id else []
        if not events:
            return False
        
        last_trigger = max(events, key=lambda x: x['chapter_number'])
        return (state.chapter - last_trigger['chapter_number']) < event.cooldown_chapters
    
    def get_upcoming_events(self, state: GameState) -> List[Dict]:
        upcoming = []
        
        for character in state.characters:
            memories = self._memory_manager.get_all_memories(character.name)
            current_affection = state.get_affection(character.name)
            
            for event in self._event_configs:
                if event.character_name and event.character_name != character.name:
                    continue
                
                event_key = f"{event.id}_{character.name}"
                
                if not event.is_repeatable and event_key in self._triggered_events:
                    continue
                
                affection_needed = event.trigger_conditions.get("affection_min", 0)
                if current_affection < affection_needed:
                    diff = affection_needed - current_affection
                    upcoming.append({
                        "character": character.name,
                        "event_name": event.event_name,
                        "affection_needed": affection_needed,
                        "current_affection": current_affection,
                        "diff": diff,
                        "event_type": event.event_type
                    })
        
        upcoming.sort(key=lambda x: x["diff"])
        return upcoming[:3]


class DynamicEventManager:
    def __init__(self, db: GalgameDatabase):
        self._db = db
        self._event_pool: List[DynamicEvent] = []
        self._triggered_counts: Dict[str, int] = {}
        self._state_id: Optional[int] = None
        self._load_default_events()
    
    def set_state_id(self, state_id: int):
        self._state_id = state_id
        self._load_triggered_counts()
    
    def _load_triggered_counts(self):
        if self._state_id is None:
            return
        self._triggered_counts.clear()
        events = self._db.get_triggered_events(self._state_id)
        for event in events:
            event_id = event['event_id']
            self._triggered_counts[event_id] = self._triggered_counts.get(event_id, 0) + 1
    
    def _load_default_events(self):
        default_events = [
            DynamicEvent(
                id="rainy_day",
                event_name="雨天邂逅",
                description="下雨天遇到了某个角色",
                event_type="contextual",
                trigger_conditions=[{"weather": "rainy"}],
                base_probability=0.3,
                required_context={"weather": "rainy"},
                effects={"affection_random": 3},
                next_events=["shared_umbrella"],
                chain_probability=0.5
            ),
            DynamicEvent(
                id="shared_umbrella",
                event_name="共撑一把伞",
                description="和角色一起撑伞回家",
                event_type="chain",
                trigger_conditions=[],
                base_probability=0.0,
                required_context={},
                effects={"affection": 5},
                next_events=[],
                chain_probability=0.0
            ),
            DynamicEvent(
                id="lost_item",
                event_name="失物招领",
                description="角色捡到了主角丢失的物品",
                event_type="random",
                trigger_conditions=[],
                base_probability=0.15,
                required_context={},
                effects={"affection": 3, "currency": -10},
                next_events=["thank_you_gift"],
                chain_probability=0.3
            ),
            DynamicEvent(
                id="street_performance",
                event_name="街头表演",
                description="看到角色在街头表演",
                event_type="random",
                trigger_conditions=[],
                base_probability=0.1,
                required_context={"time_of_day": "evening"},
                effects={"currency": -20, "affection": 4},
                next_events=[],
                chain_probability=0.0
            ),
            DynamicEvent(
                id="exam_stress",
                event_name="考试压力",
                description="角色因为考试而焦虑",
                event_type="random",
                trigger_conditions=[],
                base_probability=0.2,
                required_context={},
                effects={"affection": 2},
                next_events=["study_together"],
                chain_probability=0.4
            ),
            DynamicEvent(
                id="study_together",
                event_name="一起学习",
                description="和角色一起复习功课",
                event_type="chain",
                trigger_conditions=[],
                base_probability=0.0,
                required_context={},
                effects={"affection": 5},
                next_events=[],
                chain_probability=0.0
            ),
            DynamicEvent(
                id="birthday_surprise",
                event_name="生日惊喜",
                description="为角色准备生日惊喜",
                event_type="scheduled",
                trigger_conditions=[{"special_date": "birthday"}],
                base_probability=1.0,
                required_context={"special_date": "birthday"},
                effects={"affection": 10, "currency": -50},
                next_events=[],
                chain_probability=0.0,
                max_triggers=1
            ),
        ]
        self._event_pool.extend(default_events)
    
    def generate_dynamic_event(
        self,
        state: GameState,
        context: EventContext
    ) -> Optional[DynamicEvent]:
        eligible_events = self._filter_eligible_events(state, context)
        
        if not eligible_events:
            return None
        
        weighted_events = []
        for event in eligible_events:
            probability = self._calculate_probability(event, state, context)
            weighted_events.append((event, probability))
        
        selected = self._weighted_random_choice(weighted_events)
        
        if selected:
            event_id = selected.id
            self._triggered_counts[event_id] = self._triggered_counts.get(event_id, 0) + 1
            
            if self._state_id:
                self._db.save_triggered_event(
                    self._state_id, event_id, "dynamic", state.chapter
                )
            
            if selected.next_events and random.random() < selected.chain_probability:
                pass
            
            return selected
        
        return None
    
    def _filter_eligible_events(
        self,
        state: GameState,
        context: EventContext
    ) -> List[DynamicEvent]:
        eligible = []
        
        for event in self._event_pool:
            triggered_count = self._triggered_counts.get(event.id, 0)
            if triggered_count >= event.max_triggers:
                continue
            
            if event.cooldown_chapters > 0:
                recent_events = [
                    e for e in (self._db.get_triggered_events(self._state_id, event.id) if self._state_id else [])
                    if state.chapter - e['chapter_number'] < event.cooldown_chapters
                ]
                if recent_events:
                    continue
            
            if event.event_type == "contextual":
                if context.weather != event.required_context.get("weather", context.weather):
                    continue
            
            if event.event_type == "scheduled":
                if context.special_date != event.required_context.get("special_date"):
                    continue
            
            eligible.append(event)
        
        return eligible
    
    def _calculate_probability(
        self,
        event: DynamicEvent,
        state: GameState,
        context: EventContext
    ) -> float:
        base_prob = event.base_probability
        
        context_multiplier = 1.0
        
        if event.required_context.get("weather") == context.weather:
            context_multiplier *= 1.5
        
        if event.required_context.get("time_of_day") == context.time_of_day:
            context_multiplier *= 1.3
        
        nearby_chars = event.required_context.get("characters", [])
        if nearby_chars and all(c in context.nearby_characters for c in nearby_chars):
            context_multiplier *= 2.0
        
        return min(1.0, base_prob * context_multiplier)
    
    def _weighted_random_choice(self, weighted_items: List[tuple]) -> Optional[DynamicEvent]:
        if not weighted_items:
            return None
        
        total_weight = sum(weight for _, weight in weighted_items)
        if total_weight <= 0:
            return None
        
        random_value = random.uniform(0, total_weight)
        current_weight = 0
        
        for item, weight in weighted_items:
            current_weight += weight
            if random_value <= current_weight:
                return item
        
        return weighted_items[-1][0]
    
    def get_event_content(self, event: DynamicEvent, character_name: str = "") -> Dict:
        scene_descriptions = {
            "rainy_day": f"天空突然下起了大雨，你正愁没带伞时，看到了{character_name}...",
            "shared_umbrella": f"{character_name}微笑着把伞递给你，你们并肩走在雨中...",
            "lost_item": f"你发现自己丢了东西，正着急时，{character_name}拿着它走了过来...",
            "street_performance": f"傍晚的街道上，你看到了{character_name}在表演...",
            "exam_stress": f"{character_name}看起来压力很大，原来是因为即将到来的考试...",
            "study_together": f"你决定和{character_name}一起复习，气氛意外地融洽...",
            "birthday_surprise": f"今天是{character_name}的生日，你准备了一个惊喜...",
        }
        
        return {
            "description": scene_descriptions.get(event.id, event.description),
            "event_name": event.event_name,
            "effects": event.effects
        }


class SpecialDateManager:
    def __init__(self):
        self._character_birthdays: Dict[str, str] = {}
        self._special_dates = {
            "02-14": {"name": "情人节", "events": ["valentine_confession", "valentine_date"]},
            "12-25": {"name": "圣诞节", "events": ["christmas_party", "christmas_gift"]},
            "01-01": {"name": "新年", "events": ["new_year_prayer", "new_year_party"]},
            "07-07": {"name": "七夕", "events": ["tanabata_wish"]},
            "10-31": {"name": "万圣节", "events": ["halloween_party"]},
        }
    
    def register_character_birthday(self, character_name: str, birthday: str):
        self._character_birthdays[character_name] = birthday
    
    def get_today_events(self) -> List[Dict]:
        today = datetime.now().strftime("%m-%d")
        events = []
        
        if today in self._special_dates:
            info = self._special_dates[today]
            events.append({
                "type": "holiday",
                "name": info["name"],
                "event_ids": info["events"]
            })
        
        for char_name, birthday in self._character_birthdays.items():
            if birthday == today:
                events.append({
                    "type": "birthday",
                    "name": f"{char_name}的生日",
                    "character": char_name,
                    "event_ids": [f"birthday_{char_name}"]
                })
        
        return events
    
    def is_special_date(self) -> bool:
        today = datetime.now().strftime("%m-%d")
        return today in self._special_dates or today in self._character_birthdays.values()
