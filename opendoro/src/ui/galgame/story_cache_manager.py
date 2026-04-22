from typing import Dict, List
from .models import StoryCache, ChapterData


class StoryCacheManager:
    
    @staticmethod
    def update_after_response(cache: StoryCache) -> None:
        cache.current_chapter.response_count += 1
    
    @staticmethod
    def update_after_chapter_summary(cache: StoryCache, summary: Dict) -> None:
        chapter_summary = summary.get('chapter_summary', '')
        if chapter_summary:
            cache.previous_chapter_summaries.append(chapter_summary)
        
        cache.current_chapter.is_completed = True
        
        for event in summary.get('key_events', []):
            if event and event not in cache.key_plot_points:
                cache.key_plot_points.append(event)
        
        for fs in summary.get('new_foreshadowing', []):
            if fs and fs not in cache.foreshadowing:
                cache.foreshadowing.append(fs)
        
        for resolved in summary.get('resolved_foreshadowing', []):
            if resolved in cache.foreshadowing:
                cache.foreshadowing.remove(resolved)
    
    @staticmethod
    def update_after_chapter_plan(cache: StoryCache, plan: Dict) -> None:
        new_chapter = ChapterData(
            chapter_number=cache.current_chapter.chapter_number + 1,
            chapter_name=plan.get('chapter_name', ''),
            chapter_outline=plan.get('chapter_outline', ''),
            opening_setting=plan.get('opening_setting', ''),
            response_count=0,
            is_completed=False
        )
        cache.current_chapter = new_chapter
    
    @staticmethod
    def update_after_story_plan(cache: StoryCache, plan: Dict) -> None:
        cache.story_synopsis = plan.get('story_synopsis', '')
        cache.world_analysis = plan.get('world_analysis', '')
        cache.character_analysis = plan.get('character_analysis', '')
        
        first_chapter = plan.get('first_chapter', {})
        cache.current_chapter = ChapterData(
            chapter_number=1,
            chapter_name=first_chapter.get('chapter_name', ''),
            chapter_outline=first_chapter.get('chapter_outline', ''),
            opening_setting=first_chapter.get('opening_setting', ''),
            response_count=0,
            is_completed=False
        )
        
        for point in plan.get('key_plot_points', []):
            if point and point not in cache.key_plot_points:
                cache.key_plot_points.append(point)
        
        for fs in plan.get('foreshadowing', []):
            if fs and fs not in cache.foreshadowing:
                cache.foreshadowing.append(fs)
    
    @staticmethod
    def should_transition_chapter(cache: StoryCache) -> bool:
        return cache.current_chapter.response_count >= 3
    
    @staticmethod
    def get_chapter_display_name(cache: StoryCache) -> str:
        chapter = cache.current_chapter
        if chapter.chapter_name and chapter.chapter_name.strip():
            return chapter.chapter_name.strip()
        return ""
    
    @staticmethod
    def get_previous_summaries_text(cache: StoryCache, max_chapters: int = 3) -> str:
        if not cache.previous_chapter_summaries:
            return "无"
        
        recent = cache.previous_chapter_summaries[-max_chapters:]
        return "\n\n".join([f"第{i+1}章摘要：{s}" for i, s in enumerate(recent)])
    
    @staticmethod
    def get_key_plots_text(cache: StoryCache) -> str:
        if not cache.key_plot_points:
            return "暂无"
        return "、".join(cache.key_plot_points[-5:])
    
    @staticmethod
    def get_foreshadowing_text(cache: StoryCache) -> str:
        if not cache.foreshadowing:
            return "暂无"
        return "、".join(cache.foreshadowing)
    
    @staticmethod
    def create_empty_cache() -> StoryCache:
        return StoryCache()
