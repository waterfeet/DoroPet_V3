from typing import Optional, Dict, List
from PyQt5.QtCore import QThread, pyqtSignal
from src.core.logger import logger

from .models import Protagonist, Character, WorldSetting, GameState, StoryCache
from .story_generator import StoryGenerator


class StoryGenerationWorker(QThread):
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        method_name: str,
        *args,
        **kwargs
    ):
        super().__init__()
        self.generator = generator
        self.method_name = method_name
        self.args = args
        self.kwargs = kwargs
        self._is_stopped = False
        self._full_text = ""
    
    def run(self):
        try:
            method = getattr(self.generator, self.method_name)
            gen = method(*self.args, **self.kwargs)
            
            self._full_text = ""
            result = None
            
            try:
                while True:
                    if self._is_stopped:
                        logger.info("Story generation stopped by user")
                        break
                    
                    text = next(gen)
                    self._full_text += text
                    self.text_generated.emit(text)
                    
            except StopIteration as e:
                result = e.value
            
            if not self._is_stopped:
                if result is None:
                    from .response_parser import ResponseParser
                    result = ResponseParser.parse(self._full_text)
                
                self.generation_complete.emit(result)
                
        except Exception as e:
            logger.error(f"Story generation error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True


class StoryPlanWorker(QThread):
    plan_complete = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.protagonist = protagonist
        self.characters = characters
        self.world_setting = world_setting
        self.model_id = model_id
    
    def run(self):
        try:
            cache = self.generator.generate_story_plan(
                self.protagonist,
                self.characters,
                self.world_setting,
                self.model_id
            )
            self.plan_complete.emit(cache)
        except Exception as e:
            logger.error(f"Story plan error: {e}")
            self.error_occurred.emit(str(e))


class ChapterSummaryWorker(QThread):
    summary_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        chapter_messages: List[str],
        story_cache: StoryCache,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.chapter_messages = chapter_messages
        self.story_cache = story_cache
        self.model_id = model_id
    
    def run(self):
        try:
            summary = self.generator.generate_chapter_summary(
                self.chapter_messages,
                self.story_cache,
                self.model_id
            )
            self.summary_complete.emit(summary)
        except Exception as e:
            logger.error(f"Chapter summary error: {e}")
            self.error_occurred.emit(str(e))


class NextChapterPlanWorker(QThread):
    plan_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        story_cache: StoryCache,
        current_state: GameState,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.story_cache = story_cache
        self.current_state = current_state
        self.model_id = model_id
    
    def run(self):
        try:
            plan = self.generator.generate_next_chapter_plan(
                self.story_cache,
                self.current_state,
                self.model_id
            )
            self.plan_complete.emit(plan)
        except Exception as e:
            logger.error(f"Next chapter plan error: {e}")
            self.error_occurred.emit(str(e))


class ChapterOpeningWorker(QThread):
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        story_cache: StoryCache,
        current_state: GameState,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.story_cache = story_cache
        self.current_state = current_state
        self.model_id = model_id
        self._is_stopped = False
        self._full_text = ""
    
    def run(self):
        try:
            gen = self.generator.generate_chapter_opening(
                self.story_cache,
                self.current_state,
                self.model_id
            )
            
            self._full_text = ""
            result = None
            
            try:
                while True:
                    if self._is_stopped:
                        logger.info("Chapter opening generation stopped")
                        break
                    
                    text = next(gen)
                    self._full_text += text
                    self.text_generated.emit(text)
                    
            except StopIteration as e:
                result = e.value
            
            if not self._is_stopped:
                if result is None:
                    from .response_parser import ResponseParser
                    result = ResponseParser.parse(self._full_text)
                
                self.generation_complete.emit(result)
                
        except Exception as e:
            logger.error(f"Chapter opening error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True


class ChapterContinuationWorker(QThread):
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        context: List[Dict],
        choice: str,
        story_cache: StoryCache,
        current_state: GameState,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.context = context
        self.choice = choice
        self.story_cache = story_cache
        self.current_state = current_state
        self.model_id = model_id
        self._is_stopped = False
        self._full_text = ""
    
    def run(self):
        try:
            gen = self.generator.generate_chapter_continuation(
                self.context,
                self.choice,
                self.story_cache,
                self.current_state,
                self.model_id
            )
            
            self._full_text = ""
            result = None
            
            try:
                while True:
                    if self._is_stopped:
                        logger.info("Chapter continuation generation stopped")
                        break
                    
                    text = next(gen)
                    self._full_text += text
                    self.text_generated.emit(text)
                    
            except StopIteration as e:
                result = e.value
            
            if not self._is_stopped:
                if result is None:
                    from .response_parser import ResponseParser
                    result = ResponseParser.parse(self._full_text)
                
                self.generation_complete.emit(result)
                
        except Exception as e:
            logger.error(f"Chapter continuation error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True


class StartStoryWorker(QThread):
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        protagonist: Protagonist,
        characters: List[Character],
        world_setting: WorldSetting,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.protagonist = protagonist
        self.characters = characters
        self.world_setting = world_setting
        self.model_id = model_id
        self._is_stopped = False
        self._full_text = ""
    
    def run(self):
        try:
            gen = self.generator.generate_story_start(
                self.protagonist,
                self.characters,
                self.world_setting,
                self.model_id
            )
            
            self._full_text = ""
            result = None
            
            try:
                while True:
                    if self._is_stopped:
                        logger.info("Start story generation stopped")
                        break
                    
                    text = next(gen)
                    self._full_text += text
                    self.text_generated.emit(text)
                    
            except StopIteration as e:
                result = e.value
            
            if not self._is_stopped:
                if result is None:
                    from .response_parser import ResponseParser
                    result = ResponseParser.parse(self._full_text)
                
                self.generation_complete.emit(result)
                
        except Exception as e:
            logger.error(f"Start story error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True


class ContinueStoryWorker(QThread):
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        context: List[Dict],
        choice: str,
        current_state: GameState,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.context = context
        self.choice = choice
        self.current_state = current_state
        self.model_id = model_id
        self._is_stopped = False
        self._full_text = ""
    
    def run(self):
        try:
            gen = self.generator.generate_next_scene(
                self.context,
                self.choice,
                self.current_state,
                self.model_id
            )
            
            self._full_text = ""
            result = None
            
            try:
                while True:
                    if self._is_stopped:
                        logger.info("Continue story generation stopped")
                        break
                    
                    text = next(gen)
                    self._full_text += text
                    self.text_generated.emit(text)
                    
            except StopIteration as e:
                result = e.value
            
            if not self._is_stopped:
                if result is None:
                    from .response_parser import ResponseParser
                    result = ResponseParser.parse(self._full_text)
                
                self.generation_complete.emit(result)
                
        except Exception as e:
            logger.error(f"Continue story error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True


class SpecialSceneWorker(QThread):
    text_generated = pyqtSignal(str)
    generation_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        generator: StoryGenerator,
        scene_type: str,
        current_state: GameState,
        extra_params: Dict = None,
        model_id: Optional[str] = None
    ):
        super().__init__()
        self.generator = generator
        self.scene_type = scene_type
        self.current_state = current_state
        self.extra_params = extra_params or {}
        self.model_id = model_id
        self._is_stopped = False
        self._full_text = ""
    
    def run(self):
        try:
            gen = self.generator.generate_special_scene(
                self.scene_type,
                self.current_state,
                self.extra_params,
                self.model_id
            )
            
            self._full_text = ""
            result = None
            
            try:
                while True:
                    if self._is_stopped:
                        logger.info("Special scene generation stopped")
                        break
                    
                    text = next(gen)
                    self._full_text += text
                    self.text_generated.emit(text)
                    
            except StopIteration as e:
                result = e.value
            
            if not self._is_stopped:
                if result is None:
                    from .response_parser import ResponseParser
                    result = ResponseParser.parse(self._full_text)
                
                self.generation_complete.emit(result)
                
        except Exception as e:
            logger.error(f"Special scene error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        self._is_stopped = True
