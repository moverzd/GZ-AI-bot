import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Literal
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Импортируем константы из оригинального файла
from .llm_generator import SYSTEM_PROMT, USER_PROMPT

class MultiLLMGenerator:
    """
    Класс для генерации ответов с помощью разных LLM провайдеров (OpenAI, DeepSeek).
    """
    
    def __init__(self, provider: Literal["openai", "deepseek"] = "openai"):
        self.provider = provider
        self.client = None
        self.system_prompt = SYSTEM_PROMT
        
        # Настройка API ключей и базовых URL в зависимости от провайдера
        if provider == "openai":
            self.api_key = os.environ.get('OPENAI_API_KEY')
            self.base_url = None
            self.model = "gpt-4o-mini"
        elif provider == "deepseek":
            self.api_key = os.environ.get('DEEPSEEK_API_KEY')
            self.base_url = "https://api.deepseek.com"
            self.model = "deepseek-chat"
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")
    
    async def generate_response(self, query: str, search_results: List[Dict[str, Any]]) -> str:
        """
        Генерирует ответ LLM на основе запроса и результатов поиска.
        """
        logger.info(f"Генерация ответа {self.provider.upper()} для запроса: {query}")
        
        if not search_results:
            return "Я не могу ответить на этот вопрос, так как не нашел релевантной информации в документах."
        
        if not self.api_key:
            logger.error(f"API ключ {self.provider.upper()} не найден")
            return f"Ошибка: API ключ {self.provider.upper()} не найден."
        
        # Формируем контекст из найденных документов
        context = self._build_context(search_results)
        logger.info(f"Контекст для {self.provider.upper()}: {len(context)} символов")
        
        # Формируем пользовательский промпт
        user_prompt = self._build_user_prompt(query, context)
        
        try:
            # Инициализируем клиента, если еще не инициализирован
            if not self.client:
                if self.base_url:
                    self.client = AsyncOpenAI(
                        api_key=self.api_key, 
                        base_url=self.base_url,
                        timeout=60.0
                    )
                else:
                    self.client = AsyncOpenAI(api_key=self.api_key, timeout=60.0)
            
            # Устанавливаем переменную окружения для отключения параллелизма токенизаторов
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            logger.info(f"Отправляем запрос к {self.provider.upper()} API...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Низкая температура для точных ответов с данными
                max_tokens=1500,  # Увеличиваем лимит токенов для более полных ответов
                timeout=45  # Таймаут для запроса
            )
            
            answer = response.choices[0].message.content or "Ответ не получен"
            logger.info(f"Получен ответ от {self.provider.upper()} API длиной {len(answer)} символов")
            
            return answer
            
        except asyncio.TimeoutError:
            logger.error(f"Превышено время ожидания ответа от {self.provider.upper()} API")
            return f"Превышено время ожидания ответа от {self.provider.upper()}. Пожалуйста, попробуйте еще раз."
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа {self.provider.upper()}: {e}")
            return f"Произошла ошибка при генерации ответа {self.provider.upper()}: {str(e)}"
    
    def _build_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Формирует контекст из результатов поиска для передачи в LLM.
        """
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            product_id = result.get("product_id")
            product_name = result.get("product_name", f"Документ {i}")
            similarity = result.get("similarity", 0)
            text = result.get("text", "") or result.get("text_preview", "")
            
            # Логируем информацию о документе
            logger.info(f"Документ #{i}: '{product_name}' (ID: {product_id}, сходство: {similarity:.4f})")
            
            # Добавляем информацию о документе в контекст
            document_header = f"=== ДОКУМЕНТ {i}: {product_name} ===\n"
            document_content = f"{text}\n"
            
            context_parts.append(document_header + document_content)
        
        return "\n".join(context_parts)
    
    def _build_user_prompt(self, query: str, context: str) -> str:
        """
        Формирует пользовательский промпт для LLM.
        """
        return USER_PROMPT.format(context=context, query=query)
    
    async def close(self):
        """Закрывает соединение с API."""
        if self.client:
            await self.client.close()
