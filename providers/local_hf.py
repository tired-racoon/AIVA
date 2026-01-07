import json
import re
from typing import List, Dict, Iterator, Optional, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from .base import BaseLLMProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class LocalHFProvider(BaseLLMProvider):
    def __init__(self):
        logger.info(f"Loading local model: {settings.local_model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(settings.local_model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            settings.local_model_name,
            torch_dtype="auto",
            device_map=settings.local_device_map
        )
        logger.info("Local model loaded successfully")
    
    def _build_tool_prompt(self, tools: List[Dict[str, Any]]) -> str:
        if not tools:
            return ""
        
        tools_desc = """Ты - голосовой помощник Айва, который может как отвечать на вопросы, так и использовать инструменты.

    ВАЖНО: 
    - Если пользователь просто общается или задает вопрос, на который ты знаешь ответ - отвечай ОБЫЧНЫМ ТЕКСТОМ
    - Используй инструменты ТОЛЬКО когда это действительно нужно (поиск в интернете, управление музыкой, системные настройки)

    Доступные инструменты:

    """
        
        for tool in tools:
            func = tool["function"]
            tools_desc += f"Функция: {func['name']}\n"
            tools_desc += f"Описание: {func['description']}\n"
            tools_desc += f"Параметры: {json.dumps(func['parameters'], ensure_ascii=False)}\n\n"
        
        tools_desc += "\nФормат вызова функции (используй ТОЛЬКО при необходимости):\n"
        tools_desc += '{"function": "имя_функции", "arguments": {...}}\n\n'
        
        return tools_desc
    
    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        json_match = re.search(r'\{[^\}]*"function"[^\}]*\}', text, re.DOTALL)
        if json_match:
            try:
                tool_call = json.loads(json_match.group())
                return tool_call
            except json.JSONDecodeError:
                pass
        return None

    def generate(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        
        if tools:
            system_prompt = self._build_tool_prompt(tools)
            messages_with_tools = [{"role": "system", "content": system_prompt}] + messages
        else:
            messages_with_tools = messages
        
        try:
            text = self.tokenizer.apply_chat_template(
                messages_with_tools,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except Exception as e:
            logger.warning(f"Chat template failed: {e}, using fallback")
            text = "\n\n".join([f"{m['role']}: {m['content']}" for m in messages_with_tools])
            text += "\n\nassistant:"
        
        model_inputs = self.tokenizer([text], return_tensors="pt")
        
        if hasattr(self.model, 'device'):
            model_inputs = model_inputs.to(self.model.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=settings.max_tokens,
                temperature=settings.temperature,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=True
            )
        
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
        content = self.tokenizer.decode(output_ids, skip_special_tokens=True).strip()
        
        tool_call = self._parse_tool_call(content) if tools else None
        
        if tool_call:
            return {
                "content": None,
                "tool_calls": [{
                    "function": tool_call["function"],
                    "arguments": tool_call.get("arguments", {})
                }]
            }
        
        return {
            "content": content,
            "tool_calls": None
        }
    
    def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[Dict[str, Any]]:
        
        result = self.generate(messages, tools)
        
        if result.get("content"):
            yield {
                "type": "content",
                "content": result["content"],
                "tool_calls": None
            }
        
        if result.get("tool_calls"):
            yield {
                "type": "tool_calls",
                "content": result.get("content"),
                "tool_calls": result["tool_calls"]
            }