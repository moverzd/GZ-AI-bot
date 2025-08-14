-- ========================================
-- GZ AI Bot - Database Setup Script
-- Создание пустой базы данных со всеми таблицами
-- ========================================

-- Создание базы данных с правильной кодировкой
CREATE DATABASE IF NOT EXISTS gzbot_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE gzbot_db;

-- ========================================
-- Таблица категорий продуктов
-- ========================================
DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Основная таблица продуктов
-- ========================================
DROP TABLE IF EXISTS `products`;
CREATE TABLE `products` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `category_id` int unsigned NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `fk_prod_cat` (`category_id`),
  FULLTEXT KEY `idx_ft_product` (`name`),
  CONSTRAINT `fk_prod_cat` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Таблица сфер применения
-- ========================================
DROP TABLE IF EXISTS `spheres`;
CREATE TABLE `spheres` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Связь продуктов со сферами применения
-- ========================================
DROP TABLE IF EXISTS `product_spheres`;
CREATE TABLE `product_spheres` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int unsigned NOT NULL,
  `sphere_id` int unsigned NOT NULL,
  `product_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `advantages` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ux_prod_sphere` (`product_id`,`sphere_id`),
  KEY `fk_ps_product` (`product_id`),
  KEY `fk_ps_sphere` (`sphere_id`),
  CONSTRAINT `fk_ps_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ps_sphere` FOREIGN KEY (`sphere_id`) REFERENCES `spheres` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Таблица файлов продуктов
-- ========================================
DROP TABLE IF EXISTS `product_files`;
CREATE TABLE `product_files` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `product_id` int unsigned NOT NULL,
  `file_id` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `kind` enum('image','video','document','presentation','pdf','word','excel','archive','other') COLLATE utf8mb4_unicode_ci NOT NULL,
  `ordering` int NOT NULL DEFAULT '0',
  `uploaded_by` bigint DEFAULT NULL,
  `uploaded_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `file_size` bigint DEFAULT NULL,
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `original_filename` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_main_image` tinyint(1) NOT NULL DEFAULT '0',
  `local_path` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ux_prod_kind_order` (`product_id`,`kind`,`ordering`),
  KEY `idx_pf_product` (`product_id`),
  KEY `idx_pf_kind` (`kind`),
  KEY `idx_pf_main_image` (`is_main_image`),
  CONSTRAINT `fk_pf_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Группы продуктов (если используется)
-- ========================================
DROP TABLE IF EXISTS `product_groups`;
CREATE TABLE `product_groups` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Триггеры для автоматической синхронизации
-- ========================================

-- ========================================
-- Индексы для оптимизации производительности
-- ========================================

-- Дополнительные индексы для поиска
ALTER TABLE `products` ADD INDEX `idx_is_deleted` (`is_deleted`);
ALTER TABLE `product_files` ADD INDEX `idx_is_deleted` (`is_deleted`);
ALTER TABLE `product_files` ADD INDEX `idx_uploaded_at` (`uploaded_at`);

-- Составные индексы для часто используемых запросов
ALTER TABLE `product_spheres` ADD INDEX `idx_product_sphere_active` (`product_id`, `sphere_id`);
ALTER TABLE `product_files` ADD INDEX `idx_product_kind_active` (`product_id`, `kind`, `is_deleted`);

-- ========================================
-- Вставка базовых данных (опционально)
-- ========================================

-- Можно добавить базовые категории
-- INSERT INTO `categories` (`name`) VALUES 
-- ('Праймеры «БРИТ»'),
-- ('Материалы рулонные'),
-- ('Ленты «БРИТ»'),
-- ('Составы, эмульсии и добавки'),
-- ('Промышленно-гражданские мастики'),
-- ('Дорожно-аэродромные мастики'),
-- ('Герметики «БРИТ»');

-- Можно добавить базовые сферы применения
-- INSERT INTO `spheres` (`name`) VALUES 
-- ('Дорожное строительство'),
-- ('Мостовые сооружения'),
-- ('Кровельные работы'),
-- ('Гидроизоляция'),
-- ('Промышленное строительство');

-- ========================================
-- Таблицы для отслеживания взаимодействий
-- ========================================

-- Таблица для хранения запросов пользователей
CREATE TABLE user_queries (
  id int NOT NULL AUTO_INCREMENT,
  user_id int NOT NULL,
  username varchar(255) DEFAULT NULL,
  query_text text NOT NULL,
  query_type enum('search','ai_question','product_view') NOT NULL DEFAULT 'search',
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_queries_user_id (user_id),
  KEY idx_user_queries_created_at (created_at),
  KEY idx_user_queries_type (query_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица для хранения ответов бота
CREATE TABLE bot_responses (
  id int NOT NULL AUTO_INCREMENT,
  query_id int NOT NULL,
  response_text text NOT NULL,
  response_type varchar(50) NOT NULL DEFAULT 'ai_generated',
  execution_time decimal(8,3) DEFAULT NULL,
  sources_count int DEFAULT '0',
  message_id int DEFAULT NULL,
  created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_bot_responses_query_id (query_id),
  KEY idx_bot_responses_created_at (created_at),
  KEY idx_bot_responses_type (response_type),
  FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- Информация о созданной структуре
-- ========================================

SELECT 'База данных gzbot_db успешно создана!' as message;
SELECT 'Созданные таблицы:' as tables_created;
SHOW TABLES;

-- ========================================
-- Конец скрипта
-- ========================================
