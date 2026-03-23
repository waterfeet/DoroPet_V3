import re
import html
import base64
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexers.special import TextLexer
from pygments.formatters import HtmlFormatter

from src.core.logger import logger
from src.core.quick_chat_state import QuickChatState, get_quick_chat_state, GenerationState
from src.core.quick_chat_dependencies import get_quick_chat_deps


class MarkdownRenderer:
    def __init__(self, is_dark: bool = True):
        self.is_dark = is_dark
        self._update_style_config()

    def _update_style_config(self):
        if self.is_dark:
            self.style_name = 'one-dark'
            self.bg_color = "#282c34"
            self.header_bg = "#21252b"
            self.border_color = "#181a1f"
            self.text_color = "#abb2bf"
        else:
            self.style_name = 'xcode'
            self.bg_color = "#f6f8fa"
            self.header_bg = "#e1e4e8"
            self.border_color = "#d1d5da"
            self.text_color = "#24292e"

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._update_style_config()

    def render(self, text: str) -> str:
        extensions = ['fenced_code', 'tables']
        try:
            text = self._preprocess_image_urls(text)
            markdown_html = markdown.markdown(text, extensions=extensions)
            markdown_html = self._process_code_blocks(markdown_html)
            custom_css = self._generate_custom_css()
            return custom_css + markdown_html
        except Exception as e:
            logger.error(f"[MarkdownRenderer] 渲染失败: {e}")
            return f"<pre>{text}</pre>"

    def _preprocess_image_urls(self, text: str) -> str:
        bare_image_pattern = re.compile(r'!\s*`([^`]+)`')
        text = bare_image_pattern.sub(r'![](\1)', text)
        http_image_pattern = re.compile(r'(https?://[^\s<>"\']+\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?[^\s<>"\']*)?)', re.IGNORECASE)
        text = http_image_pattern.sub(r'![](\1)', text)
        return text

    def _process_code_blocks(self, markdown_html: str) -> str:
        def replace_block(match):
            lang = match.group('lang')
            code_content = match.group('code')
            clean_code = html.unescape(code_content)

            try:
                lexer = get_lexer_by_name(lang) if lang else guess_lexer(clean_code)
            except:
                lexer = TextLexer()

            formatter = HtmlFormatter(style=self.style_name, noclasses=True)
            highlighted_html = highlight(clean_code, lexer, formatter)

            start_idx = highlighted_html.find('<pre')
            end_idx = highlighted_html.rfind('</pre>') + 6

            pre_content = highlighted_html[start_idx:end_idx] if start_idx != -1 else f'<pre>{code_content}</pre>'

            pre_content = re.sub(
                r'<pre[^>]*>',
                f'<pre style="margin: 0; padding: 8px; background-color: {self.bg_color}; color: {self.text_color}; white-space: pre-wrap; font-family: Consolas, monospace; border-radius: 4px;">',
                pre_content,
                count=1
            )

            lang_display = lang if lang else "Code"

            return (
                f'<div style="margin: 8px 0; border: 1px solid {self.border_color}; border-radius: 6px; overflow: hidden;">'
                f'<div style="background-color: {self.header_bg}; padding: 6px 12px; border-bottom: 1px solid {self.border_color};">'
                f'<span style="color: {self.text_color}; font-family: sans-serif; font-size: 11px; font-weight: bold;">{lang_display}</span>'
                f'</div>'
                f'<div style="background-color: {self.bg_color}; padding: 0;">{pre_content}</div>'
                f'</div>'
            )

        pattern = r'<pre><code class="language-(?P<lang>\w*)">(?P<code>.*?)</code></pre>'
        markdown_html = re.sub(pattern, replace_block, markdown_html, flags=re.DOTALL)

        pattern_no_lang = r'<pre><code>(?P<code>.*?)</code></pre>'
        markdown_html = re.sub(pattern_no_lang, replace_block, markdown_html, flags=re.DOTALL)

        return markdown_html

    def _generate_custom_css(self) -> str:
        return f"""
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 13px; line-height: 1.5; color: {self.text_color}; }}
            p {{ margin: 0.5em 0; }}
            h1, h2, h3, h4, h5, h6 {{ margin: 0.8em 0 0.4em 0; font-weight: 600; }}
            ul, ol {{ margin: 0.5em 0; padding-left: 1.5em; }}
            li {{ margin: 0.2em 0; }}
            blockquote {{ border-left: 3px solid {self.border_color}; margin: 0.5em 0; padding-left: 1em; color: #666; }}
            code {{ background-color: {self.bg_color}; padding: 2px 6px; border-radius: 3px; font-family: Consolas, monospace; font-size: 12px; }}
            table {{ border-collapse: collapse; margin: 0.5em 0; }}
            th, td {{ border: 1px solid {self.border_color}; padding: 6px 12px; }}
            th {{ background-color: {self.header_bg}; }}
            img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 8px 0; }}
        </style>
        """


