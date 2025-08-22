-- Инициализация базы данных для Positive Support Bot
-- Этот файл выполняется при первом запуске PostgreSQL контейнера

-- Создание базы данных если она не существует
-- (PostgreSQL в Docker уже создает БД из POSTGRES_DB)

-- Установка кодировки
ALTER DATABASE support_bot SET client_encoding TO 'utf8';
ALTER DATABASE support_bot SET default_text_search_config TO 'pg_catalog.russian';

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Логирование
\echo 'Инициализация базы данных завершена'
