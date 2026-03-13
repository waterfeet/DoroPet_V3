"""Message Parser Module - Parse and cache message content into structured blocks."""

import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


class ContentType(Enum):
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"


@dataclass
class ContentBlock:
    type: ContentType
    content: str
    language: Optional[str] = None
    
    def is_code(self) -> bool:
        return self.type == ContentType.CODE
    
    def is_text(self) -> bool:
        return self.type == ContentType.TEXT

    def is_thinking(self) -> bool:
        return self.type == ContentType.THINKING
    
    def is_tool_call(self) -> bool:
        return self.type == ContentType.TOOL_CALL


class MessageParser:
    THINKING_START = chr(60) + chr(116) + chr(104) + chr(105) + chr(110) + chr(107) + chr(62)
    THINKING_END = chr(60) + chr(47) + chr(116) + chr(104) + chr(105) + chr(110) + chr(107) + chr(62)
    
    # Also support the "riode" internal tags if they are used for real-time display
    RIODE_THINK_START = "riodeThink>"
    RIODE_THINK_END = "riodeThinkEnd>"

    CODE_BLOCK_PATTERN = re.compile(r'```(?:([\w\+\-\.]+))?\n([\s\S]*?)```')
    
    @classmethod
    def _get_thinking_pattern(cls):
        # Support both standard <think> and internal riodeThink tags
        pattern_str = f"({cls.THINKING_START}|{cls.RIODE_THINK_START})(.*?)({cls.THINKING_END}|{cls.RIODE_THINK_END})"
        return re.compile(pattern_str, re.DOTALL)
    
    @classmethod
    def parse(cls, raw_content: str) -> Tuple[Optional[str], List[ContentBlock]]:
        thinking_content = None
        display_content = raw_content
        
        pattern = cls._get_thinking_pattern()
        thinking_match = pattern.search(raw_content)
        if thinking_match:
            thinking_content = thinking_match.group(2).strip()
            # Replace the thinking block with an empty string for display content parsing
            display_content = pattern.sub('', raw_content)
        
        blocks = cls._parse_display_content(display_content.strip())
        
        # If we found thinking content, we can also add it as a block if needed, 
        # but the current UI uses a separate thinking_content return value.
        
        return thinking_content, blocks
    
    @classmethod
    def _parse_display_content(cls, content: str) -> List[ContentBlock]:
        blocks = []
        
        parts = re.split(r'(```(?:[\w\+\-\.]+)?\n[\s\S]*?```)', content)
        
        for part in parts:
            if not part.strip():
                continue
                
            if part.startswith('```') and part.endswith('```'):
                code_block = cls._parse_code_block(part)
                if code_block:
                    blocks.append(code_block)
            else:
                text = part.strip()
                if text:
                    blocks.append(ContentBlock(
                        type=ContentType.TEXT,
                        content=text
                    ))
        
        return blocks
    
    @classmethod
    def _parse_code_block(cls, block: str) -> Optional[ContentBlock]:
        lines = block.split('\n')
        if len(lines) < 2:
            return None
            
        first_line = lines[0]
        lang = first_line.strip('`').strip()
        code = '\n'.join(lines[1:-1])
        
        return ContentBlock(
            type=ContentType.CODE,
            content=code,
            language=lang
        )
    
    @classmethod
    def extract_thinking(cls, content: str) -> Tuple[Optional[str], str]:
        pattern = cls._get_thinking_pattern()
        thinking_match = pattern.search(content)
        
        if thinking_match:
            thinking_text = thinking_match.group(1).strip()
            display_text = pattern.sub('', content).strip()
            return thinking_text, display_text
        
        return None, content.strip()
    
    @classmethod
    def has_code_blocks(cls, content: str) -> bool:
        return bool(cls.CODE_BLOCK_PATTERN.search(content))
    
    @classmethod
    def get_code_blocks(cls, content: str) -> List[Tuple[str, str]]:
        blocks = []
        for match in cls.CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1) or ""
            code = match.group(2)
            blocks.append((lang, code))
        return blocks


class MessageCache:
    _instance = None
    _cache: dict = {}
    _max_size: int = 100
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get(self, msg_id: int) -> Optional[Tuple[Optional[str], List[ContentBlock]]]:
        return self._cache.get(msg_id)
    
    def set(self, msg_id: int, thinking: Optional[str], blocks: List[ContentBlock]):
        if len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[msg_id] = (thinking, blocks)
    
    def invalidate(self, msg_id: int):
        self._cache.pop(msg_id, None)
    
    def clear(self):
        self._cache.clear()
    
    def get_or_parse(self, msg_id: int, raw_content: str) -> Tuple[Optional[str], List[ContentBlock]]:
        cached = self.get(msg_id)
        if cached is not None:
            return cached
        
        thinking, blocks = MessageParser.parse(raw_content)
        self.set(msg_id, thinking, blocks)
        return thinking, blocks
