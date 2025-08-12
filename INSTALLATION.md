# Установка и запуск GZ AI Bot

## Быстрый старт

### 1. Создание окружения
```bash
conda create -n gzbot python=3.12
conda activate gzbot
pip install -r requirements.txt
```

### 2. Настройка конфигурации
Пример конфигурации `.env`:
```env
# MYSQL settings
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_mysql_password
DB_NAME=gzbot_db

# Telegram settings
TG_BOT_TOKEN=7123456789:AAHdqTcvbXorOxmNTkj4dQAI0S3X2LQjOyA
TG_ADMIN_IDS=123456789,987654321

# OpenAI API
OPENAI_API_KEY=sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz

# File storage
DOWNLOAD_FOLDER=src/files/
```

### 3. Инициализация базы данных
```bash
mysql -u root -p < database_setup.sql
```

### 4. Запуск
```bash
python bot.py
```

## Архитектура базы данных

### MySQL - основное хранилище
Используется для структурированных данных: продукты, категории, пользователи, документы, запросы пользователей, метрики ответов системы

**1. categories** - Категории продуктов
- `id`, `name`

**2. products** - Каталог продуктов  
- `id`, `category_id`, `name`, `created_at`, `updated_at`, `is_deleted`

**3. spheres** - Сферы применения
- `id`, `name`

**4. product_spheres** - Связь продуктов со сферами
- `id`, `product_id`, `sphere_id`, `product_name`, `advantages`, `description`

**5. product_files** - Файлы и медиа
- `id`, `product_id`, `file_id`, `kind`, `ordering`, `title`, `local_path`, `is_main_image`

**6. product_package** - Информация об упаковке
- `id`, `product_id`, `package_info`

**7. user_queries** - Логирование запросов пользователей
- `id`, `user_id`, `username`, `query_text`, `query_type`, `created_at`

**8. bot_responses** - Метрики ответов системы
- `id`, `query_id`, `response_text`, `response_type`, `execution_time`, `sources_count`, `message_id`, `created_at`

### ChromaDB - векторное хранилище
**ChromaDB** — это векторное хранилище, предназначенное для семантического поиска по документам с использованием метода Retrieval-Augmented Generation (RAG). Хранилище автоматически создается в каталоге `./chroma_db/`. Оно содержит эмбеддинги текстовых фрагментов, а также метаданные документов, что позволяет эффективно организовать и ускорить поиск информации на основе семантического анализа.

## Диагностика

При запуске система проверяет состояние компонентов:
- Подключение к MySQL
- Инициализация ChromaDB  
- Загрузка модели эмбеддингов
- Статус файлового сервиса
- Готовность поисковой системы

Администраторы получают уведомление о статусе в Telegram.

## Структура проекта

```
gzbot/
├── bot.py                    # Точка входа
├── requirements.txt          # Python зависимости  
├── database_setup.sql        # Схема БД (пустая)
├── backup_2025-08-12.sql    # Бэкап с данными
├── .env                   # Конфигурация
├── src/
│   ├── config/              # Настройки
│   ├── database/            # ORM модели, репозитории
│   ├── handlers/            # Telegram обработчики
│   ├── keyboards/           # UI клавиатуры
│   ├── middlewares/         # Промежуточные слои
│   ├── services/            # Бизнес-логика
│   └── files/              # Медиа файлы продуктов
└── chroma_db/              # Векторная БД (автосоздание)
```

## Технический стек

- **Backend**: Python 3.12, aiogram 3.4+
- **Databases**: MySQL 8.0+, ChromaDB
- **ML**: sentence-transformers, PyTorch
- **File Processing**: pandas, openpyxl, PyPDF2
