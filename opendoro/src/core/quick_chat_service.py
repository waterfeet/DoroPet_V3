"""
快捷聊天后端服务模块

该模块实现了快捷聊天窗口的核心业务逻辑，包括：
- Markdown 渲染
- 会话管理
- 消息处理
- 工具状态管理
- 快捷短语管理
- LLM 交互

设计原则：
- 前后端分离：所有 UI 无关的逻辑都在此模块中
- 可复用性：该服务可被其他模块复用
- 单一职责：每个类/方法只负责一个功能
"""
import re
import html
import base64
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter

from src.core.logger import logger


class MarkdownRenderer:
    """
    Markdown 渲染器
    
    负责将 Markdown 文本转换为带语法高亮的 HTML
    支持代码块、表格、引用等常见 Markdown 语法
    """
    
    def __init__(self, is_dark: bool = True):
        self.is_dark = is_dark
        self._update_style_config()
    
    def _update_style_config(self):
        """根据主题更新样式配置"""
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
        """设置主题"""
        self.is_dark = is_dark
        self._update_style_config()
    
    def render(self, text: str) -> str:
        """
        渲染 Markdown 文本为 HTML
        
        参数:
            text: Markdown 格式的文本
            
        返回:
            渲染后的 HTML 字符串
        """
        extensions = ['fenced_code', 'tables']
        
        try:
            markdown_html = markdown.markdown(text, extensions=extensions)
            markdown_html = self._process_code_blocks(markdown_html)
            custom_css = self._generate_custom_css()
            return custom_css + markdown_html
        except Exception as e:
            logger.error(f"[MarkdownRenderer] 渲染失败: {e}")
            return f"<pre>{text}</pre>"
    
    def _process_code_blocks(self, markdown_html: str) -> str:
        """处理代码块，添加语法高亮"""
        def replace_block(match):
            lang = match.group('lang')
            code_content = match.group('code')
            clean_code = html.unescape(code_content)
            
            try:
                if lang:
                    lexer = get_lexer_by_name(lang)
                else:
                    lexer = guess_lexer(clean_code)
            except:
                from pygments.lexers.special import TextLexer
                lexer = TextLexer()
            
            formatter = HtmlFormatter(style=self.style_name, noclasses=True)
            highlighted_html = highlight(clean_code, lexer, formatter)
            
            start_idx = highlighted_html.find('<pre')
            end_idx = highlighted_html.rfind('</pre>') + 6
            
            if start_idx != -1:
                pre_content = highlighted_html[start_idx:end_idx]
            else:
                pre_content = f'<pre>{code_content}</pre>'
            
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
        """生成自定义 CSS 样式"""
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
        </style>
        """


class QuickChatSessionManager:
    """
    快捷聊天会话管理器
    
    负责管理快捷聊天专用的会话，包括：
    - 创建/获取会话
    - 消息存储
    - 消息加载
    """
    
    SESSION_TITLE = "快捷聊天"
    
    def __init__(self, chat_db):
        self.chat_db = chat_db
        self.current_session_id: Optional[int] = None
    
    def get_or_create_session(self) -> Optional[int]:
        """
        获取或创建快捷聊天专用会话
        
        返回:
            会话 ID，失败返回 None
        """
        if self.current_session_id:
            return self.current_session_id
        
        cursor = self.chat_db.conn.cursor()
        cursor.execute("""
            SELECT id, title FROM sessions 
            WHERE title = ?
        """, (self.SESSION_TITLE,))
        
        row = cursor.fetchone()
        if row:
            self.current_session_id = row[0]
            logger.info(f"[QuickChatSessionManager] 找到快捷聊天会话：id={self.current_session_id}")
            return self.current_session_id
        
        self.current_session_id = self.chat_db.create_session(
            self.SESSION_TITLE, 
            "You are a helpful assistant."
        )
        logger.info(f"[QuickChatSessionManager] 创建快捷聊天会话：id={self.current_session_id}")
        return self.current_session_id
    
    def add_message(self, role: str, content: str, images: Optional[List[str]] = None) -> Optional[int]:
        """
        添加消息到会话
        
        参数:
            role: 消息角色 (user/assistant)
            content: 消息内容
            images: 图片路径列表
            
        返回:
            消息 ID，失败返回 None
        """
        session_id = self.get_or_create_session()
        if not session_id:
            return None
        
        msg_id = self.chat_db.add_message(
            session_id, 
            role, 
            content, 
            images=images
        )
        logger.info(f"[QuickChatSessionManager] 添加消息：msg_id={msg_id}, role={role}")
        return msg_id
    
    def get_messages(self) -> List[Tuple]:
        """
        获取会话中的所有消息
        
        返回:
            消息列表，每条消息为 (msg_id, role, content, images) 元组
        """
        session_id = self.get_or_create_session()
        if not session_id:
            return []
        
        return self.chat_db.get_messages(session_id)
    
    def delete_message(self, msg_id: int) -> bool:
        """
        删除指定消息
        
        参数:
            msg_id: 消息 ID
            
        返回:
            是否删除成功
        """
        try:
            self.chat_db.delete_message(msg_id)
            logger.info(f"[QuickChatSessionManager] 删除消息：msg_id={msg_id}")
            return True
        except Exception as e:
            logger.error(f"[QuickChatSessionManager] 删除消息失败：{e}")
            return False
    
    def delete_messages_from(self, msg_id: int) -> List[int]:
        """
        删除指定消息及其之后的所有消息
        
        参数:
            msg_id: 起始消息 ID
            
        返回:
            被删除的消息 ID 列表
        """
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
    """
    快捷聊天工具管理器
    
    负责管理工具插件的启用状态
    """
    
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
    
    def __init__(self):
        self.tool_states: Dict[str, bool] = self.DEFAULT_TOOLS.copy()
    
    def toggle_tool(self, tool_name: str, enabled: bool) -> bool:
        """
        切换工具启用状态
        
        参数:
            tool_name: 工具名称
            enabled: 是否启用
            
        返回:
            是否操作成功
        """
        if tool_name in self.tool_states or tool_name.startswith("skill:"):
            self.tool_states[tool_name] = enabled
            status = "启用" if enabled else "禁用"
            logger.info(f"[QuickChatToolManager] {status}工具：{tool_name}")
            return True
        return False
    
    def get_enabled_tools(self) -> List[str]:
        """获取所有启用的工具列表"""
        return [k for k, v in self.tool_states.items() if v]
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """检查工具是否启用"""
        return self.tool_states.get(tool_name, False)
    
    def get_tool_display_name(self, tool_name: str) -> str:
        """获取工具的显示名称"""
        return self.TOOL_NAMES.get(tool_name, tool_name)
    
    def get_enabled_tool_names(self) -> List[str]:
        """获取启用工具的显示名称列表"""
        enabled = self.get_enabled_tools()
        return [self.TOOL_NAMES.get(t, t) for t in enabled if not t.startswith("skill:")]
    
    def load_from_settings(self, settings):
        """从设置加载工具状态"""
        for tool_name in self.tool_states.keys():
            saved_value = settings.value(f"tool_{tool_name}_enabled", None)
            if saved_value is not None:
                self.tool_states[tool_name] = (
                    saved_value if isinstance(saved_value, bool) 
                    else (str(saved_value).lower() == 'true')
                )
    
    def save_to_settings(self, settings):
        """保存工具状态到设置"""
        for tool_name, enabled in self.tool_states.items():
            settings.setValue(f"tool_{tool_name}_enabled", enabled)


class QuickPhraseManager:
    """
    快捷短语管理器
    
    负责管理快捷短语的加载、保存和更新
    """
    
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
        """获取所有短语（默认 + 自定义），去重"""
        all_phrases = []
        seen = set()
        for phrase in self.default_phrases + self.custom_phrases:
            if phrase not in seen:
                all_phrases.append(phrase)
                seen.add(phrase)
        return all_phrases
    
    def load_from_settings(self, settings):
        """从设置加载自定义短语"""
        saved_phrases = settings.value(self.SETTINGS_KEY, [])
        if not isinstance(saved_phrases, list):
            saved_phrases = saved_phrases.split('||') if saved_phrases else []
        self.custom_phrases = [p for p in saved_phrases if p.strip()]
    
    def save_to_settings(self, settings, phrases: List[str]):
        """保存自定义短语到设置"""
        self.custom_phrases = [p.strip() for p in phrases if p.strip()]
        settings.setValue(self.SETTINGS_KEY, self.custom_phrases)


class ImageProcessor:
    """
    图片处理器
    
    负责图片的编码和处理
    """
    
    @staticmethod
    def encode_to_base64(image_path: str) -> Optional[str]:
        """
        将图片编码为 base64 字符串
        
        参数:
            image_path: 图片文件路径
            
        返回:
            base64 编码的字符串，失败返回 None
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"[ImageProcessor] 编码图片失败 {image_path}: {e}")
            return None
    
    @staticmethod
    def build_image_content(image_path: str, base64_data: str) -> Dict:
        """
        构建图片消息内容
        
        参数:
            image_path: 图片路径
            base64_data: base64 编码数据
            
        返回:
            图片消息内容字典
        """
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_data}"
            },
            "_file_path": image_path
        }
    
    @staticmethod
    def build_display_content(image_path: str) -> Dict:
        """
        构建用于显示的图片内容
        
        参数:
            image_path: 图片路径
            
        返回:
            显示用图片内容字典
        """
        return {
            "type": "image_url",
            "image_url": {"url": f"file://{image_path}"},
            "_file_path": image_path
        }
    
    @staticmethod
    def validate_image_path(image_path: str) -> bool:
        """验证图片路径是否有效"""
        return bool(image_path and os.path.exists(image_path))


