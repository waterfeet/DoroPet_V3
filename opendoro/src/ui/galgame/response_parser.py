import re
from typing import Dict, List, Tuple
from src.core.logger import logger


class ResponseParser:
    STORY_PATTERN = r'\[故事\](.*?)\[/故事\]'
    CHOICE_PATTERN = r'\[选择(\d+)\](.*?)\[/选择\d+\]'
    CHOICE_PATTERN_ALT = r'\[选择(\d+)\](.*?)(?=\[选择\d+\]|\[好感度\]|\[货币\]|$)'
    AFFECTION_PATTERN = r'\[好感度\](.*?)\[/好感度\]|\[好感度\](.*?)(?=\[货币\]|$)'
    CURRENCY_PATTERN = r'\[货币\](.*?)\[/货币\]|\[货币\](.*?)(?=$)'
    
    @classmethod
    def parse(cls, response: str) -> Dict:
        result = {
            "story": "",
            "choices": [],
            "affection_changes": {},
            "currency_change": 0
        }
        
        # 优先提取 [故事]...[/故事] 标签内的内容
        story_match = re.search(cls.STORY_PATTERN, response, re.DOTALL)
        if story_match:
            result["story"] = story_match.group(1).strip()
        else:
            # 如果没有故事标签，使用旧的解析方式
            story = response
            
            # 去除 markdown 标题 (## 标题)
            story = re.sub(r'^#{1,6}\s+.*$', '', story, flags=re.MULTILINE)
            
            # 去除选择标签及其内容
            story = re.sub(r'\[选择\d+\].*?\[/选择\d+\]', '', story, flags=re.DOTALL)
            story = re.sub(r'\[选择\d+\].*?(?=\[选择\d+\]|\[好感度\]|\[货币\]|$)', '', story, flags=re.DOTALL)
            
            # 去除好感度标签及其内容
            story = re.sub(r'\[好感度\].*?\[/好感度\]', '', story, flags=re.DOTALL)
            story = re.sub(r'\[好感度\].*?(?=\[货币\]|$)', '', story, flags=re.DOTALL)
            
            # 去除货币标签及其内容
            story = re.sub(r'\[货币\].*?\[/货币\]', '', story, flags=re.DOTALL)
            story = re.sub(r'\[货币\].*?$', '', story, flags=re.DOTALL)
            
            # 去除多余空行
            story = re.sub(r'\n{3,}', '\n\n', story)
            result["story"] = story.strip()
        
        # 提取选择项 - 先尝试带结束标签的格式
        choices = re.findall(cls.CHOICE_PATTERN, response, re.DOTALL)
        if choices:
            for idx, choice_text in choices:
                choice_text = choice_text.strip()
                if choice_text:
                    result["choices"].append({
                        "id": int(idx),
                        "text": choice_text
                    })
        else:
            # 尝试不带结束标签的格式
            alt_choices = re.findall(cls.CHOICE_PATTERN_ALT, response, re.DOTALL)
            for idx, choice_text in alt_choices:
                choice_text = choice_text.strip()
                if choice_text:
                    result["choices"].append({
                        "id": int(idx),
                        "text": choice_text
                    })
        
        # 提取好感度变化
        affection_text = re.search(cls.AFFECTION_PATTERN, response, re.DOTALL)
        if affection_text:
            text = affection_text.group(1) or affection_text.group(2) or ""
            result["affection_changes"] = cls._parse_affection(text)
        
        # 提取货币变化
        currency_text = re.search(cls.CURRENCY_PATTERN, response, re.DOTALL)
        if currency_text:
            text = currency_text.group(1) or currency_text.group(2) or ""
            result["currency_change"] = cls._parse_currency(text)
        
        if not result["choices"]:
            result["choices"] = cls._generate_default_choices()
        
        logger.debug(f"Parsed response: {len(result['choices'])} choices, affection: {result['affection_changes']}, currency: {result['currency_change']}")
        
        return result
    
    @classmethod
    def _parse_affection(cls, text: str) -> Dict[str, int]:
        changes = {}
        patterns = [
            r'(\w+)\s*([+-]\d+)',
            r'(\w+)[:：]\s*([+-]?\d+)',
            r'(\w+)\s*增加\s*(\d+)',
            r'(\w+)\s*减少\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for name, change in matches:
                name = name.strip()
                change_val = int(change)
                if '减少' in text or (change.startswith('-') and len(change) > 1):
                    change_val = -abs(int(change.replace('-', '')))
                elif '增加' in text:
                    change_val = abs(int(change))
                if name:
                    changes[name] = change_val
        
        return changes
    
    @classmethod
    def _parse_currency(cls, text: str) -> int:
        match = re.search(r'([+-]?\d+)', text)
        if match:
            return int(match.group(1))
        
        if '获得' in text or '增加' in text:
            match = re.search(r'(\d+)', text)
            return int(match.group(1)) if match else 0
        elif '失去' in text or '减少' in text or '花费' in text:
            match = re.search(r'(\d+)', text)
            return -int(match.group(1)) if match else 0
        
        return 0
    
    @classmethod
    def _generate_default_choices(cls) -> List[Dict]:
        return [
            {"id": 1, "text": "继续前进"},
            {"id": 2, "text": "停下来观察"},
            {"id": 3, "text": "寻找其他路径"}
        ]
    
    @classmethod
    def extract_character_name(cls, text: str) -> Tuple[str, str]:
        patterns = [
            r'^【(.+?)】(.*)$',
            r'^「(.+?)」(.*)$',
            r'^\[(.+?)\](.*)$',
            r'^(\w+)[：:](.*)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip(), match.group(2).strip()
        
        return "", text
    
    @classmethod
    def parse_dialogue(cls, content: str) -> List[Dict]:
        dialogues = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            char_name, text = cls.extract_character_name(line)
            if char_name:
                dialogues.append({
                    "type": "dialogue",
                    "character": char_name,
                    "text": text
                })
            else:
                dialogues.append({
                    "type": "narration",
                    "text": line
                })
        
        return dialogues
    
    @classmethod
    def validate_response(cls, parsed: Dict) -> bool:
        if not parsed.get("story"):
            return False
        if not parsed.get("choices"):
            return False
        return True
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        # 流式输出处理：处理不完整的标签
        
        # 如果包含 [故事] 标签开始
        if '[故事]' in text:
            # 如果也有 [/故事] 结束标签，提取完整故事
            if '[/故事]' in text:
                story_match = re.search(r'\[故事\](.*?)\[/故事\]', text, re.DOTALL)
                if story_match:
                    return story_match.group(1).strip()
            else:
                # 只有开始标签，提取标签之后的内容
                idx = text.index('[故事]')
                return text[idx + 5:].strip()
        
        # 如果包含 [/故事] 结束标签（但没有开始标签，说明开始标签在之前的文本中）
        if '[/故事]' in text:
            idx = text.index('[/故事]')
            return text[:idx].strip()
        
        # 如果包含任何选择、好感度、货币标签，返回空（不显示）
        if '[选择' in text or '[好感度]' in text or '[货币]' in text:
            return ''
        
        # 去除 markdown 标题
        text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)
        # 去除选择标签（带结束标签）
        text = re.sub(r'\[选择\d+\].*?\[/选择\d+\]', '', text, flags=re.DOTALL)
        # 去除选择标签（不带结束标签）
        text = re.sub(r'\[选择\d+\]', '', text)
        text = re.sub(r'\[/选择\d+\]', '', text)
        text = re.sub(r'\[选择\]', '', text)
        text = re.sub(r'\[/选择\]', '', text)
        # 去除好感度和货币标签
        text = re.sub(r'\[好感度\].*?\[/好感度\]', '', text, flags=re.DOTALL)
        text = re.sub(r'\[好感度\].*?(?=\[货币\]|$)', '', text, flags=re.DOTALL)
        text = re.sub(r'\[货币\].*?\[/货币\]', '', text, flags=re.DOTALL)
        text = re.sub(r'\[货币\].*?$', '', text, flags=re.DOTALL)
        # 去除故事标签本身
        text = re.sub(r'\[故事\]', '', text)
        text = re.sub(r'\[/故事\]', '', text)
        # 去除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


class StreamingParser:
    def __init__(self):
        self.buffer = ""
        self.story_start = False
        self.story_end = False
        self.choices_start = False
        self.current_choice = ""
        self.choices = []
        self.affection_start = False
        self.affection_text = ""
        self.currency_start = False
        self.currency_text = ""
        self.story_parts = []
    
    def feed(self, chunk: str) -> Dict:
        self.buffer += chunk
        result = {
            "story_chunk": "",
            "complete": False
        }
        
        # 检测 [故事] 标签开始
        if '[故事]' in self.buffer and not self.story_start:
            before_story = self.buffer[:self.buffer.index('[故事]')]
            if before_story.strip():
                self.story_parts.append(before_story)
            self.story_start = True
            self.buffer = self.buffer[self.buffer.index('[故事]') + 5:]
        
        # 检测 [/故事] 标签结束
        if self.story_start and '[/故事]' in self.buffer and not self.story_end:
            story_part = self.buffer[:self.buffer.index('[/故事]')]
            result["story_chunk"] = story_part
            self.story_parts.append(story_part)
            self.story_end = True
            self.buffer = self.buffer[self.buffer.index('[/故事]') + 6:]
        
        # 如果故事标签还没开始，直接输出
        if not self.story_start:
            result["story_chunk"] = chunk
        
        # 如果在故事标签内，继续输出
        elif self.story_start and not self.story_end:
            result["story_chunk"] = chunk
        
        # 故事结束后，检测选择
        if self.story_end and '[选择' in self.buffer and not self.choices_start:
            self.choices_start = True
        
        if self.choices_start:
            if '[好感度]' in self.buffer:
                choice_part = self.buffer[:self.buffer.index('[好感度')]
                self._parse_choices_in_buffer(choice_part)
                self.affection_start = True
                self.buffer = self.buffer[self.buffer.index('[好感度'):]
            elif '[货币]' in self.buffer:
                choice_part = self.buffer[:self.buffer.index('[货币')]
                self._parse_choices_in_buffer(choice_part)
                self.currency_start = True
                self.buffer = self.buffer[self.buffer.index('[货币'):]
            else:
                self._parse_choices_in_buffer(self.buffer)
        
        if self.affection_start:
            if '[货币]' in self.buffer:
                self.affection_text = self.buffer[:self.buffer.index('[货币')]
                self.currency_start = True
                self.buffer = self.buffer[self.buffer.index('[货币'):]
            else:
                self.affection_text = self.buffer
        
        if self.currency_start:
            self.currency_text = self.buffer
        
        return result
    
    def _parse_choices_in_buffer(self, text: str):
        # 先尝试带结束标签的格式
        pattern = r'\[选择(\d+)\](.*?)\[/选择\d+\]'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            for idx, choice_text in matches:
                existing_ids = [c['id'] for c in self.choices]
                if int(idx) not in existing_ids:
                    self.choices.append({
                        "id": int(idx),
                        "text": choice_text.strip()
                    })
        else:
            # 尝试不带结束标签的格式
            pattern = r'\[选择(\d+)\](.*?)(?=\[选择\d+\]|$)'
            matches = re.findall(pattern, text, re.DOTALL)
            for idx, choice_text in matches:
                existing_ids = [c['id'] for c in self.choices]
                if int(idx) not in existing_ids:
                    self.choices.append({
                        "id": int(idx),
                        "text": choice_text.strip()
                    })
    
    def finalize(self) -> Dict:
        story = ''.join(self.story_parts)
        
        # 去除 markdown 标题
        story = re.sub(r'^#{1,6}\s+.*$', '', story, flags=re.MULTILINE)
        # 去除多余空行
        story = re.sub(r'\n{3,}', '\n\n', story)
        
        affection_changes = {}
        if self.affection_text:
            # 去除标签
            aff_text = re.sub(r'\[好感度\]', '', self.affection_text)
            aff_text = re.sub(r'\[/好感度\]', '', aff_text)
            affection_changes = ResponseParser._parse_affection(aff_text)
        
        currency_change = 0
        if self.currency_text:
            # 去除标签
            curr_text = re.sub(r'\[货币\]', '', self.currency_text)
            curr_text = re.sub(r'\[/货币\]', '', curr_text)
            currency_change = ResponseParser._parse_currency(curr_text)
        
        if not self.choices:
            self.choices = ResponseParser._generate_default_choices()
        
        return {
            "story": story.strip(),
            "choices": self.choices,
            "affection_changes": affection_changes,
            "currency_change": currency_change
        }
