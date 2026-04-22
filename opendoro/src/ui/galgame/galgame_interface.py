from typing import Optional, List
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    TitleLabel, BodyLabel, FluentIcon, isDarkTheme, InfoBar, InfoBarPosition
)

from src.core.database import ChatDatabase
from src.provider.manager import ProviderManager
from src.core.logger import logger

from .models import (
    Protagonist, Character, WorldSetting, GameState, GameConfig,
    StoryMessage, GameChoice, MessageRole, AffectionState, get_relationship_name,
    StoryCache, EventContext
)
from .database import GalgameDatabase
from .story_generator import StoryGenerator, StoryContextManager
from .story_cache_manager import StoryCacheManager
from .story_worker import (
    StartStoryWorker, ContinueStoryWorker,
    StoryPlanWorker, ChapterSummaryWorker, NextChapterPlanWorker,
    ChapterOpeningWorker, ChapterContinuationWorker
)
from .memory_manager import CharacterMemoryManager
from .event_trigger import ExclusiveEventTrigger, DynamicEventManager, SpecialDateManager
from .ending_manager import EndingManager
from .widgets import TopConfigPanel, StoryFlowArea, GalgameStatusBar
from .dialogs import ProtagonistDialog, CharacterDialog, WorldDialog, SaveDialog, ShopDialog, PromptGeneratorDialog, InventoryDialog, FontSettingsDialog, MemoryDialog, EndingDialog, EndingListDialog