class MessageContentBuilder:
    """
    消息内容构建器
    
    负责构建不同类型的消息内容
    """
    
    @staticmethod
    def build_user_message(
        text: str, 
        images: Optional[List[str]] = None
    ) -> Tuple[Any, Any]:
        """
        构建用户消息内容
        
        参数:
            text: 文本内容
            images: 图片路径列表
            
        返回:
            (api_content, display_content) 元组
            - api_content: 发送给 API 的内容
            - display_content: 用于 UI 显示的内容
        """
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
                api_content.append(
                    ImageProcessor.build_image_content(img_path, base64_data)
                )
            
            if ImageProcessor.validate_image_path(img_path):
                display_content.append(
                    ImageProcessor.build_display_content(img_path)
                )
        
        return api_content if api_content else text, display_content if display_content else text
    
    @staticmethod
    def build_history_message(
        content: str, 
        images: Optional[List[str]] = None
    ) -> Any:
        """
        构建历史消息内容（用于加载历史记录）
        
        参数:
            content: 文本内容
            images: 图片路径列表
            
        返回:
            消息内容
        """
        if not images:
            return content
        
        message_content = [{"type": "text", "text": content}] if content else []
        
        for img_path in images:
            if ImageProcessor.validate_image_path(img_path):
                message_content.append(
                    ImageProcessor.build_display_content(img_path)
                )
        
        return message_content if message_content else content


