import re
import logging

logger = logging.getLogger(__name__)

class QueryProcessor:
    """
    Класс для минимальной обработки поисковых запросов.
    """
    
    def clean_query(self, query_text: str) -> str:
        """
        Улучшенная очистка и расширение запроса
        """
        if not query_text or not isinstance(query_text, str):
            return ""
        
        # Базовая очистка
        cleaned_query = " ".join(query_text.strip().split())
        
        # Добавляем синонимы и расширения для лучшего поиска
        query_expansions = []
        
        # Расширяем запрос синонимами битумных терминов
        expansions = {
            "битум": ["битумный", "битумная", "асфальт"],
            "гидроизоляция": ["гидроизоляционный", "водозащита", "влагозащита"],
            "кровля": ["кровельный", "крыша", "покрытие"],
            "температура": ["термический", "тепловой", "нагрев", "размягчения"],
            "применение": ["использование", "область применения", "назначение"],
            "характеристики": ["свойства", "параметры", "показатели", "спецификация"],
            "отличие": ["разница", "различие", "сравнение", "отличается"],
            "мастика": ["герметик", "состав", "материал"],
            "гибкость": ["эластичность", "пластичность"],
            "прочность": ["стойкость", "устойчивость"],
        }
        
        # Ищем ключевые слова и добавляем синонимы
        query_lower = cleaned_query.lower()
        for key, synonyms in expansions.items():
            if key in query_lower:
                query_expansions.extend(synonyms)
        
        # Если найдены расширения, добавляем их к запросу
        if query_expansions:
            expanded_query = cleaned_query + " " + " ".join(query_expansions)
        else:
            expanded_query = cleaned_query
            
        logger.info(f"Исходный запрос: '{query_text}'")
        logger.info(f"Расширенный запрос: '{expanded_query}'")

        return expanded_query
    
    def extract_product_names(self, query: str) -> list:
        """
        Извлекает названия продуктов из запроса.
        """
        # Паттерны для поиска названий продуктов
        patterns = [
            r'[ТтTt]-?\d+',  # T-65, Т-75, T75, Т75, M-100 и т.д.
            r'[А-Яа-я]+-?\d+',  # ЗВС-65, БТ-75, ЗВС65 и т.д.
            r'«[^»]+»',  # продукты в кавычках
            r'"[^"]+"',  # продукты в двойных кавычках
        ]
        
        products = []
        for pattern in patterns:
            matches = re.findall(pattern, query)
            products.extend(matches)
        
        # Убираем дубликаты и кавычки
        unique_products = []
        for product in products:
            clean_product = product.strip('«»"\'')
            if clean_product and clean_product not in unique_products:
                unique_products.append(clean_product)

        logger.info(f"Исходный запрос: '{query}'")
        logger.info(f"Извлеченные продукты: {unique_products}")
        return unique_products
