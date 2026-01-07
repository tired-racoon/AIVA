from providers import BaseLLMProvider, LocalHFProvider, YandexProvider, OpenRouterProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

def get_provider() -> BaseLLMProvider:
    provider_map = {
        "local": LocalHFProvider,
        "yandex": YandexProvider,
        "openrouter": OpenRouterProvider
    }
    
    provider_class = provider_map.get(settings.llm_provider)
    if not provider_class:
        logger.error(f"Unknown provider: {settings.llm_provider}")
        raise ValueError(f"Unknown provider: {settings.llm_provider}")
    
    logger.info(f"Using provider: {settings.llm_provider}")
    return provider_class()