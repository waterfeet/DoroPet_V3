#!/usr/bin/env python3
"""
Open-Meteo 天气查询工具
无需 API Key，开箱即用
支持自动获取当前城市
"""

import requests
import json
from datetime import datetime
from typing import Optional, Dict, Tuple


WEATHER_CODES = {
    0: "晴朗", 1: "多云", 2: "多云", 3: "阴天",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "阵雨", 82: "暴雨",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "大雷阵雨伴冰雹"
}

WEATHER_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌧️", 53: "🌧️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "❄️", 73: "❄️", 75: "❄️",
    80: "🌦️", 81: "🌦️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️"
}


def get_current_location() -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
    """通过IP自动获取当前城市位置"""
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            lat = data.get("latitude")
            lon = data.get("longitude")
            city = data.get("city")
            country = data.get("country_name")
            return lat, lon, city, country
    except Exception:
        pass
    
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                lat = data.get("lat")
                lon = data.get("lon")
                city = data.get("city")
                country = data.get("country")
                return lat, lon, city, country
    except Exception:
        pass
    
    return None, None, None, None


def geocoding(city_name: str) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str]]:
    """将城市名转换为经纬度"""
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&format=json"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get("results"):
            return None, None, None, None
        
        result = data["results"][0]
        return result["latitude"], result["longitude"], result["name"], result["country"]
    except Exception:
        return None, None, None, None


def get_weather_data(lat: float, lon: float, city_name: str, country: str) -> Dict:
    """获取天气数据并返回字典格式"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data.get("current", {})
        daily = data.get("daily", {})
        
        weather_code = current.get("weather_code", 0)
        weather_desc = WEATHER_CODES.get(weather_code, "未知")
        weather_icon = WEATHER_ICONS.get(weather_code, "🌤️")
        
        temperature = current.get("temperature_2m", "--")
        humidity = current.get("relative_humidity_2m", "--")
        wind_speed = current.get("wind_speed_10m", "--")
        
        forecast = []
        if daily.get("time"):
            for i in range(min(3, len(daily["time"]))):
                date = daily["time"][i]
                high = daily["temperature_2m_max"][i] if i < len(daily["temperature_2m_max"]) else "--"
                low = daily["temperature_2m_min"][i] if i < len(daily["temperature_2m_min"]) else "--"
                code = daily["weather_code"][i] if i < len(daily["weather_code"]) else 0
                desc = WEATHER_CODES.get(code, "未知")
                forecast.append({
                    "date": date,
                    "weather": desc,
                    "high": high,
                    "low": low
                })
        
        return {
            "success": True,
            "location": f"{city_name}, {country}",
            "city": city_name,
            "country": country,
            "temperature": f"{temperature}°C",
            "temp_value": temperature,
            "humidity": f"{humidity}%",
            "wind_speed": f"{wind_speed} km/h",
            "weather_code": weather_code,
            "weather_desc": weather_desc,
            "icon": weather_icon,
            "description": f"{weather_desc}，温度{temperature}°C，湿度{humidity}%，风速{wind_speed}km/h",
            "forecast": forecast
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "location": "未知位置",
            "temperature": "--",
            "icon": "🌤️",
            "description": f"天气数据获取失败: {str(e)}"
        }


def query_weather(city_name: str = None) -> Dict:
    """
    查询天气主函数
    
    Args:
        city_name: 城市名称（英文或拼音），如果为None则自动获取当前位置
    
    Returns:
        包含天气信息的字典
    """
    if city_name:
        city_name = city_name.strip()
        lat, lon, name, country = geocoding(city_name)
        
        if lat is None:
            return {
                "success": False,
                "error": f"找不到城市: {city_name}",
                "location": city_name,
                "temperature": "--",
                "icon": "❓",
                "description": f"找不到城市「{city_name}」，请检查城市名称（建议使用英文或拼音，如: Beijing, Shanghai）"
            }
    else:
        lat, lon, name, country = get_current_location()
        
        if lat is None:
            return {
                "success": False,
                "error": "无法获取当前位置",
                "location": "未知位置",
                "temperature": "--",
                "icon": "❓",
                "description": "无法自动获取当前位置，请手动输入城市名称"
            }
    
    return get_weather_data(lat, lon, name, country)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python weather_tool.py [城市名]")
        print("示例: python weather_tool.py Beijing")
        print("      python weather_tool.py  (自动获取当前位置)")
        print("提示: 请使用英文或拼音输入城市名（如: Beijing, Shanghai, Kunming, London）")
        
        print("\n正在自动获取当前位置的天气...")
        result = query_weather()
    else:
        city_name = sys.argv[1]
        print(f"正在查询 {city_name} 的天气...")
        result = query_weather(city_name)
    
    if result["success"]:
        print(f"\n{'='*50}")
        print(f"📍 {result['location']}")
        print(f"{'='*50}")
        print(f"🌤️  当前天气: {result['weather_desc']}")
        print(f"🌡️  温度: {result['temperature']}")
        print(f"💧 湿度: {result['humidity']}")
        print(f"💨 风速: {result['wind_speed']}")
        
        if result.get("forecast"):
            print(f"\n📅 未来3天预报:")
            print(f"{'-'*50}")
            for f in result["forecast"]:
                print(f"📆 {f['date']}: {f['weather']}, {f['high']}°C / {f['low']}°C")
        print(f"{'='*50}\n")
    else:
        print(f"\n❌ {result['description']}\n")


if __name__ == "__main__":
    main()
