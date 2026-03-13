#!/usr/bin/env python3
"""
Emoji utilities for favicon generation.
Provides emoji suggestions based on project descriptions and emoji rendering.
"""

import re
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    import emoji as emoji_lib
except ImportError:
    emoji_lib = None

try:
    from pilmoji import Pilmoji
    PILMOJI_AVAILABLE = True
except (ImportError, AttributeError):
    # Handle both import errors and compatibility issues with pilmoji/emoji
    PILMOJI_AVAILABLE = False
    Pilmoji = None

# Curated emoji database with keywords for better matching
# Format: emoji -> (name, keywords, category)
EMOJI_DATABASE = {
    # Technology & Development
    "🚀": ("rocket", ["rocket", "launch", "startup", "space", "speed", "growth"], "tech"),
    "💻": ("laptop", ["computer", "laptop", "code", "dev", "developer", "programming"], "tech"),
    "⚡": ("lightning", ["fast", "speed", "energy", "power", "quick", "performance"], "tech"),
    "🔧": ("wrench", ["tool", "tools", "build", "fix", "settings", "maintenance"], "tech"),
    "🛠️": ("tools", ["tool", "tools", "build", "construction", "development"], "tech"),
    "📱": ("phone", ["mobile", "app", "phone", "smartphone", "application"], "tech"),
    "🌐": ("globe", ["web", "website", "global", "internet", "world", "online"], "tech"),
    "💡": ("bulb", ["idea", "innovation", "creative", "light", "bright", "solution"], "tech"),

    # Business & Commerce
    "🏪": ("store", ["shop", "store", "retail", "business", "commerce"], "business"),
    "🛒": ("cart", ["shopping", "cart", "ecommerce", "buy", "purchase"], "business"),
    "💼": ("briefcase", ["business", "work", "professional", "office", "corporate"], "business"),
    "💰": ("money", ["money", "finance", "payment", "cash", "wealth"], "business"),
    "💳": ("card", ["credit", "card", "payment", "transaction", "banking"], "business"),
    "📊": ("chart", ["analytics", "chart", "data", "stats", "graph", "metrics"], "business"),
    "📈": ("trending", ["growth", "trending", "increase", "success", "profit"], "business"),

    # Food & Beverage
    "☕": ("coffee", ["coffee", "cafe", "beverage", "drink", "tea"], "food"),
    "🍕": ("pizza", ["pizza", "food", "restaurant", "italian", "dining"], "food"),
    "🍔": ("burger", ["burger", "food", "restaurant", "fast food", "dining"], "food"),
    "🍰": ("cake", ["cake", "bakery", "dessert", "sweet", "pastry"], "food"),
    "🍺": ("beer", ["beer", "bar", "pub", "drink", "alcohol", "brewery"], "food"),
    "🍽️": ("dining", ["restaurant", "dining", "food", "meal", "eat"], "food"),
    "🥗": ("salad", ["healthy", "salad", "food", "fresh", "organic", "vegetable"], "food"),

    # Health & Fitness
    "💪": ("muscle", ["fitness", "gym", "health", "workout", "strong", "exercise"], "health"),
    "❤️": ("heart", ["health", "love", "care", "wellness", "medical"], "health"),
    "🏃": ("running", ["fitness", "run", "sport", "exercise", "active"], "health"),
    "🧘": ("yoga", ["yoga", "meditation", "wellness", "mindfulness", "zen"], "health"),

    # Education & Learning
    "📚": ("books", ["education", "learning", "books", "study", "knowledge"], "education"),
    "🎓": ("graduation", ["education", "school", "university", "learning", "graduate"], "education"),
    "✏️": ("pencil", ["write", "edit", "draw", "create", "education"], "education"),
    "🧠": ("brain", ["think", "smart", "intelligence", "learning", "knowledge"], "education"),

    # Creative & Design
    "🎨": ("art", ["art", "design", "creative", "paint", "color"], "creative"),
    "📷": ("camera", ["photo", "photography", "picture", "image", "visual"], "creative"),
    "🎬": ("movie", ["video", "film", "movie", "production", "cinema"], "creative"),
    "🎵": ("music", ["music", "audio", "sound", "song", "melody"], "creative"),
    "✨": ("sparkles", ["magic", "special", "shine", "star", "highlight"], "creative"),

    # Communication & Social
    "💬": ("chat", ["chat", "message", "talk", "communication", "conversation"], "social"),
    "📧": ("email", ["email", "mail", "message", "contact", "communication"], "social"),
    "📢": ("announcement", ["announce", "broadcast", "news", "alert", "notification"], "social"),
    "🤝": ("handshake", ["partnership", "deal", "agreement", "collaboration"], "social"),

    # Travel & Places
    "✈️": ("airplane", ["travel", "flight", "airplane", "trip", "vacation"], "travel"),
    "🏨": ("hotel", ["hotel", "accommodation", "stay", "lodging", "hospitality"], "travel"),
    "🗺️": ("map", ["map", "navigation", "location", "direction", "travel"], "travel"),
    "📍": ("pin", ["location", "place", "map", "pin", "address", "local"], "travel"),
    "🌍": ("earth", ["global", "world", "international", "planet", "earth"], "travel"),

    # Entertainment & Gaming
    "🎮": ("game", ["game", "gaming", "play", "video game", "entertainment"], "entertainment"),
    "🎯": ("target", ["goal", "target", "aim", "focus", "precision"], "entertainment"),
    "🎪": ("circus", ["event", "entertainment", "show", "fun", "festival"], "entertainment"),
    "🎉": ("party", ["celebrate", "party", "event", "celebration", "fun"], "entertainment"),

    # Nature & Animals
    "🌱": ("plant", ["growth", "nature", "plant", "green", "eco", "organic"], "nature"),
    "🌳": ("tree", ["nature", "tree", "environment", "green", "eco"], "nature"),
    "🐶": ("dog", ["dog", "pet", "animal", "puppy"], "nature"),
    "🐱": ("cat", ["cat", "pet", "animal", "kitten"], "nature"),

    # Generic/Universal
    "⭐": ("star", ["star", "favorite", "best", "quality", "rating"], "generic"),
    "🌟": ("glowing", ["star", "shine", "special", "featured", "highlight"], "generic"),
    "✅": ("check", ["check", "done", "complete", "verified", "success"], "generic"),
    "🔥": ("fire", ["hot", "trending", "popular", "fire", "exciting"], "generic"),
    "👍": ("thumbs_up", ["like", "good", "approve", "yes", "positive"], "generic"),
    "🏆": ("trophy", ["winner", "award", "achievement", "success", "champion"], "generic"),
}