class QuickChatSessionManager:
    SESSION_TITLE = "沉浸聊天"

    def __init__(self, chat_db, state: QuickChatState):
        self.chat_db = chat_db
        self._state = state
        self.current_session_id: Optional[int] = None

    def get_or_create_session(self) -> Optional[int]:
        if self.current_session_id:
            return self.current_session_id

        cursor = self.chat_db.conn.cursor()
        cursor.execute("SELECT id, title FROM sessions WHERE title = ?", (self.SESSION_TITLE,))

        row = cursor.fetchone()
        if row:
            self.current_session_id = row[0]
            self._state.session_id = self.current_session_id
            logger.info(f"[QuickChatSessionManager] 找到沉浸聊天会话：id={self.current_session_id}")
            return self.current_session_id

        self.current_session_id = self.chat_db.create_session(
            self.SESSION_TITLE,
            "You are a helpful assistant."
        )
        self._state.session_id = self.current_session_id
        logger.info(f"[QuickChatSessionManager] 创建沉浸聊天会话：id={self.current_session_id}")
        return self.current_session_id

    def add_message(self, role: str, content: str, images: Optional[List[str]] = None) -> Optional[int]:
        session_id = self.get_or_create_session()
        if not session_id:
            return None

        msg_id = self.chat_db.add_message(session_id, role, content, images=images)
        logger.info(f"[QuickChatSessionManager] 添加消息：msg_id={msg_id}, role={role}")
        return msg_id

    def get_messages(self) -> List[Tuple]:
        session_id = self.get_or_create_session()
        if not session_id:
            return []

        return self.chat_db.get_messages(session_id)

    def delete_message(self, msg_id: int) -> bool:
        try:
            self.chat_db.delete_message(msg_id)
            logger.info(f"[QuickChatSessionManager] 删除消息：msg_id={msg_id}")
            return True
        except Exception as e:
            logger.error(f"[QuickChatSessionManager] 删除消息失败：{e}")
            return False

    def delete_messages_from(self, msg_id: int) -> List[int]:
        session_id = self.get_or_create_session()
        if not session_id:
            return []

        msgs = self.chat_db.get_messages(session_id)

        target_idx = -1
        for i, m in enumerate(msgs):
            if m[0] == msg_id:
                target_idx = i
                break

        if target_idx == -1:
            return []

        ids_to_delete = [m[0] for m in msgs[target_idx:]]
        for mid in ids_to_delete:
            self.chat_db.delete_message(mid)

        logger.info(f"[QuickChatSessionManager] 删除消息：{ids_to_delete}")
        return ids_to_delete


