"""Stream Processor - Handles LLM streaming response parsing and buffering."""

import time
import re
import json
import xml.etree.ElementTree as ET
from typing import Optional, Callable, Dict, Any, Tuple, List
from dataclasses import dataclass, field
from enum import Enum, auto
from PyQt5.QtCore import QObject, pyqtSignal


class StreamState(Enum):
    IDLE = auto()
    CONTENT = auto()
    THINKING = auto()
    TOOL_CALL = auto()


@dataclass
class StreamChunk:
    content: str = ""
    reasoning: str = ""
    tool_call_id: str = ""
    tool_call_name: str = ""
    tool_call_args: str = ""
    tool_call_index: int = -1
    is_content: bool = False
    is_reasoning: bool = False
    is_tool_call: bool = False


@dataclass
class StreamBuffer:
    content: str = ""
    reasoning: str = ""
    pending_emit: str = ""
    last_emit_time: float = 0
    emit_threshold: int = 10
    emit_interval: float = 0.05


class StreamProcessor(QObject):
    chunk_ready = pyqtSignal(str)
    thinking_start = pyqtSignal()
    thinking_chunk = pyqtSignal(str)
    thinking_end = pyqtSignal()
    content_chunk = pyqtSignal(str)
    tool_call_start = pyqtSignal(int, str)
    tool_call_chunk = pyqtSignal(int, str)
    tool_call_complete = pyqtSignal(int, str, str, str)
    stream_complete = pyqtSignal(str, str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = StreamState.IDLE
        self.buffer = StreamBuffer()
        self.full_content = ""
        self.full_reasoning = ""
        self.current_turn_content = ""
        self.current_turn_reasoning = ""
        self.tool_calls_buffer: Dict[int, Dict[str, Any]] = {}
        self._is_stopped = False
    
    def reset(self):
        self.state = StreamState.IDLE
        self.buffer = StreamBuffer()
        self.full_content = ""
        self.full_reasoning = ""
        self.current_turn_content = ""
        self.current_turn_reasoning = ""
        self.tool_calls_buffer = {}
        self._is_stopped = False
    
    def stop(self):
        self._is_stopped = True
        self._flush_buffer()
    
    def process_chunk(self, delta) -> Optional[StreamChunk]:
        if self._is_stopped:
            return None
        
        chunk = self._parse_delta(delta)
        
        if chunk.is_reasoning:
            self._handle_reasoning(chunk)
        elif chunk.is_content:
            self._handle_content(chunk)
        elif chunk.is_tool_call:
            self._handle_tool_call(chunk)
        
        return chunk
    
    def _parse_delta(self, delta) -> StreamChunk:
        chunk = StreamChunk()
        
        reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        if reasoning is None:
            if hasattr(delta, 'model_extra') and delta.model_extra:
                reasoning = delta.model_extra.get('reasoning_content') or delta.model_extra.get('reasoning')
            elif hasattr(delta, '__dict__'):
                reasoning = delta.__dict__.get('reasoning_content') or delta.__dict__.get('reasoning')
        
        if reasoning:
            chunk.is_reasoning = True
            chunk.reasoning = reasoning
        
        if delta.content:
            chunk.is_content = True
            chunk.content = delta.content
        
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            for tc in delta.tool_calls:
                tc_chunk = StreamChunk()
                tc_chunk.is_tool_call = True
                tc_chunk.tool_call_index = tc.index if tc.index is not None else 0
                if tc.id:
                    tc_chunk.tool_call_id = tc.id
                if tc.function:
                    if tc.function.name:
                        tc_chunk.tool_call_name = tc.function.name
                    if tc.function.arguments:
                        tc_chunk.tool_call_args = tc.function.arguments
                self._handle_tool_call(tc_chunk)
        
        return chunk
    
    def _handle_reasoning(self, chunk: StreamChunk):
        if self.state != StreamState.THINKING:
            self._flush_buffer()
            self._transition_to_thinking()
        
        self.buffer.reasoning += chunk.reasoning
        self.full_reasoning += chunk.reasoning
        self.current_turn_reasoning += chunk.reasoning
        self.buffer.pending_emit += chunk.reasoning
        
        self._try_emit_buffer()
    
    def _handle_content(self, chunk: StreamChunk):
        if self.state == StreamState.THINKING:
            self._flush_buffer()
            self._transition_from_thinking()
        
        if self.state != StreamState.CONTENT:
            self.state = StreamState.CONTENT
        
        self.buffer.content += chunk.content
        self.full_content += chunk.content
        self.current_turn_content += chunk.content
        self.buffer.pending_emit += chunk.content
        
        self._try_emit_buffer()
    
    def _handle_tool_call(self, chunk: StreamChunk):
        if self.state == StreamState.THINKING:
            self._flush_buffer()
            self._transition_from_thinking()
        
        self.state = StreamState.TOOL_CALL
        
        idx = chunk.tool_call_index
        if idx not in self.tool_calls_buffer:
            self.tool_calls_buffer[idx] = {
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""}
            }
            self.tool_call_start.emit(idx, chunk.tool_call_name)
        
        if chunk.tool_call_id:
            self.tool_calls_buffer[idx]["id"] = chunk.tool_call_id
        if chunk.tool_call_name:
            self.tool_calls_buffer[idx]["function"]["name"] += chunk.tool_call_name
        if chunk.tool_call_args:
            self.tool_calls_buffer[idx]["function"]["arguments"] += chunk.tool_call_args
            self.tool_call_chunk.emit(idx, chunk.tool_call_args)
    
    def _transition_to_thinking(self):
        self.state = StreamState.THINKING
        self.thinking_start.emit()
    
    def _transition_from_thinking(self):
        self.thinking_end.emit()
        self.state = StreamState.CONTENT
    
    def _try_emit_buffer(self):
        current_time = time.time()
        should_emit = (
            len(self.buffer.pending_emit) >= self.buffer.emit_threshold or
            (current_time - self.buffer.last_emit_time) > self.buffer.emit_interval
        )
        
        if should_emit and self.buffer.pending_emit:
            if self.state == StreamState.THINKING:
                self.thinking_chunk.emit(self.buffer.pending_emit)
            else:
                self.chunk_ready.emit(self.buffer.pending_emit)
            self.buffer.pending_emit = ""
            self.buffer.last_emit_time = current_time
    
    def _flush_buffer(self):
        if self.buffer.pending_emit:
            if self.state == StreamState.THINKING:
                self.thinking_chunk.emit(self.buffer.pending_emit)
            else:
                self.chunk_ready.emit(self.buffer.pending_emit)
            self.buffer.pending_emit = ""
    
    def _parse_xml_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        from src.core.agent_tools import AVAILABLE_TOOLS, _get_skill_manager
        import logging
        import xml.etree.ElementTree as ET
        logger = logging.getLogger("DoroPet")
        
        xml_tool_calls = []
        
        valid_tools = set(AVAILABLE_TOOLS.keys())
        skill_manager = _get_skill_manager()
        skill_schemas = skill_manager.get_tool_schemas()
        for schema in skill_schemas:
            valid_tools.add(schema["function"]["name"])
        
        logger.info(f"[StreamProcessor] Parsing XML tool calls from content (length {len(content)}): {content[:200]}...")
        
        try:
            wrapped_content = f"<root>{content}</root>"
            root = ET.fromstring(wrapped_content)
            
            for tool_elem in root:
                if tool_elem.tag not in valid_tools:
                    logger.info(f"[StreamProcessor] Skipping <{tool_elem.tag}> - not in valid tools")
                    continue
                
                tool_name = tool_elem.tag
                args = {}
                
                for arg_elem in tool_elem:
                    args[arg_elem.tag] = arg_elem.text if arg_elem.text else ""
                
                if not args and tool_elem.text:
                    args = {"input": tool_elem.text.strip()}
                
                xml_tool_calls.append({
                    "id": f"call_{len(xml_tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args, ensure_ascii=False)
                    }
                })
                logger.info(f"[StreamProcessor] Successfully parsed tool: {tool_name} with args: {args}")
        except ET.ParseError as e:
            logger.error(f"[StreamProcessor] XML parse error: {e}")
        
        logger.info(f"[StreamProcessor] Total XML tool calls parsed: {len(xml_tool_calls)}")
        return xml_tool_calls
    
    def _clean_xml_tool_calls(self, content: str) -> str:
        pattern = r'<(\w+)>(.*?)</\1>'
        cleaned_content = re.sub(pattern, '', content, flags=re.DOTALL)
        return cleaned_content.strip()
    
    def finalize(self) -> Tuple[str, str, str, Dict[int, Dict[str, Any]]]:
        self._flush_buffer()
        
        if self.state == StreamState.THINKING:
            self.thinking_end.emit()
        
        xml_tool_calls = self._parse_xml_tool_calls(self.current_turn_content)
        
        if xml_tool_calls:
            next_index = max(self.tool_calls_buffer.keys()) + 1 if self.tool_calls_buffer else 0
            for i, tool_call in enumerate(xml_tool_calls):
                self.tool_calls_buffer[next_index + i] = tool_call
            
            self.current_turn_content = self._clean_xml_tool_calls(self.current_turn_content)
            if not self.current_turn_content:
                self.current_turn_content = ""
        
        self.state = StreamState.IDLE
        
        return self.full_content, self.current_turn_content, self.current_turn_reasoning, self.tool_calls_buffer
    
    def get_tool_calls(self) -> list:
        sorted_indices = sorted(self.tool_calls_buffer.keys())
        return [self.tool_calls_buffer[idx] for idx in sorted_indices]
    
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls_buffer) > 0
