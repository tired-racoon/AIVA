from typing import Dict, Any
from datetime import datetime
import locale
from .base import BaseTool
from utils import setup_logger

logger = setup_logger(__name__)

class TimeTool(BaseTool):
    def __init__(self):
        try:
            locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
        except:
            pass
        logger.info("Time tool initialized")
    
    def _hours_to_words(self, hours: int) -> str:
        hour_names = {
            0: 'ноль', 1: 'один', 2: 'два', 3: 'три', 4: 'четыре',
            5: 'пять', 6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять',
            10: 'десять', 11: 'одиннадцать', 12: 'двенадцать', 13: 'тринадцать',
            14: 'четырнадцать', 15: 'пятнадцать', 16: 'шестнадцать',
            17: 'семнадцать', 18: 'восемнадцать', 19: 'девятнадцать',
            20: 'двадцать', 21: 'двадцать один', 22: 'двадцать два',
            23: 'двадцать три'
        }
        return hour_names.get(hours, str(hours))
    
    def _minutes_to_words(self, minutes: int) -> str:
        ones = ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
        tens = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят']
        teens = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 
                'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать']
        
        if minutes == 0:
            return 'ноль'
        elif minutes < 10:
            return ones[minutes]
        elif 10 <= minutes < 20:
            return teens[minutes - 10]
        else:
            return (tens[minutes // 10] + ' ' + ones[minutes % 10]).strip()
    
    def _get_hour_word(self, hours: int) -> str:
        if hours % 10 == 1 and hours % 100 != 11:
            return 'час'
        elif hours % 10 in [2, 3, 4] and hours % 100 not in [12, 13, 14]:
            return 'часа'
        else:
            return 'часов'
    
    def _get_minute_word(self, minutes: int) -> str:
        if minutes % 10 == 1 and minutes % 100 != 11:
            return 'минута'
        elif minutes % 10 in [2, 3, 4] and minutes % 100 not in [12, 13, 14]:
            return 'минуты'
        else:
            return 'минут'
    
    def execute(self, action: str, params: Dict[str, Any]) -> str:
        try:
            if action == "get_current_time":
                now = datetime.now()
                date_str = now.strftime("%d.%m.%Y")
                weekday = now.strftime("%A")
                
                hours = now.hour
                minutes = now.minute
                
                hours_word = self._hours_to_words(hours)
                hour_form = self._get_hour_word(hours)
                
                if minutes == 0:
                    time_str = f"{hours_word} {hour_form}"
                else:
                    minutes_word = self._minutes_to_words(minutes)
                    minute_form = self._get_minute_word(minutes)
                    time_str = f"{hours_word} {hour_form} {minutes_word} {minute_form}"
                
                return f"Текущая дата и время: {date_str}, {time_str} ({weekday})"
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            logger.error(f"Error in time tool: {e}")
            return f"Ошибка: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "time",
            "description": "Get current date and time",
            "actions": {
                "get_current_time": {}
            }
        }