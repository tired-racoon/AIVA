from providers import BaseLLMProvider, LocalHFProvider, YandexProvider, OpenRouterProvider
from config.settings import get_settings
from utils import setup_logger

logger = setup_logger(__name__)

_provider_cache = {}

def get_provider() -> BaseLLMProvider:
    settings = get_settings()
    
    cache_key = f"{settings.llm_provider}_{settings.local_model_name}_{settings.yandex_model}_{settings.openrouter_model}"
    
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]
    
    provider_map = {
        "local": LocalHFProvider,
        "yandex": YandexProvider,
        "openrouter": OpenRouterProvider
    }
    
    provider_class = provider_map.get(settings.llm_provider)
    if not provider_class:
        logger.error(f"Unknown provider: {settings.llm_provider}")
        raise ValueError(f"Unknown provider: {settings.llm_provider}")
    
    logger.info(f"Creating new provider: {settings.llm_provider}")
    provider = provider_class()
    _provider_cache[cache_key] = provider
    
    return provider

def clear_provider_cache():
    global _provider_cache
    _provider_cache.clear()
    logger.info("Provider cache cleared")