def extract_keywords(description: str) -> List[str]:
    """
    Extract keywords from project description.

    Args:
        description: Project description text

    Returns:
        List of lowercase keywords
    """
    # Convert to lowercase
    text = description.lower()

    # Remove punctuation and split
    words = re.findall(r'\b\w+\b', text)

    # Filter out common stop words
    stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'for', 'to', 'in', 'on', 'at',
                  'with', 'from', 'by', 'about', 'my', 'our', 'your', 'this', 'that'}

    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    return keywords


def score_emoji(emoji_data: tuple, keywords: List[str]) -> int:
    """
    Score an emoji based on keyword matches.

    Args:
        emoji_data: Tuple of (name, keywords, category)
        keywords: List of user keywords

    Returns:
        Match score (higher is better)
    """
    name, emoji_keywords, category = emoji_data
    score = 0

    for keyword in keywords:
        # Exact keyword match
        if keyword in emoji_keywords:
            score += 10
        # Partial match
        elif any(keyword in ek or ek in keyword for ek in emoji_keywords):
            score += 5
        # Name match
        if keyword in name or name in keyword:
            score += 8

    return score


def suggest_emojis(description: str, count: int = 4) -> List[Dict[str, str]]:
    """
    Suggest relevant emojis based on project description.

    Args:
        description: Description of the project/website/app
        count: Number of emoji suggestions to return (default: 4)

    Returns:
        List of dicts with 'emoji', 'name', and 'description' keys
    """
    if not description:
        # Return generic popular emojis if no description
        return [
            {"emoji": "🚀", "name": "Rocket", "description": "Launch, startup, fast growth"},
            {"emoji": "⭐", "name": "Star", "description": "Featured, favorite, quality"},
            {"emoji": "💡", "name": "Light Bulb", "description": "Ideas, innovation, solutions"},
            {"emoji": "🌟", "name": "Glowing Star", "description": "Special, highlighted, shine"},
        ]

    # Extract keywords from description
    keywords = extract_keywords(description)

    # Score all emojis
    scored_emojis = []
    for emoji_char, emoji_data in EMOJI_DATABASE.items():
        score = score_emoji(emoji_data, keywords)
        if score > 0:  # Only include emojis with matches
            name, emoji_keywords, category = emoji_data
            scored_emojis.append({
                "emoji": emoji_char,
                "name": name.replace("_", " ").title(),
                "description": ", ".join(emoji_keywords[:3]),
                "score": score,
                "category": category
            })

    # Sort by score (highest first)
    scored_emojis.sort(key=lambda x: x['score'], reverse=True)

    # Ensure diversity: try to get emojis from different categories
    selected = []
    used_categories = set()

    # First pass: select top scoring emoji from each category
    for emoji in scored_emojis:
        if len(selected) >= count:
            break
        if emoji['category'] not in used_categories:
            selected.append(emoji)
            used_categories.add(emoji['category'])

    # Second pass: fill remaining slots with highest scoring regardless of category
    for emoji in scored_emojis:
        if len(selected) >= count:
            break
        if emoji not in selected:
            selected.append(emoji)

    # If still not enough, add generic fallbacks
    fallbacks = [
        {"emoji": "⭐", "name": "Star", "description": "Featured, favorite, quality"},
        {"emoji": "🌟", "name": "Glowing Star", "description": "Special, highlighted"},
        {"emoji": "✨", "name": "Sparkles", "description": "Magic, special"},
        {"emoji": "💫", "name": "Dizzy", "description": "Exciting, dynamic"},
    ]

    for fallback in fallbacks:
        if len(selected) >= count:
            break
        if fallback not in selected:
            selected.append(fallback)

    # Remove score from output and return only the requested count
    result = []
    for emoji in selected[:count]:
        result.append({
            "emoji": emoji["emoji"],
            "name": emoji["name"],
            "description": emoji["description"]
        })

    return result


