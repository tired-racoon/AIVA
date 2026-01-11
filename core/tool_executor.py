import json
from typing import Dict, List, Any, Optional
from tools import BaseTool, OSControlTool, MusicTool, WebSearchTool
from utils import setup_logger

logger = setup_logger(__name__)

class ToolExecutor:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {
            "os_control": OSControlTool(),
            "music": MusicTool(),
            "web_search": WebSearchTool()
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
                "description": "Управление Яндекс.Музыкой: поиск и воспроизведение треков, исполнителей, альбомов",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["search", "play_track", "play_artist", "play_album", "play_likes", "stop_music", "get_track_info"],
                            "description": "Действие с музыкой"
                        },
                        "query": {
                            "type": "string",
                            "description": "Поисковой запрос для поиска музыки"
                        },
                        "track_id": {
                            "type": "string",
                            "description": "ID трека или название трека для воспроизведения. Можно передать как числовой ID, так и название трека"
                        },
                        "artist_id": {
                            "type": "string",
                            "description": "ID исполнителя или имя исполнителя для воспроизведения. Можно передать как числовой ID, так и имя исполнителя"
                        },
                        "album_id": {
                            "type": "string",
                            "description": "ID альбома или название альбома для воспроизведения. Можно передать как числовой ID, так и название альбома"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Количество треков для воспроизведения (для исполнителя)",
                            "default": 10
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["sequential", "random"],
                            "description": "Режим воспроизведения любимых треков. sequential - последовательно в порядке добавления в избранное, random - в случайном порядке. Используй 'sequential' когда пользователь говорит 'включи любимое', 'включи мои треки', 'включи избранное'. Используй 'random' когда пользователь говорит 'включи любимое в случайном порядке', 'включи микс из любимого'."
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
        
        return tools
    
    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        action = arguments.pop("action", None)
        if not action:
            return "Error: action not specified"
        
        return self.execute(tool_name, action, arguments)