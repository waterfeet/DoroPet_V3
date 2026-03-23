import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LyricLine:
    time_ms: int
    text: str
    
    def __lt__(self, other):
        return self.time_ms < other.time_ms


class LyricParser:
    METADATA_TAGS = ['ti', 'ar', 'al', 'by', 'ver', 'kuwo', 'offset', 'length', 're', 've']
    
    @staticmethod
    def parse(lrc_text: str) -> List[LyricLine]:
        if not lrc_text:
            return []
        
        lines = []
        
        for line in lrc_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            is_metadata = False
            for tag in LyricParser.METADATA_TAGS:
                if line_lower.startswith(f'[{tag}:'):
                    is_metadata = True
                    break
            
            if is_metadata:
                continue
            
            parsed_times = LyricParser._extract_times(line)
            if not parsed_times:
                continue
            
            text = LyricParser._extract_text(line)
            if not text:
                continue
            
            for time_ms in parsed_times:
                lines.append(LyricLine(time_ms=time_ms, text=text))
        
        lines.sort()
        return lines
    
    @staticmethod
    def _extract_times(line: str) -> List[int]:
        times = []
        
        pattern1 = r'\[(\d{1,2}):(\d{1,2})\.(\d{1,3})\]'
        for match in re.finditer(pattern1, line):
            minutes, seconds, ms = match.groups()
            time_ms = int(minutes) * 60 * 1000 + int(seconds) * 1000 + int(ms.ljust(3, '0')[:3])
            times.append(time_ms)
        
        if not times:
            pattern2 = r'\[(\d{1,2}):(\d{1,2})\]'
            for match in re.finditer(pattern2, line):
                minutes, seconds = match.groups()
                time_ms = int(minutes) * 60 * 1000 + int(seconds) * 1000
                times.append(time_ms)
        
        if not times:
            pattern3 = r'\[(\d{1,2}):(\d{1,2})\.(\d{1,2})\]'
            for match in re.finditer(pattern3, line):
                minutes, seconds, ms = match.groups()
                time_ms = int(minutes) * 60 * 1000 + int(seconds) * 1000 + int(ms) * 10
                times.append(time_ms)
        
        return times
    
    @staticmethod
    def _extract_text(line: str) -> str:
        text = re.sub(r'\[\d{1,2}:\d{1,2}(\.\d{1,3})?\]', '', line)
        return text.strip()
    
    @staticmethod
    def find_current_line(lines: List[LyricLine], current_time_ms: int) -> int:
        if not lines:
            return -1
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].time_ms <= current_time_ms:
                return i
        
        return -1
    
    @staticmethod
    def format_time(ms: int) -> str:
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
