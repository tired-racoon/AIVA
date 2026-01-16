import json
from typing import Dict, List, Any, Optional
from tools import BaseTool, OSControlTool, MusicTool, WebSearchTool, TimeTool
from utils import setup_logger

logger = setup_logger(__name__)

class ToolExecutor:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {
            "os_control": OSControlTool(),
            "music": MusicTool(),
            "web_search": WebSearchTool(),
            "time": TimeTool()
        }
        logger.info("Tool executor initialized")
    
    def execute(self, tool_name: str, action: str, params: Dict) -> str:
        tool = self.tools.get(tool_name)
        if not tool:
            logger.warning(f"Unknown tool: {tool_name}")
            return f"Unknown tool: {tool_name}"
        
        logger.info(f"Executing {tool_name}.{action} with params: {params}")
        result = tool.execute(action, params)
        logger.info(f"Tool execution result: {result}")
        return result
    
    def get_tools_definition(self) -> List[Dict[str, Any]]:
        tools = []
        
        tools.append({
            "type": "function",
            "function": {
                "name": "os_control",
                "description": "Управление системными настройками: громкость, яркость экрана",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["set_volume", "mute", "unmute", "set_brightness"],
                            "description": "Действие для выполнения"
                        },
                        "level": {
                            "type": "integer",
                            "description": "Уровень громкости или яркости (0-100)",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "required": ["action"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "music",
                "description": "Управление Яндекс.Музыкой: поиск и воспроизведение треков, исполнителей, альбомов, пауза",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["search", "play_track", "play_artist", "play_album", "play_likes", "stop_music", "pause_music", "resume_music", "get_track_info"],
                            "description": "Действие с музыкой"
                        },
                        "query": {
                            "type": "string",
                            "description": "Поисковой запрос для поиска музыки"
                        },
                        "track_id": {
                            "type": "string",
                            "description": "ID трека или название трека для воспроизведения"
                        },
                        "artist_id": {
                            "type": "string",
                            "description": "ID исполнителя или имя исполнителя"
                        },
                        "album_id": {
                            "type": "string",
                            "description": "ID альбома или название альбома"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Количество треков",
                            "default": 10
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["sequential", "random"],
                            "description": "Режим воспроизведения"
                        }
                    },
                    "required": ["action"]
                }
            }
        })
                
        tools.append({
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Поиск информации в интернете через DuckDuckGo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["search"],
                            "description": "Действие поиска"
                        },
                        "query": {
                            "type": "string",
                            "description": "Поисковой запрос"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Максимальное количество результатов",
                            "default": 10,
                            "minimum": 5,
                            "maximum": 15
                        }
                    },
                    "required": ["action", "query"]
                }
            }
        })
        

        tools.append({
            "type": "function",
            "function": {
                "name": "time",
                "description": "Получение текущей даты и времени. Используй этот инструмент когда пользователь спрашивает 'сколько времени', 'какое время', 'который час', 'какая дата', 'какой сегодня день'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get_current_time"],
                            "description": "Получить текущее время"
                        }
                    },
                    "required": ["action"]
                }
            }
        })

        return tools
    
    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        action = arguments.pop("action", None)
        if not action:
            return "Error: action not specified"
        
        return self.execute(tool_name, action, arguments)