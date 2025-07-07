import re
from typing import List, Optional
from sqlalchemy import select, func, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ProductFile, Product, ProductSphere, Category, Sphere

def normalize_search_query(query: str) -> List[str]:
    """
    Нормализует поисковый запрос для более точного поиска
    
    Примеры:
    "БМ-50" -> ["бм-50", "бм50", "бм 50"]
    "бм 50" -> ["бм 50", "бм50", "бм-50"]
    "мб50" -> ["мб50", "мб-50", "мб 50"]
    "брит а" -> ["брита", "брит-а", "брит а", "брит", "брита"]
    "бм" -> ["бм"]  # Короткие запросы остаются как есть
    """
    if not query:
        return []
    
    # Приводим к нижнему регистру и убираем лишние пробелы
    normalized = query.lower().strip()
    
    # Если запрос слишком короткий (1-2 символа), ищем только точное совпадение
    if len(normalized) <= 2:
        return [normalized]
    
    # Список вариантов поиска
    search_variants = [normalized]
    
    # Удаляем все пробелы и дефисы для создания "сжатой" версии запроса
    condensed_query = re.sub(r'[\s\-]+', '', normalized)
    if condensed_query != normalized and len(condensed_query) >= 3:
        search_variants.append(condensed_query)
    
    # Проверяем, есть ли в запросе буквы и цифры (например, "мб50")
    has_letters_and_digits = bool(re.search(r'[а-яёa-z]', normalized)) and bool(re.search(r'\d', normalized))
    
    # Если есть пробелы или дефисы, добавляем альтернативы
    if '-' in normalized or ' ' in normalized:
        # Добавляем вариант с пробелами вместо дефисов
        with_spaces = re.sub(r'[\-]+', ' ', normalized)
        if with_spaces != normalized and with_spaces not in search_variants:
            search_variants.append(with_spaces)
        
        # Добавляем вариант с дефисами вместо пробелов
        with_dashes = re.sub(r'\s+', '-', normalized)
        if with_dashes != normalized and with_dashes not in search_variants:
            search_variants.append(with_dashes)
        
        # Если запрос состоит из отдельных букв/слов (например "брит а"), 
        # создаем вариант с объединением всех частей
        parts = re.split(r'[\s\-]+', normalized)
        if len(parts) > 1:
            # Вариант с полным объединением всех частей
            joined = ''.join(parts)
            if joined not in search_variants:
                search_variants.append(joined)
            
            # Специальная обработка для запросов типа "брит а" - также добавляем просто "брит"
            if len(parts) == 2 and len(parts[1]) == 1:
                if parts[0] not in search_variants:
                    search_variants.append(parts[0])
            
            # Варианты с объединением пар соседних частей
            for i in range(len(parts) - 1):
                # Объединяем текущую часть со следующей
                combined_parts = parts.copy()
                combined_parts[i] = parts[i] + parts[i + 1]
                combined_parts.pop(i + 1)
                
                # Создаем вариант с пробелами
                with_spaces_pair = ' '.join(combined_parts)
                if with_spaces_pair not in search_variants:
                    search_variants.append(with_spaces_pair)
                
                # Создаем вариант с дефисами
                with_dashes_pair = '-'.join(combined_parts)
                if with_dashes_pair not in search_variants:
                    search_variants.append(with_dashes_pair)
    
    # Если в запросе есть буквы и цифры (например "мб50"), добавляем варианты с разделителями
    if has_letters_and_digits:
        # Добавляем вариант с дефисом между буквами и цифрами
        with_dash = re.sub(r'([а-яёa-z]+)(\d+)', r'\1-\2', normalized)
        if with_dash != normalized and with_dash not in search_variants:
            search_variants.append(with_dash)
        
        # Добавляем вариант с пробелом между буквами и цифрами
        with_space = re.sub(r'([а-яёa-z]+)(\d+)', r'\1 \2', normalized)
        if with_space != normalized and with_space not in search_variants:
            search_variants.append(with_space)
    
    # Для дополнительной точности: если запрос имеет формат "X Y", где X и Y - однобуквенные части,
    # добавляем варианты "XY" и "X-Y"
    if re.match(r'^[а-яёa-z]\s+[а-яёa-z]$', normalized):
        single_letters = normalized.split()
        combined = ''.join(single_letters)
        if combined not in search_variants:
            search_variants.append(combined)
        
        with_dash = '-'.join(single_letters)
        if with_dash not in search_variants:
            search_variants.append(with_dash)
    
    # Убираем дубликаты, сохраняя порядок
    unique_variants = []
    for variant in search_variants:
        if variant and variant not in unique_variants:
            unique_variants.append(variant)
    
    return unique_variants

"""
Controling admin panel:
- soft removing products
- get main image
- get docs
- insert main and description images
- insert doc
"""