def get_emoji_name(emoji_char: str) -> str:
    """
    Get the name of an emoji character.

    Args:
        emoji_char: Emoji character (e.g., "🚀")

    Returns:
        Emoji name or empty string if not found
    """
    if emoji_char in EMOJI_DATABASE:
        return EMOJI_DATABASE[emoji_char][0].replace("_", " ").title()

    # Fallback to emoji library if available
    if emoji_lib:
        try:
            return emoji_lib.demojize(emoji_char).strip(':').replace('_', ' ').title()
        except:
            pass

    return ""


def generate_emoji_icon(emoji_char: str, size: Tuple[int, int], bg_color: Optional[str] = None) -> Image.Image:
    """
    Generate an icon image from an emoji character.

    Args:
        emoji_char: Unicode emoji character (e.g., "🚀")
        size: Tuple of (width, height) in pixels
        bg_color: Optional background color (hex or name). If None, transparent background.

    Returns:
        PIL Image object with the emoji rendered

    Raises:
        ImportError: If pilmoji library is not installed
        ValueError: If emoji_char is empty or invalid
    """
    if not PILMOJI_AVAILABLE:
        raise ImportError(
            "pilmoji library is required for emoji rendering. "
            "Install it with: pip install pilmoji"
        )

    if not emoji_char:
        raise ValueError("emoji_char cannot be empty")

    # Create image with background
    if bg_color:
        # Solid background color
        img = Image.new('RGB', size, bg_color)
    else:
        # Transparent background
        img = Image.new('RGBA', size, (0, 0, 0, 0))

    # Calculate emoji font size
    # Use 75% of the minimum dimension to leave padding
    emoji_size = int(min(size) * 0.75)

    # Use Pilmoji to render the emoji
    with Pilmoji(img) as pilmoji:
        # Get text bounding box to center properly
        # Pilmoji doesn't provide easy centering, so we estimate
        # Emojis are roughly square, so we can center based on size

        # Calculate position (centered)
        x = (size[0] - emoji_size) // 2
        y = (size[1] - emoji_size) // 2

        # Render emoji
        # Note: Pilmoji uses font_size parameter for emoji size
        pilmoji.text((x, y), emoji_char, font=None, fill=(0, 0, 0, 0),
                     emoji_scale_factor=emoji_size/64)  # Pilmoji default emoji size is 64

    return img


def generate_emoji_icon_fallback(emoji_char: str, size: Tuple[int, int], bg_color: Optional[str] = None) -> Image.Image:
    """
    Fallback method to generate emoji icon using system fonts.
    Used when Pilmoji is not available.

    Args:
        emoji_char: Unicode emoji character
        size: Tuple of (width, height)
        bg_color: Optional background color

    Returns:
        PIL Image with emoji (may not render properly on all systems)
    """
    # Create image
    if bg_color:
        img = Image.new('RGB', size, bg_color)
    else:
        img = Image.new('RGBA', size, (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)

    # Try to use a color emoji font
    emoji_size = int(min(size) * 0.75)

    # Try common emoji font paths
    font_paths = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",  # macOS
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",  # Linux
        "C:\\Windows\\Fonts\\seguiemj.ttf",  # Windows
    ]

    font = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, emoji_size)
            break
        except:
            continue

    if not font:
        # Fallback to default font with text representation
        font = ImageFont.load_default()
        text = f"Emoji: {emoji_char}"
    else:
        text = emoji_char

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    # Draw the emoji
    draw.text((x, y), text, font=font, embedded_color=True, fill=(0, 0, 0))

    return img


if __name__ == '__main__':
    # Test the suggestion system
    test_cases = [
        "coffee shop website",
        "rocket launch startup",
        "fitness gym app",
        "pizza delivery service",
        "online education platform",
        "travel booking site",
    ]

    print("Emoji Suggestion Tests")
    print("=" * 80)

    for description in test_cases:
        print(f"\nDescription: '{description}'")
        print("-" * 80)
        suggestions = suggest_emojis(description, count=4)
        for i, emoji_data in enumerate(suggestions, 1):
            print(f"{i}. {emoji_data['emoji']}  {emoji_data['name']:<20} - {emoji_data['description']}")
