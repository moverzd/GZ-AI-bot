import os
from typing import List
from dotenv import load_dotenv

"""
Файл конфигурации.
Создает класс Settings, который хранит:
- настройки базы данных 
- токен тг
- список админов
"""

load_dotenv()

class Settings:
    """
    Инициализация из .env
    """
    def __init__(self):
        # Токен Telegram бота
        self.bot_token = os.getenv("TG_BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("TG_BOT_TOKEN is required")
        
        # Настройки базы данных
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", "3306"))
        self.db_user = os.getenv("DB_USER", "root")
        self.db_pass = os.getenv("DB_PASS", None)
        if self.db_pass is None:
            raise ValueError("DB_PASS is required")
        self.db_name = os.getenv("DB_NAME")
        if not self.db_name:
            raise ValueError("DB_NAME is required")
        
        # Список ID администраторов
        admin_ids_raw = os.getenv("TG_ADMIN_IDS", "")
        # Убираем комментарии (все после #) и парсим ID
        admin_ids_clean = admin_ids_raw.split('#')[0].strip()
        self.admin_ids = [int(item.strip()) for item in admin_ids_clean.split(",") if item.strip().isdigit()]

    # превращает метод в атрибут: settings.database_url() -> settings.database_url
    @property
    def database_url(self) -> str:
        """Формирует строку подключения к базе данных"""
        return f"mysql+aiomysql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

# Создаем экземпляр настроек для использования в приложении
settings = Settings()

# Экспортируем для обратной совместимости
BOT_TOKEN = settings.bot_token
DATABASE_URL = settings.database_url
TG_ADMIN_IDS = settings.admin_ids