class ProductRepository:
    """
    repository to work with products
    """
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, product_id:int) -> Optional[Product]:
        """
        return product id
        """
        result = await self.session.execute(
            select(Product).where(Product.id == product_id, Product.is_deleted == False)
        )
        return result.scalars().first()
    
    async def search(self, query: str) -> List[Product]:
        """
        searching product by query with improved accuracy
        Поддерживает расширенный поиск по нескольким словам, разным форматам,
        учитывает разделенные буквы (например, "брит а" для поиска "БРИТ А")
        """
        if not query or len(query.strip()) == 0:
            return []
        
        # Нормализуем поисковый запрос
        search_variants = normalize_search_query(query)
        
        # Создаем условия для поиска
        or_conditions = []
        
        # Добавляем обычные условия по имени продукта для каждого варианта запроса
        for variant in search_variants:
            # Основной поиск по варианту
            or_conditions.append(Product.name.ilike(f"%{variant}%"))
            
            # Для каждого варианта добавляем условия с перевернутым регистром
            # (помогает с поиском по смешанным регистрам типа "БрИт А")
            if variant != variant.upper() and variant != variant.lower():
                or_conditions.append(Product.name.ilike(f"%{variant.upper()}%"))
                or_conditions.append(Product.name.ilike(f"%{variant.lower()}%"))
        
        # Для специального случая "брит а" -> "БРИТ А"
        parts = query.lower().strip().split()
        if len(parts) == 2 and len(parts[1]) == 1:
            # Основные варианты поиска для формата "слово + буква"
            combined = parts[0] + parts[1]
            with_dash = f"{parts[0]}-{parts[1]}"
            with_space = f"{parts[0]} {parts[1]}"
            
            or_conditions.append(Product.name.ilike(f"%{combined}%"))
            or_conditions.append(Product.name.ilike(f"%{with_dash}%"))
            or_conditions.append(Product.name.ilike(f"%{with_space}%"))
            
            # Добавляем варианты с разным регистром для специальных случаев
            or_conditions.append(Product.name.ilike(f"%{combined.upper()}%"))
            or_conditions.append(Product.name.ilike(f"%{with_dash.upper()}%"))
            or_conditions.append(Product.name.ilike(f"%{with_space.upper()}%"))
            
            # Поиск только по первой части (например, "брит" для "брит а")
            or_conditions.append(Product.name.ilike(f"%{parts[0]}%"))
        
        # Также добавляем специальный поиск для отдельных букв (например, "а" в "БРИТ А")
        # Эта часть поможет находить продукты, где буквы написаны через дефис
        if len(parts) >= 2:
            for part in parts:
                if len(part) == 1:
                    letter_pattern = f"%{part}%"
                    or_conditions.append(Product.name.ilike(letter_pattern))
        
        # Выполняем запрос с объединением всех условий через OR
        result = await self.session.execute(
            select(Product).where(
                or_(*or_conditions),
                Product.is_deleted == False
            )
        )
        
        return list(result.scalars().all())

    async def get_by_category(self, category_id: int) -> List[Product]:
        """
        Get products by id
        """
        result = await self.session.execute(
            select(Product).where(
                Product.category_id == category_id,
                Product.is_deleted == False
            )
        )
        return list(result.scalars().all())

    #TODO: make error handling
    async def soft_delete_product(self, product_id: int) -> None:
        """
        soft deleting product - just changing flag is_deleted to True
        """
        await self.session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(is_deleted = True)
        )
        await self.session.execute(
            update(ProductSphere)
            .where(ProductSphere.product_id == product_id)
            .values(is_deleted = True)
        )
        await self.session.commit()
        print("product was deleted")


class ProductFileRepository:
    """
    Репозиторий для работы с файлами продуктов
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_main_image(self, product_id: int) -> Optional[str]:
        """
        Obvious, isn't it? getting main image for building a messgae
        """
        result = await self.session.execute(
            select(ProductFile.file_id)
            .where(ProductFile.product_id == product_id, ProductFile.kind == "image", ProductFile.is_deleted == False)
            .order_by(ProductFile.ordering) # lowerst first = main image
            .limit(1)
        )
        return result.scalar()

    async def get_documents(self, product_id: int):
        """
        returns the list of files related to product_id
        """
        result = await self.session.execute(
            select(ProductFile)
            .where(ProductFile.product_id == product_id, ProductFile.kind == "doc", ProductFile.is_deleted == False)
            .order_by(ProductFile.ordering)
        )
        return result.scalars().all()

    async def add_file(self, product_id: int, file_id: str, kind: str, ordering: int = 0) -> ProductFile:
        """Добавление файла к продукту"""
        product_file = ProductFile(
            product_id=product_id,
            file_id=file_id,
            kind=kind,
            ordering=ordering
        )
        self.session.add(product_file)
        await self.session.commit()
        await self.session.refresh(product_file)
        return product_file


async def insert_image(session, product_id: int, file_id: int, is_main: bool):
    """
    inserting description images or main image
    """
    if is_main:
        # downshifting all images 
        await session.execute(
            ProductFile.__table__.update()
            .where(ProductFile.product_id == product_id, ProductFile.kind == "image", ProductFile.is_deleted == False)
            .values(ordering = ProductFile.ordering + 1)
        )
        ordering = 0
        pf = ProductFile(product_id = product_id, file_id = file_id, kind = "image", ordering = ordering)
        session.add(pf)
        await session.commit()
    else:
        # finding next number for other cases images
        ordering = (await session.scalar(
            select(func.coalesce(func.max(ProductFile.ordering), -1))
            .where(ProductFile.product_id == product_id, ProductFile.kind == "image")
        )) + 1
        
        pf = ProductFile(product_id = product_id, file_id = file_id, kind = "image", ordering = ordering)
        session.add(pf)
        await session.commit()


async def insert_doc(session, product_id: int, file_id: int):
    """
    inserting document to product
    """
    max_ord = await session.scalar(
        select(func.coalesce(func.max(ProductFile.ordering), -1))
        .where(ProductFile.product_id == product_id, ProductFile.kind == "doc"))
    
    pf = ProductFile(product_id = product_id, file_id = file_id, kind = "doc", ordering = max_ord + 1)
    
    session.add(pf)
    await session.commit()