class QuickChatService:
    """
    快捷聊天服务
    
    整合所有后端功能，提供统一的接口
    """
    
    def __init__(self, chat_db, persona_db=None, memory_manager=None, tts_manager=None):
        self.chat_db = chat_db
        self.persona_db = persona_db
        self.memory_manager = memory_manager
        self.tts_manager = tts_manager
        
        self.session_manager = QuickChatSessionManager(chat_db)
        self.tool_manager = QuickChatToolManager()
        self.phrase_manager = QuickPhraseManager()
        self.markdown_renderer = MarkdownRenderer()
        
        self.current_persona = "默认助手"
        self.current_system_prompt = "You are a helpful assistant."
    
    def set_theme(self, is_dark: bool):
        """设置主题"""
        self.markdown_renderer.set_theme(is_dark)
    
    def render_markdown(self, text: str) -> str:
        """渲染 Markdown 文本"""
        return self.markdown_renderer.render(text)
    
    def get_or_create_session(self) -> Optional[int]:
        """获取或创建会话"""
        return self.session_manager.get_or_create_session()
    
    def add_message(
        self, 
        role: str, 
        content: str, 
        images: Optional[List[str]] = None
    ) -> Optional[int]:
        """添加消息"""
        return self.session_manager.add_message(role, content, images)
    
    def get_messages(self) -> List[Tuple]:
        """获取所有消息"""
        return self.session_manager.get_messages()
    
    def delete_message(self, msg_id: int) -> bool:
        """删除消息"""
        return self.session_manager.delete_message(msg_id)
    
    def delete_messages_from(self, msg_id: int) -> List[int]:
        """删除指定消息及其之后的所有消息"""
        return self.session_manager.delete_messages_from(msg_id)
    
    def build_user_message(
        self, 
        text: str, 
        images: Optional[List[str]] = None
    ) -> Tuple[Any, Any]:
        """构建用户消息"""
        return MessageContentBuilder.build_user_message(text, images)
    
    def build_history_message(
        self, 
        content: str, 
        images: Optional[List[str]] = None
    ) -> Any:
        """构建历史消息"""
        return MessageContentBuilder.build_history_message(content, images)
    
    def get_enabled_tools(self) -> List[str]:
        """获取启用的工具列表"""
        return self.tool_manager.get_enabled_tools()
    
    def toggle_tool(self, tool_name: str, enabled: bool) -> bool:
        """切换工具状态"""
        return self.tool_manager.toggle_tool(tool_name, enabled)
    
    def get_all_phrases(self) -> List[str]:
        """获取所有快捷短语"""
        return self.phrase_manager.get_all_phrases()
    
    def load_settings(self, settings):
        """加载设置"""
        self.tool_manager.load_from_settings(settings)
        self.phrase_manager.load_from_settings(settings)
    
    def save_settings(self, settings):
        """保存设置"""
        self.tool_manager.save_to_settings(settings)
    
    def save_phrases(self, settings, phrases: List[str]):
        """保存快捷短语"""
        self.phrase_manager.save_to_settings(settings, phrases)
    
    def get_context_for_llm(self, session_id: int) -> List[Dict]:
        """
        获取发送给 LLM 的上下文
        
        参数:
            session_id: 会话 ID
            
        返回:
            消息列表
        """
        if self.memory_manager:
            history = self.memory_manager.get_context(session_id)
        else:
            history = []
        
        system_prompt = self.current_system_prompt
        if len(system_prompt) > 1000:
            if "你是 Doro" in system_prompt:
                system_prompt = "你是 Doro，一个可爱的白色小生物。你性格活泼、黏人，喜欢用可爱的语气和表情符号。请用中文回复，保持简短友好。"
        
        history.insert(0, {"role": "system", "content": system_prompt})
        return history
    
    def add_to_memory(self, role: str, content: Any, session_id: int):
        """添加消息到记忆管理器"""
        if self.memory_manager:
            self.memory_manager.short_term_messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
    
    def clear_memory(self):
        """清空短期记忆"""
        if self.memory_manager:
            self.memory_manager.short_term_messages.clear()
    
    def speak(self, msg_id: int, content: str):
        """朗读消息"""
        clean_content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()
        if clean_content and self.tts_manager:
            self.tts_manager.speak(str(msg_id), clean_content)
    
    def load_personas(self) -> Tuple[List[str], List[str], List[bool]]:
        """
        加载人格列表
        
        返回:
            (names, prompts, doro_tools) 元组
        """
        names = ["默认助手"]
        prompts = ["You are a helpful assistant."]
        doro_tools = [False]
        
        if self.persona_db:
            personas = self.persona_db.get_personas()
            for p in personas:
                names.append(p[1])
                prompts.append(p[3])
                doro_tools.append(bool(p[5]))
        
        return names, prompts, doro_tools
    
    def set_persona(self, name: str, prompt: str):
        """设置当前人格"""
        self.current_persona = name
        self.current_system_prompt = prompt
