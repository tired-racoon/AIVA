from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage
from langchain_core.tools import Tool
from tools import OSControlTool, MusicTool, WebSearchTool, TimeTool
from utils import setup_logger

logger = setup_logger(__name__)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    next_action: str

class LangGraphExecutor:
    def __init__(self):
        self.tools = {
            "os_control": OSControlTool(),
            "music": MusicTool(),
            "web_search": WebSearchTool(),
            "time": TimeTool()
        }
        
        self.langchain_tools = self._create_langchain_tools()
        self.tool_node = ToolNode(self.langchain_tools)
        self.graph = self._build_graph()
        
        logger.info("LangGraph executor initialized")
    
    def _create_langchain_tools(self) -> List[Tool]:
        tools = []
        
        for name, tool_instance in self.tools.items():
            schema = tool_instance.get_schema()
            
            for action_name, action_params in schema["actions"].items():
                tool = Tool(
                    name=f"{name}_{action_name}",
                    func=lambda params, n=name, a=action_name: self.tools[n].execute(a, params),
                    description=f"{schema['description']} - {action_name}"
                )
                tools.append(tool)
        
        return tools
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        workflow.add_node("tools", self.tool_node)
        
        def route_decision(state: AgentState) -> str:
            messages = state["messages"]
            last_message = messages[-1]
            
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END
        
        workflow.set_conditional_entry_point(route_decision)
        workflow.add_edge("tools", END)
        
        return workflow.compile()
    
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
    
    def execute_with_graph(self, tool_calls: List[Dict[str, Any]]) -> str:
        results = []
        
        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = tool_call["arguments"]
            
            if function_name not in self.tools:
                results.append(f"[{function_name}]: Unknown tool")
                continue
            
            action = arguments.pop("action", None)
            if not action:
                results.append(f"[{function_name}]: action not specified")
                continue
            
            logger.info(f"Executing {function_name}.{action} with args: {arguments}")
            result = self.tools[function_name].execute(action, arguments)
            results.append(f"[{function_name}]: {result}")
        
        return "\n".join(results)
    
    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        action = arguments.pop("action", None)
        if not action:
            return "Error: action not specified"
        
        if tool_name not in self.tools:
            return f"Unknown tool: {tool_name}"
        
        return self.tools[tool_name].execute(action, arguments)