class GalgameInterface(QWidget):
    def __init__(self, db: ChatDatabase, parent=None):
        super().__init__(parent)
        self._db = db
        self._galgame_db = GalgameDatabase()
        self._provider_manager = ProviderManager.get_instance()
        self._story_generator = StoryGenerator(self._provider_manager)
        self._context_manager = StoryContextManager()
        
        self._memory_manager = CharacterMemoryManager(self._galgame_db)
        self._exclusive_event_trigger = ExclusiveEventTrigger(self._galgame_db, self._memory_manager)
        self._dynamic_event_manager = DynamicEventManager(self._galgame_db)
        self._special_date_manager = SpecialDateManager()
        self._ending_manager = EndingManager(self._galgame_db, self._provider_manager)
        self._current_event_context = EventContext()
        self._has_ended = False
        
        self._game_config: Optional[GameConfig] = None
        self._game_state: Optional[GameState] = None
        self._story_cache: Optional[StoryCache] = None
        self._current_worker = None
        self._streaming_card = None
        self._is_generating = False
        self._streaming_buffer = ""
        self._chapter_messages: List[str] = []
        
        self._protagonist = Protagonist()
        self._characters: List[Character] = []
        self._world_setting = WorldSetting()
        self._current_model_id = None
        
        self._story_size = 14
        self._title_size = 16
        
        self._load_font_settings()
        
        self.setObjectName("GalgameInterface")
        self.init_ui()
        self._load_models()
        self._load_saved_config()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.top_panel = TopConfigPanel(self)
        self.top_panel.protagonist_clicked.connect(self._show_protagonist_dialog)
        self.top_panel.characters_clicked.connect(self._show_characters_dialog)
        self.top_panel.world_clicked.connect(self._show_world_dialog)
        self.top_panel.smart_generate_clicked.connect(self._show_smart_generate_dialog)
        self.top_panel.start_clicked.connect(self._start_game)
        self.top_panel.model_changed.connect(self._on_model_changed)
        self.top_panel.font_settings_clicked.connect(self._show_font_settings_dialog)
        layout.addWidget(self.top_panel)
        
        self.story_area = StoryFlowArea(self)
        self.story_area.choice_selected.connect(self._on_choice_selected)
        self.story_area.chapter_changed.connect(self._on_chapter_changed)
        layout.addWidget(self.story_area, 1)
        
        self.status_bar = GalgameStatusBar(self)
        self.status_bar.shop_clicked.connect(self._show_shop_dialog)
        self.status_bar.save_clicked.connect(self._show_save_dialog)
        self.status_bar.inventory_clicked.connect(self._show_inventory_dialog)
        self.status_bar.memory_clicked.connect(self._show_memory_dialog)
        self.status_bar.ending_clicked.connect(self._show_ending_dialog)
        self.status_bar.chapter_selected.connect(self._on_chapter_selected)
        layout.addWidget(self.status_bar)
        
        self._show_welcome()
        self.update_theme()
    
    def _load_models(self):
        models = self._db.get_models()
        self.top_panel.set_models(models)
        self._load_saved_config()
    
    def _load_saved_config(self):
        """Load saved configuration from database"""
        saved_config = self._galgame_db.load_current_config()
        if saved_config:
            self._protagonist = saved_config['protagonist']
            self._characters = saved_config['characters']
            self._world_setting = saved_config['world_setting']
            self._current_model_id = saved_config['model_id']
            
            if self._current_model_id:
                self.top_panel.set_current_model(self._current_model_id)
    
    def _save_current_config(self):
        model_id = self.top_panel.get_current_model_id()
        self._galgame_db.save_current_config(
            self._protagonist,
            self._characters,
            self._world_setting,
            model_id or ""
        )
    
    def _load_font_settings(self):
        import json
        import os
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config')
        os.makedirs(config_path, exist_ok=True)
        font_config_file = os.path.join(config_path, 'galgame_font.json')
        
        if os.path.exists(font_config_file):
            try:
                with open(font_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._story_size = config.get('story_size', 14)
                    self._title_size = config.get('title_size', 16)
            except:
                pass
    
    def _save_font_settings(self):
        import json
        import os
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config')
        os.makedirs(config_path, exist_ok=True)
        font_config_file = os.path.join(config_path, 'galgame_font.json')
        
        config = {
            'story_size': self._story_size,
            'title_size': self._title_size
        }
        
        with open(font_config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def _show_font_settings_dialog(self):
        dialog = FontSettingsDialog(
            self, 
            self._story_size, 
            self._title_size
        )
        dialog.font_changed.connect(self._apply_font_settings)
        dialog.exec_()
    
    def _apply_font_settings(self, story_size: int, title_size: int):
        self._story_size = story_size
        self._title_size = title_size
        
        self._save_font_settings()
        
        self.story_area.set_font_sizes(story_size, title_size)
        self.story_area.update_theme()
        
        self._show_info("字体设置已应用！")
    
    def _show_welcome(self):
        welcome_msg = StoryMessage(
            id=0,
            role=MessageRole.SYSTEM,
            character_name=None,
            content="欢迎来到 Galgame 模式！\n\n"
                    "请先配置以下内容开始游戏：\n"
                    "1. 点击「主角配置」设置你的角色\n"
                    "2. 点击「角色配置」添加游戏中的角色\n"
                    "3. 点击「世界观」设置故事背景\n"
                    "4. 选择要使用的AI模型\n"
                    "5. 点击「开始游戏」开始冒险！\n\n"
                    "提示：你也可以使用底部的「存档」按钮来保存或加载游戏进度。"
        )
        self.story_area.add_message(welcome_msg)
    
    def _show_protagonist_dialog(self):
        dialog = ProtagonistDialog(self._protagonist, self)
        if dialog.exec_():
            self._protagonist = dialog.get_protagonist()
            self._save_current_config()
            self._show_info(f"主角已设置: {self._protagonist.name}")
    
    def _show_characters_dialog(self):
        dialog = CharacterDialog(self._characters, self)
        if dialog.exec_():
            self._characters = dialog.get_characters()
            self._save_current_config()
            self._show_info(f"已配置 {len(self._characters)} 个角色")
    
    def _show_world_dialog(self):
        dialog = WorldDialog(self._world_setting, self)
        if dialog.exec_():
            self._world_setting = dialog.get_world_setting()
            self._save_current_config()
            self._show_info(f"世界观已设置: {self._world_setting.name}")
    
    def _show_smart_generate_dialog(self):
        dialog = PromptGeneratorDialog(self._provider_manager, self)
        dialog.config_generated.connect(self._on_config_generated)
        dialog.exec_()
    
    def _on_config_generated(self, protagonist: Protagonist, characters: List[Character], world_setting: WorldSetting):
        self._protagonist = protagonist
        self._characters = characters
        self._world_setting = world_setting
        self._save_current_config()
        self._show_info(f"智能配置已应用：{self._protagonist.name} + {len(self._characters)} 个角色")
    
    def _on_model_changed(self, model_id: str):
        logger.info(f"Model changed to: {model_id}")
        self._current_model_id = model_id
        self._save_current_config()
    
    def _start_game(self):
        if self._is_generating:
            return
        
        if not self._characters:
            self._show_error("请先添加至少一个角色！")
            return
        
        model_id = self.top_panel.get_current_model_id()
        if not model_id:
            self._show_error("请先配置AI模型！")
            return
        
        self._is_generating = True
        self.top_panel.set_start_enabled(False)
        
        self.story_area.clear_all()
        
        self._game_state = GameState(
            save_id=0,
            config_id=0,
            chapter=1,
            scene="开场",
            currency=100,
            affections=[
                AffectionState(
                    character_name=char.name,
                    affection=char.initial_affection,
                    relationship=char.relationship
                ) for char in self._characters
            ],
            protagonist=self._protagonist,
            characters=self._characters,
            world_setting=self._world_setting
        )
        
        self._chapter_messages = []
        self._update_status_bar()
        
        # 注册角色生日
        for char in self._characters:
            if hasattr(char, 'birthday') and char.birthday:
                self._special_date_manager.register_character_birthday(char.name, char.birthday)
        
        # 检查今日特殊事件
        special_events = self._special_date_manager.get_today_events()
        if special_events:
            for event in special_events:
                self._show_info(f"🎉 今日特殊：{event['name']}！")
        
        # Phase 1: 生成故事规划
        self._show_info("正在生成故事大纲...")
        
        self._current_worker = StoryPlanWorker(
            self._story_generator,
            self._protagonist,
            self._characters,
            self._world_setting,
            model_id
        )
        self._current_worker.plan_complete.connect(self._on_story_plan_complete)
        self._current_worker.error_occurred.connect(self._on_generation_error)
        self._current_worker.start()
    
    def _on_story_plan_complete(self, cache: StoryCache):
        self._story_cache = cache
        self._game_state.story_cache = cache
        
        chapter_num = cache.current_chapter.chapter_number if cache.current_chapter else 1
        chapter_name = cache.current_chapter.chapter_name if cache.current_chapter else ""
        
        self._show_info(f"开始 第{chapter_num}章：{chapter_name if chapter_name else '无题'}")
        self._update_status_bar()
        
        # Phase 2: 生成第一章开头
        self._streaming_buffer = ""
        self._streaming_card = self.story_area.add_streaming_message(
            "narrator",
            chapter_number=chapter_num,
            chapter_name=chapter_name
        )
        
        model_id = self.top_panel.get_current_model_id()
        
        self._current_worker = ChapterOpeningWorker(
            self._story_generator,
            self._story_cache,
            self._game_state,
            model_id
        )
        self._current_worker.text_generated.connect(self._on_text_generated)
        self._current_worker.generation_complete.connect(self._on_generation_complete)
        self._current_worker.error_occurred.connect(self._on_generation_error)
        self._current_worker.start()
    
    def _on_chapter_changed(self, chapter_num: int, chapter_name: str):
        chapters = self.story_area.get_chapters()
        if chapters:
            self.status_bar.update_chapters(chapters, chapter_num)
        else:
            self.status_bar.update_chapters([chapter_num], chapter_num)
    
    def _on_chapter_selected(self, chapter_num: int):
        self.story_area.scroll_to_chapter(chapter_num)
    
    def _on_choice_selected(self, choice_id: int):
        if self._is_generating or not self._game_state:
            return
        
        self._is_generating = True
        self.top_panel.set_start_enabled(False)
        
        selected_choice = None
        if self._game_state.messages:
            last_msg = self._game_state.messages[-1]
            for choice in last_msg.choices:
                if choice.id == choice_id:
                    selected_choice = choice
                    last_msg.selected_choice = choice_id
                    break
        
        if not selected_choice:
            return
        
        choice_text = selected_choice.text
        
        # 检测并处理物品消耗
        self._handle_item_consumption(choice_text)
        
        # 检测并处理金币消耗
        self._handle_currency_consumption(choice_text)
        
        self._context_manager.add_user_choice(choice_text)
        
        # 检查是否需要触发章节过渡
        if self._story_cache and StoryCacheManager.should_transition_chapter(self._story_cache):
            self._transition_to_next_chapter(selected_choice.text)
        else:
            self._continue_chapter_generation(selected_choice.text)
    
    def _continue_chapter_generation(self, choice_text: str):
        self._streaming_buffer = ""
        
        # 从 story_cache 获取章节信息
        chapter_num = 1
        chapter_name = ""
        if self._story_cache and self._story_cache.current_chapter:
            chapter_num = self._story_cache.current_chapter.chapter_number
            chapter_name = self._story_cache.current_chapter.chapter_name
        
        self._streaming_card = self.story_area.add_streaming_message(
            "narrator",
            chapter_number=chapter_num,
            chapter_name=chapter_name
        )
        
        model_id = self.top_panel.get_current_model_id()
        context = self._context_manager.get_context()
        
        self._current_worker = ChapterContinuationWorker(
            self._story_generator,
            context,
            choice_text,
            self._story_cache,
            self._game_state,
            model_id
        )
        self._current_worker.text_generated.connect(self._on_text_generated)
        self._current_worker.generation_complete.connect(self._on_generation_complete)
        self._current_worker.error_occurred.connect(self._on_generation_error)
        self._current_worker.start()
    
    def _transition_to_next_chapter(self, choice_text: str):
        model_id = self.top_panel.get_current_model_id()
        
        self._show_info("正在生成章节摘要...")
        
        # Step 1: 概括前文
        self._current_worker = ChapterSummaryWorker(
            self._story_generator,
            self._chapter_messages,
            self._story_cache,
            model_id
        )
        self._current_worker.summary_complete.connect(
            lambda summary: self._on_chapter_summary_complete(summary, choice_text)
        )
        self._current_worker.error_occurred.connect(self._on_generation_error)
        self._current_worker.start()
    
    def _on_chapter_summary_complete(self, summary: dict, choice_text: str):
        StoryCacheManager.update_after_chapter_summary(self._story_cache, summary)
        
        model_id = self.top_panel.get_current_model_id()
        
        self._show_info("正在规划下一章...")
        
        # Step 2: 生成下一章规划
        self._current_worker = NextChapterPlanWorker(
            self._story_generator,
            self._story_cache,
            self._game_state,
            model_id
        )
        self._current_worker.plan_complete.connect(
            lambda plan: self._on_next_chapter_plan_complete(plan, choice_text)
        )
        self._current_worker.error_occurred.connect(self._on_generation_error)
        self._current_worker.start()
    
    def _on_next_chapter_plan_complete(self, plan: dict, choice_text: str):
        StoryCacheManager.update_after_chapter_plan(self._story_cache, plan)
        
        chapter_num = self._story_cache.current_chapter.chapter_number if self._story_cache.current_chapter else 1
        chapter_name = plan.get('chapter_name', '')
        
        # 更新 story_cache 中的章节名称
        if self._story_cache.current_chapter:
            self._story_cache.current_chapter.chapter_name = chapter_name
        
        self._show_info(f"开始 第{chapter_num}章：{chapter_name if chapter_name else '无题'}")
        self._update_status_bar()
        
        # 清空章节消息
        self._chapter_messages = []
        
        # Step 3: 生成新章节开头
        self._streaming_buffer = ""
        self._streaming_card = self.story_area.add_streaming_message(
            "narrator",
            chapter_number=chapter_num,
            chapter_name=chapter_name
        )
        
        model_id = self.top_panel.get_current_model_id()
        
        self._current_worker = ChapterOpeningWorker(
            self._story_generator,
            self._story_cache,
            self._game_state,
            model_id
        )
        self._current_worker.text_generated.connect(self._on_text_generated)
        self._current_worker.generation_complete.connect(self._on_generation_complete)
        self._current_worker.error_occurred.connect(self._on_generation_error)
        self._current_worker.start()
    
    def _on_text_generated(self, text: str):
        if self._streaming_card:
            # 累积文本到缓冲区
            self._streaming_buffer += text
            
            # 尝试提取故事内容
            from .response_parser import ResponseParser
            
            # 检查是否已经有完整的故事标签
            if '[故事]' in self._streaming_buffer and '[/故事]' in self._streaming_buffer:
                # 提取完整的故事内容
                story_match = __import__('re').search(r'\[故事\](.*?)\[/故事\]', self._streaming_buffer, __import__('re').DOTALL)
                if story_match:
                    story_content = story_match.group(1).strip()
                    self.story_area.update_streaming_content(self._streaming_card, story_content)
            elif '[故事]' in self._streaming_buffer:
                # 只有开始标签，提取标签之后的内容（但排除选择、好感度等标签）
                idx = self._streaming_buffer.index('[故事]')
                partial = self._streaming_buffer[idx + 5:]
                # 如果出现选择标签，截断
                if '[选择' in partial:
                    partial = partial[:partial.index('[选择')]
                self.story_area.update_streaming_content(self._streaming_card, partial.strip())
            # 如果还没有故事标签，不显示任何内容（避免显示标签）
    
    def _on_generation_complete(self, result: dict):
        self._is_generating = False
        self.top_panel.set_start_enabled(True)
        
        if self._streaming_card:
            self.story_area.finalize_streaming_card(self._streaming_card, result)
            
            chapter_num = 1
            chapter_name = ""
            if self._story_cache and self._story_cache.current_chapter:
                chapter_num = self._story_cache.current_chapter.chapter_number
                chapter_name = self._story_cache.current_chapter.chapter_name
            
            if self._game_state:
                self._game_state.chapter = chapter_num
            
            message = StoryMessage(
                id=len(self._game_state.messages) if self._game_state else 0,
                role=MessageRole.NARRATOR,
                character_name=None,
                content=result.get('story', ''),
                choices=[GameChoice(id=c['id'], text=c['text']) for c in result.get('choices', [])],
                chapter_number=chapter_num,
                chapter_name=chapter_name
            )
            
            if self._game_state:
                self._game_state.messages.append(message)
                self._context_manager.add_assistant_response(result.get('story', ''))
                
                story_content = result.get('story', '')
                if story_content:
                    self._chapter_messages.append(story_content)
                    self._extract_and_save_memories(story_content)
                
                if self._story_cache:
                    StoryCacheManager.update_after_response(self._story_cache)
                
                affection_changes = result.get('affection_changes', {})
                for char_name, change in affection_changes.items():
                    old_aff = self._game_state.get_affection(char_name)
                    new_aff = self._game_state.update_affection(char_name, change)
                    
                    milestone = self._check_affection_milestone(char_name, old_aff, new_aff)
                    if milestone:
                        self._show_info(f"💕 {char_name}的好感度达到了{new_aff}！{milestone}")
                        # 添加特殊记忆
                        self._memory_manager.add_memory(
                            char_name, "special",
                            f"好感度达到{new_aff}，关系升级为{get_relationship_name(new_aff)}",
                            importance=8,
                            context={"chapter": chapter_num, "milestone": True}
                        )
                    
                    for aff in self._game_state.affections:
                        if aff.character_name == char_name:
                            aff.relationship = get_relationship_name(new_aff)
                            break
                
                currency_change = result.get('currency_change', 0)
                self._game_state.currency += currency_change
                self._game_state.currency = max(0, self._game_state.currency)
                
                self._update_status_bar()
                
                # 检查专属事件触发
                self._check_exclusive_events()
                
                # 自动存档
                if self._game_state:
                    logger.info(f"Auto-save triggered: save_id={self._game_state.save_id}")
                    self._galgame_db.auto_save_state(self._game_state)
        
        self._streaming_card = None
        self._current_worker = None
    
    def _extract_and_save_memories(self, story_content: str):
        """从故事内容中提取并保存记忆"""
        if not self._game_state:
            return
        
        for char in self._game_state.characters:
            if char.name in story_content:
                memories = self._memory_manager.extract_memories_from_text(story_content, char.name)
                for mem in memories:
                    self._memory_manager.add_memory(
                        char.name,
                        mem["type"],
                        mem["content"],
                        importance=mem.get("importance", 5),
                        context={"chapter": self._game_state.chapter}
                    )
    
    def _check_exclusive_events(self):
        """检查并触发专属事件"""
        if not self._game_state:
            return
        
        event = self._exclusive_event_trigger.check_triggers(self._game_state)
        if event:
            self._show_info(f"🎭 触发专属事件：{event.character_name}的「{event.event_name}」")
            
            # 添加事件相关的记忆
            self._memory_manager.add_memory(
                event.character_name,
                "special",
                f"经历了「{event.event_name}」事件",
                importance=9,
                context={"chapter": self._game_state.chapter, "exclusive_event": event.id}
            )
        
        # 检查即将到来的事件
        upcoming = self._exclusive_event_trigger.get_upcoming_events(self._game_state)
        if upcoming:
            nearest = upcoming[0]
            if nearest["diff"] <= 10:
                self._show_info(f"💡 提示：{nearest['character']}的「{nearest['event_name']}」即将触发（还差{nearest['diff']}好感度）")
        
        # 检查结局触发
        self._check_ending()
    
    def _check_ending(self):
        """检查是否触发结局"""
        if not self._game_state or self._has_ended:
            return
        
        ending_type = self._ending_manager.check_ending_trigger(self._game_state)
        
        if ending_type:
            self._has_ended = True
            self._trigger_ending(ending_type)
    
    def _trigger_ending(self, ending_type: str):
        """触发结局"""
        character_name = self._ending_manager.get_ending_character(self._game_state, ending_type)
        
        self._show_info(f"🎊 触发结局：{ending_type}结局！")
        
        model_id = self.top_panel.get_current_model_id()
        ending = self._ending_manager.generate_ending(
            self._game_state,
            ending_type,
            character_name,
            model_id
        )
        
        # 保存结局
        save_id = self._game_state.save_id if self._game_state else 0
        self._ending_manager.save_ending(ending, save_id)
        
        # 显示结局对话框
        dialog = EndingDialog(ending, self)
        dialog.exec_()
        
        if dialog.should_start_new_game():
            self._start_new_game()
    
    def _start_new_game(self):
        """开始新游戏"""
        self._has_ended = False
        self._game_state = None
        self._story_cache = None
        self._chapter_messages = []
        
        self.story_area.clear_all()
        self._show_welcome()
        self._update_status_bar()
        self.top_panel.set_start_enabled(True)
    
    def _on_generation_error(self, error: str):
        self._is_generating = False
        self.top_panel.set_start_enabled(True)
        
        self._show_error(f"生成错误: {error}")
        
        if self._streaming_card:
            self.story_area.update_streaming_content(self._streaming_card, f"\n\n[错误: {error}]")
        
        self._streaming_card = None
        self._current_worker = None
    
    def _check_affection_milestone(self, char_name: str, old_aff: int, new_aff: int) -> str:
        milestones = {
            30: "角色开始信任你了！",
            50: "你们建立了友谊！",
            70: "角色对你产生了好感！",
            90: "角色对你非常亲密！"
        }
        
        for threshold, message in milestones.items():
            if old_aff < threshold <= new_aff:
                return message
        
        return ""
    
    def _handle_item_consumption(self, choice_text: str):
        import re
        
        if not self._game_state or not self._game_state.inventory:
            return
        
        item_pattern = r'使用(.+?)(?:来|送给|保护)'
        match = re.search(item_pattern, choice_text)
        
        if match:
            item_keyword = match.group(1).strip()
            
            for item in self._game_state.inventory[:]:
                item_name = item.get('name', '')
                if item_keyword in item_name or item_name in item_keyword:
                    self._game_state.inventory.remove(item)
                    self._show_info(f"使用了 {item_name}！")
                    break
    
    def _handle_currency_consumption(self, choice_text: str):
        import re
        
        if not self._game_state:
            return
        
        currency_pattern = r'(?:花费|消耗|支付)(\d+)(?:金币)?'
        match = re.search(currency_pattern, choice_text)
        
        if match:
            amount = int(match.group(1))
            if self._game_state.currency >= amount:
                self._game_state.currency -= amount
                self._update_status_bar()
    
    def _update_status_bar(self):
        if self._game_state:
            chapter_name = ""
            if self._story_cache:
                chapter_name = StoryCacheManager.get_chapter_display_name(self._story_cache)
            elif self._game_state.chapter:
                chapter_name = f"第{self._game_state.chapter}章"
            
            self.status_bar.update_state(
                chapter_name,
                self._game_state.currency,
                self._game_state.affections
            )
    
    def _show_shop_dialog(self):
        if not self._game_state:
            self._show_error("请先开始游戏！")
            return
        
        dialog = ShopDialog(self._galgame_db, self._game_state, self)
        dialog.exec_()
        
        self._game_state = dialog.get_updated_state()
        self._update_status_bar()
    
    def _show_inventory_dialog(self):
        if not self._game_state:
            self._show_error("请先开始游戏！")
            return
        
        dialog = InventoryDialog(self._game_state, self)
        dialog.item_used.connect(self._on_item_used)
        dialog.exec_()
        
        self._game_state = dialog.get_updated_state()
        self._update_status_bar()
    
    def _show_memory_dialog(self):
        if not self._game_state or not self._characters:
            self._show_error("请先开始游戏！")
            return
        
        character_names = [char.name for char in self._characters]
        dialog = MemoryDialog(self._memory_manager, character_names, self)
        dialog.exec_()
    
    def _show_ending_dialog(self):
        endings = self._ending_manager.get_ending_statistics()
        all_endings = self._galgame_db.get_all_endings()
        
        if not all_endings:
            self._show_info("还没有达成任何结局，继续游戏吧！")
            return
        
        dialog = EndingListDialog(all_endings, self)
        dialog.exec_()
    
    def _on_item_used(self, item: dict):
        self._show_info(f"使用了 {item.get('name', '物品')}！")
    
    def _show_save_dialog(self):
        if self._is_generating:
            InfoBar.warning(
                title="警告",
                content="正在生成故事，请稍后再保存",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        dialog = SaveDialog(self._galgame_db, self._game_state, self)
        
        if dialog.exec_():
            save_id = dialog.get_selected_save_id()
            if save_id:
                if self._game_state and self._game_state.save_id == 0:
                    self._game_state.save_id = save_id
                    self._game_state.protagonist = self._protagonist
                    self._game_state.characters = self._characters
                    self._game_state.world_setting = self._world_setting
                    self._galgame_db.save_state(self._game_state)
                    self._show_info("游戏已保存！")
                else:
                    loaded_state = self._galgame_db.load_state(save_id)
                    if loaded_state:
                        self._game_state = loaded_state
                        
                        if loaded_state.protagonist:
                            self._protagonist = loaded_state.protagonist
                        if loaded_state.characters:
                            self._characters = loaded_state.characters
                        if loaded_state.world_setting:
                            self._world_setting = loaded_state.world_setting
                        
                        self._story_cache = loaded_state.story_cache
                        
                        self._update_status_bar()
                        
                        self.story_area.clear_all()
                        for msg in self._game_state.messages:
                            self.story_area.add_message(msg)
                        
                        if self._game_state.messages:
                            last_msg = self._game_state.messages[-1]
                            if last_msg.choices:
                                if last_msg.selected_choice is None:
                                    self.story_area._show_choices([
                                        {"id": c.id, "text": c.text} for c in last_msg.choices
                                    ])
                                else:
                                    self.story_area._show_selected_choice(
                                        last_msg.choices,
                                        last_msg.selected_choice
                                    )
                        
                        chapters = self.story_area.get_chapters()
                        if chapters:
                            current_chapter = self._game_state.chapter
                            self.status_bar.update_chapters(chapters, current_chapter)
                        
                        self._show_info("存档已加载！")
    
    def _show_info(self, message: str):
        InfoBar.success(
            title="成功",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _show_error(self, message: str):
        InfoBar.error(
            title="错误",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        
        self.setStyleSheet(f"""
            #GalgameInterface {{
                background-color: {bg_color};
            }}
        """)
        
        self.top_panel.update_theme()
        self.story_area.update_theme()
        self.status_bar.update_theme()
