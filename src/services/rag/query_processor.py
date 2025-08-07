import re
import logging

logger = logging.getLogger(__name__)

class QueryProcessor:
    """
    Класс для минимальной обработки поисковых запросов.
    """
    
    def clean_query(self, query_text: str) -> str:
        """
        Очистка запроса: удаление пробелов
        """
        if not query_text or not isinstance(query_text, str):
            return ""
            
        cleaned_query = " ".join(query_text.strip().split())
        
        logger.info(f"Исходный запрос: '{query_text}'")
        logger.info(f"Очищенный запрос: '{cleaned_query}'")

        return cleaned_query
    
    def extract_product_names(self, query: str) -> list:
        """
        Извлекает названия продуктов из запроса.
        """
        # Паттерны для поиска названий продуктов
        patterns = [
            r'[ТтMm]-\d+',  # T-65, Т-75, M-100 и т.д.
            r'[А-Яа-я]+-\d+',  # ЗВС-65, БТ-75 и т.д.
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

       # TODO: сравнить результаты 
        print(f"Исходный запрос: {query}")
        print(f"Очищенный запрос: {unique_products}")
        return unique_products
