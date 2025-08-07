import logging
from typing import Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Глобальный менеджер для управления моделью эмбеддингов.
    Обеспечивает загрузку модели только один раз и переиспользование.
    """
    
    _instance: Optional['ModelManager'] = None
    _model: Optional[SentenceTransformer] = None
    _model_name: Optional[str] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(self, model_name: str = 'deepvk/USER-bge-m3') -> SentenceTransformer:
        """
        Получает модель эмбеддингов. Загружает модель только при первом вызове
        или при изменении имени модели.
        """
        if self._model is None or self._model_name != model_name:
            logger.info(f"Загружаем модель эмбеддингов: {model_name}")
            self._model = SentenceTransformer(model_name)
            self._model_name = model_name
            logger.info(f"Модель {model_name} успешно загружена")
        
        return self._model
    
    def preload_model(self, model_name: str = 'deepvk/USER-bge-m3'):
        """
        Предзагружает модель при старте приложения.
        """
        logger.info(f"Предзагрузка модели {model_name}...")
        self.get_model(model_name)
        logger.info(f"Модель {model_name} предзагружена и готова к использованию")
    
    def is_model_loaded(self, model_name: str = 'deepvk/USER-bge-m3') -> bool:
        """
        Проверяет, загружена ли модель с указанным именем.
        """
        return self._model is not None and self._model_name == model_name


# Глобальный экземпляр менеджера модели
model_manager = ModelManager()
