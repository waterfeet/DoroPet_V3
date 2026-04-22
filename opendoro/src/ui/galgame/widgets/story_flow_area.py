from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import ScrollArea, isDarkTheme

from .story_message_card import StoryMessageCard
from .choice_buttons import ChoiceButtonsPanel
from .chapter_title_card import ChapterTitleCard
from ..models import StoryMessage, GameChoice, MessageRole


class StoryFlowArea(ScrollArea):
    choice_selected = pyqtSignal(int)
    chapter_changed = pyqtSignal(int, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("storyFlowArea")
        self._message_cards = []
        self._current_choices = []
        self._choice_panel = None
        self._current_chapter = 0
        self._chapter_cards = {}
        self._story_font_size = 14
        self._title_font_size = 16
        self.init_ui()
    
    def init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.container = QWidget()
        self.container.setObjectName("storyFlowContainer")
        
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        self.layout.addStretch()
        
        self.setWidget(self.container)
        self.update_theme()
    
    def set_font_sizes(self, story_size: int, title_size: int):
        self._story_font_size = story_size
        self._title_font_size = title_size
        
        for card in self._message_cards:
            card.set_font_size(story_size)
        
        for chapter_card in self._chapter_cards.values():
            chapter_card.set_font_size(title_size)
    
    def add_message(self, message: StoryMessage):
        chapter_num = message.chapter_number
        chapter_name = message.chapter_name
        
        if chapter_num != self._current_chapter:
            self._add_chapter_title(chapter_num, chapter_name)
            self._current_chapter = chapter_num
            self.chapter_changed.emit(chapter_num, chapter_name)
        
        card = StoryMessageCard(message, self)
        card.set_font_size(self._story_font_size)
        self._message_cards.append(card)
        
        self.layout.insertWidget(self.layout.count() - 1, card)
    
    def _add_chapter_title(self, chapter_num: int, chapter_name: str):
        if chapter_num in self._chapter_cards:
            return
        
        chapter_card = ChapterTitleCard(chapter_num, chapter_name, self)
        chapter_card.set_font_size(self._title_font_size)
        self._chapter_cards[chapter_num] = chapter_card
        self.layout.insertWidget(self.layout.count() - 1, chapter_card)
    
    def add_streaming_message(self, role: str = "narrator", character_name: str = None, chapter_number: int = 1, chapter_name: str = "") -> StoryMessageCard:
        # Convert string role to MessageRole enum
        role_enum = MessageRole(role) if isinstance(role, str) else role
        temp_message = StoryMessage(
            id=0,
            role=role_enum,
            character_name=character_name,
            content="",
            chapter_number=chapter_number,
            chapter_name=chapter_name
        )
        card = StoryMessageCard(temp_message, self, is_streaming=True)
        card.set_font_size(self._story_font_size)
        self._message_cards.append(card)
        
        # 检查是否需要添加章节标题
        if chapter_number != self._current_chapter:
            self._add_chapter_title(chapter_number, chapter_name)
            self._current_chapter = chapter_number
            self.chapter_changed.emit(chapter_number, chapter_name)
        
        self.layout.insertWidget(self.layout.count() - 1, card)
        return card
    
    def update_streaming_content(self, card: StoryMessageCard, content: str):
        card.update_content(content)
    
    def finalize_streaming_card(self, card: StoryMessageCard, parsed_result: dict):
        # 用最终的故事内容更新卡片
        story = parsed_result.get('story', '')
        if story:
            card.update_content(story)
        
        card.set_choices_visible(False)
        self._current_choices = parsed_result.get('choices', [])
        
        if self._current_choices:
            self._show_choices(self._current_choices)
    
    def _show_choices(self, choices: list):
        if self._choice_panel:
            self.layout.removeWidget(self._choice_panel)
            self._choice_panel.deleteLater()
        
        self._choice_panel = ChoiceButtonsPanel(choices, self)
        self._choice_panel.choice_clicked.connect(self._on_choice_clicked)
        
        self.layout.insertWidget(self.layout.count() - 1, self._choice_panel)
    
    def _show_selected_choice(self, choices: list, selected_id: int):
        if self._choice_panel:
            self.layout.removeWidget(self._choice_panel)
            self._choice_panel.deleteLater()
        
        choice_data = [{"id": c.id, "text": c.text} for c in choices]
        self._choice_panel = ChoiceButtonsPanel(choice_data, self)
        self._choice_panel.choice_clicked.connect(self._on_choice_clicked)
        
        self._choice_panel.set_enabled(False)
        self._choice_panel.set_selected(selected_id)
        
        self.layout.insertWidget(self.layout.count() - 1, self._choice_panel)
    
    def _on_choice_clicked(self, choice_id: int):
        if self._choice_panel:
            self._choice_panel.set_enabled(False)
            self._choice_panel.set_selected(choice_id)
        
        self.choice_selected.emit(choice_id)
    
    def clear_choices(self):
        if self._choice_panel:
            self.layout.removeWidget(self._choice_panel)
            self._choice_panel.deleteLater()
            self._choice_panel = None
        self._current_choices = []
    
    def clear_all(self):
        for card in self._message_cards:
            self.layout.removeWidget(card)
            card.deleteLater()
        self._message_cards.clear()
        
        for chapter_card in self._chapter_cards.values():
            self.layout.removeWidget(chapter_card)
            chapter_card.deleteLater()
        self._chapter_cards.clear()
        self._current_chapter = 0
        
        self.clear_choices()
    
    def scroll_to_chapter(self, chapter_num: int):
        if chapter_num in self._chapter_cards:
            chapter_card = self._chapter_cards[chapter_num]
            self.ensureWidgetVisible(chapter_card)
    
    def get_chapters(self):
        return sorted(self._chapter_cards.keys())
    
    def update_theme(self):
        is_dark = isDarkTheme()
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        
        self.setStyleSheet(f"""
            #storyFlowArea, #storyFlowContainer {{
                background-color: {bg_color};
                border: none;
            }}
        """)
        
        for card in self._message_cards:
            card.update_theme()
        
        for chapter_card in self._chapter_cards.values():
            chapter_card.update_theme()
        
        if self._choice_panel:
            self._choice_panel.update_theme()
