import re

FONT_SIZE_MAP = {
    'font_size_xxs': 10,
    'font_size_xs': 11,
    'font_size_s': 12,
    'font_size_body': 13,
    'font_size_m': 14,
    'font_size_l': 15,
    'font_size_xl': 16,
    'font_size_xxl': 18,
    'font_size_xxxl': 20,
    'font_size_display': 24,
    'font_size_headline': 28,
    'font_size_hero': 36,
}

def scale_font_size(size_name, scale=1.0):
    base_size = FONT_SIZE_MAP.get(size_name, 14)
    return int(base_size * scale)

def apply_font_scale(qss, scale=1.0):
    result = qss
    for size_name, base_size in FONT_SIZE_MAP.items():
        placeholder = f'@{size_name}@'
        scaled_size = int(base_size * scale)
        result = result.replace(placeholder, f'{scaled_size}px')
    return result

def get_font_size_placeholder(size_name):
    return f'@{size_name}@'