class QuickChatToolManager:
    DEFAULT_TOOLS = {
        "search": False,
        "image": False,
        "coding": False,
        "file": False
    }

    TOOL_NAMES = {
        "search": "联网搜索",
        "image": "图片生成",
        "coding": "代码执行",
        "file": "文件操作"
    }

    def __init__(self, state: QuickChatState):
        self._state = state
        self._state.tool_states = self.DEFAULT_TOOLS.copy()

    def toggle_tool(self, tool_name: str, enabled: bool) -> bool:
        if tool_name in self._state.tool_states or tool_name.startswith("skill:"):
            self._state.toggle_tool(tool_name, enabled)
            status = "启用" if enabled else "禁用"
            logger.info(f"[QuickChatToolManager] {status}工具：{tool_name}")
            return True
        return False

    def get_enabled_tools(self) -> List[str]:
        return self._state.get_enabled_tools()

    def is_tool_enabled(self, tool_name: str) -> bool:
        return self._state.is_tool_enabled(tool_name)

    def get_tool_display_name(self, tool_name: str) -> str:
        return self.TOOL_NAMES.get(tool_name, tool_name)

    def get_enabled_tool_names(self) -> List[str]:
        enabled = self._state.get_enabled_tools()
        return [self.TOOL_NAMES.get(t, t) for t in enabled if not t.startswith("skill:")]

    def load_from_settings(self, settings):
        for tool_name in self.DEFAULT_TOOLS.keys():
            saved_value = settings.value(f"tool_{tool_name}_enabled", None)
            if saved_value is not None:
                enabled = saved_value if isinstance(saved_value, bool) else (str(saved_value).lower() == 'true')
                self._state.tool_states[tool_name] = enabled

    def save_to_settings(self, settings):
        for tool_name, enabled in self._state.tool_states.items():
            if not tool_name.startswith("skill:"):
                settings.setValue(f"tool_{tool_name}_enabled", enabled)


class QuickPhraseManager:
    DEFAULT_PHRASES = [
        "早上好！",
        "你好呀~",
        "陪我聊天~",
        "记得吃饭哦~",
        "别太累了",
        "今天心情怎么样？",
        "给我讲个故事",
        "我们来玩游戏吧",
    ]

    SETTINGS_KEY = "custom_quick_phrases"

    def __init__(self):
        self.default_phrases = self.DEFAULT_PHRASES.copy()
        self.custom_phrases: List[str] = []

    def get_all_phrases(self) -> List[str]:
        all_phrases = []
        seen = set()
        for phrase in self.default_phrases + self.custom_phrases:
            if phrase not in seen:
                all_phrases.append(phrase)
                seen.add(phrase)
        return all_phrases

    def load_from_settings(self, settings):
        saved_phrases = settings.value(self.SETTINGS_KEY, [])
        if not isinstance(saved_phrases, list):
            saved_phrases = saved_phrases.split('||') if saved_phrases else []
        self.custom_phrases = [p for p in saved_phrases if p.strip()]

    def save_to_settings(self, settings, phrases: List[str]):
        self.custom_phrases = [p.strip() for p in phrases if p.strip()]
        settings.setValue(self.SETTINGS_KEY, self.custom_phrases)


class ImageProcessor:
    @staticmethod
    def encode_to_base64(image_path: str) -> Optional[str]:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"[ImageProcessor] 编码图片失败 {image_path}: {e}")
            return None

    @staticmethod
    def build_image_content(image_path: str, base64_data: str) -> Dict:
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_data}"
            },
            "_file_path": image_path
        }

    @staticmethod
    def build_display_content(image_path: str) -> Dict:
        return {
            "type": "image_url",
            "image_url": {"url": f"file://{image_path}"},
            "_file_path": image_path
        }

    @staticmethod
    def validate_image_path(image_path: str) -> bool:
        return bool(image_path and os.path.exists(image_path))


class MessageContentBuilder:
    @staticmethod
    def build_user_message(
        text: str,
        images: Optional[List[str]] = None
    ) -> Tuple[Any, Any]:
        if not images:
            return text, text

        api_content = []
        display_content = []

        if text:
            api_content.append({"type": "text", "text": text})
            display_content.append({"type": "text", "text": text})

        for img_path in images:
            base64_data = ImageProcessor.encode_to_base64(img_path)
            if base64_data:
                api_content.append(ImageProcessor.build_image_content(img_path, base64_data))

            if ImageProcessor.validate_image_path(img_path):
                display_content.append(ImageProcessor.build_display_content(img_path))

        return api_content if api_content else text, display_content if display_content else text

    @staticmethod
    def build_history_message(
        content: str,
        images: Optional[List[str]] = None
    ) -> Any:
        if not images:
            return content

        message_content = [{"type": "text", "text": content}] if content else []

        for img_path in images:
            if ImageProcessor.validate_image_path(img_path):
                message_content.append(ImageProcessor.build_display_content(img_path))

        if not message_content:
            return content

        return message_content


class QuickChatService:
    def __init__(self):
        deps = get_quick_chat_deps()

        self._state = get_quick_chat_state()
        self._chat_db = deps.chat_db
        self._persona_db = deps.persona_db

        self.session_manager = QuickChatSessionManager(self._chat_db, self._state)
        self.tool_manager = QuickChatToolManager(self._state)
        self.phrase_manager = QuickPhraseManager()
        self.markdown_renderer = MarkdownRenderer()

        self._tts_manager = None
        self._memory_manager = None

    def set_tts_manager(self, tts_manager):
        self._tts_manager = tts_manager

    def set_memory_manager(self, memory_manager):
        self._memory_manager = memory_manager

    def set_theme(self, is_dark: bool):
        self.markdown_renderer.set_theme(is_dark)
        self._state.is_dark_theme = is_dark

    def render_markdown(self, text: str) -> str:
        return self.markdown_renderer.render(text)

    def get_or_create_session(self) -> Optional[int]:
        return self.session_manager.get_or_create_session()

    def add_message(
        self,
        role: str,
        content: str,
        images: Optional[List[str]] = None
    ) -> Optional[int]:
        return self.session_manager.add_message(role, content, images)

    def get_messages(self) -> List[Tuple]:
        return self.session_manager.get_messages()

    def delete_message(self, msg_id: int) -> bool:
        return self.session_manager.delete_message(msg_id)

    def delete_messages_from(self, msg_id: int) -> List[int]:
        return self.session_manager.delete_messages_from(msg_id)

    def build_user_message(
        self,
        text: str,
        images: Optional[List[str]] = None
    ) -> Tuple[Any, Any]:
        return MessageContentBuilder.build_user_message(text, images)

    def build_history_message(
        self,
        content: str,
        images: Optional[List[str]] = None
    ) -> Any:
        return MessageContentBuilder.build_history_message(content, images)

    def get_enabled_tools(self) -> List[str]:
        return self.tool_manager.get_enabled_tools()

    def toggle_tool(self, tool_name: str, enabled: bool) -> bool:
        return self.tool_manager.toggle_tool(tool_name, enabled)

    def get_all_phrases(self) -> List[str]:
        return self.phrase_manager.get_all_phrases()

    def load_settings(self, settings):
        self.tool_manager.load_from_settings(settings)
        self.phrase_manager.load_from_settings(settings)

    def save_settings(self, settings):
        self.tool_manager.save_to_settings(settings)

    def save_phrases(self, settings, phrases: List[str]):
        self.phrase_manager.save_to_settings(settings, phrases)

    def get_context_for_llm(self, session_id: int) -> List[Dict]:
        if self._memory_manager:
            history = self._memory_manager.get_context(session_id)
        else:
            history = []

        system_prompt = self._state.current_persona_prompt
        if len(system_prompt) > 1000:
            if "你是 Doro" in system_prompt:
                system_prompt = "你是 Doro，一个可爱的白色小生物。你性格活泼、黏人，喜欢用可爱的语气和表情符号。请用中文回复，保持简短友好。"

        history.insert(0, {"role": "system", "content": system_prompt})
        
        history = self._optimize_context_images(history)
        
        return history

    def _optimize_context_images(self, history: List[Dict]) -> List[Dict]:
        """
        优化上下文中的图片数据：
        - 保留最后一条用户消息的图片（当前正在处理的）
        - 移除历史消息中的图片，替换为文本描述
        """
        if not history:
            return history
        
        last_user_idx = -1
        for i in range(len(history) - 1, -1, -1):
            if history[i].get("role") == "user":
                last_user_idx = i
                break
        
        optimized = []
        for i, msg in enumerate(history):
            content = msg.get("content")
            
            if i == last_user_idx:
                optimized.append(msg)
            elif isinstance(content, list):
                stripped_content = self._strip_images_from_content(content)
                optimized.append({
                    "role": msg.get("role"),
                    "content": stripped_content
                })
            elif isinstance(content, str):
                stripped_content = self._strip_base64_from_string(content)
                optimized.append({
                    "role": msg.get("role"),
                    "content": stripped_content
                })
            else:
                optimized.append(msg)
        
        return optimized

    def _strip_base64_from_string(self, content: str) -> str:
        """
        从字符串中移除 base64 图片数据
        """
        if 'data:image' not in content:
            return content
        
        import re
        result = re.sub(r'!\[.*?\]\(data:image/[^;]+;base64,[^)]*\)', '[图片]', content)
        result = re.sub(r'data:image/[^;]+;base64,[^\s"\')\]]+', '[图片数据]', result)
        return result

    def _strip_images_from_content(self, content: Any) -> Any:
        """
        从消息内容中移除图片数据，只保留文本
        用于减少上下文大小，避免 token 过量
        """
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            text_parts = []
            image_count = 0
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        image_count += 1
                elif isinstance(part, str):
                    text_parts.append(part)
            
            result = " ".join(text_parts) if text_parts else ""
            if image_count > 0:
                result += f" [用户发送了 {image_count} 张图片]"
            return result if result else content
        
        return content

    def add_to_memory(self, role: str, content: Any, session_id: int):
        if self._memory_manager:
            self._memory_manager.short_term_messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })

    def clear_memory(self):
        if self._memory_manager:
            self._memory_manager.short_term_messages.clear()

    def reload_memory_from_db(self):
        if not self._memory_manager:
            return
        session_id = self.session_manager.get_or_create_session()
        if not session_id:
            return
        self._memory_manager.short_term_messages.clear()
        msgs = self._chat_db.get_messages(session_id)
        for msg in msgs:
            role = msg[1]
            content = msg[2] if msg[2] else ""
            images = msg[3] if len(msg) > 3 else None
            
            if images and len(images) > 0:
                content += f" [用户发送了 {len(images)} 张图片]"
            
            if content:
                self._memory_manager.short_term_messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": msg[6] if len(msg) > 6 else datetime.now().isoformat()
                })
        logger.info(f"[QuickChatService] 重新加载内存：{len(msgs)} 条消息")

    def speak(self, msg_id: int, content: str):
        clean_content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()
        if clean_content and self._tts_manager:
            self._tts_manager.speak(str(msg_id), clean_content)

    def load_personas(self) -> Tuple[List[str], List[str], List[bool]]:
        names = ["默认助手"]
        prompts = ["You are a helpful assistant."]
        doro_tools = [False]

        if self._persona_db:
            personas = self._persona_db.get_personas()
            for p in personas:
                names.append(p[1])
                prompts.append(p[3])
                doro_tools.append(bool(p[5]))

        return names, prompts, doro_tools

    def set_persona(self, name: str, prompt: str):
        self._state.set_persona(name, prompt)

    def get_state(self) -> QuickChatState:
        return self._state


_service_instance: Optional[QuickChatService] = None


def get_quick_chat_service() -> QuickChatService:
    global _service_instance
    if _service_instance is None:
        _service_instance = QuickChatService()
    return _service_instance


def reset_quick_chat_service():
    global _service_instance
    _service_instance = None
