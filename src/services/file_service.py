import os
import requests
import pdfplumber
import logging

from aiogram import Bot
from aiogram.types import InputFile
from src.config.settings import BOT_TOKEN, DOWNLOAD_FOLDER
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.product_file_repositories import ProductFileRepository
from src.database.models import ProductFile

from src.services.auto_chunking_service import AutoChunkingService

logger = logging.getLogger(__name__)

class FileService:
    """
    Сервис менеджмента файлов с автоматическим чанкингом
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.file_repo = ProductFileRepository(session)
        # Используем только автоматический сервис чанкинга
        self.auto_chunking_service = AutoChunkingService()
    

    async def process_pdf_and_create_embeddings(self, product_id: int, product_name: str, product_dir: str):
        """
        Обработка всех PDF файлов в директории, извлечение текста и создание эмбеддингов для продуктов
        """
        # Проверяем, что директория существует
        if not os.path.exists(product_dir):
            logger.error(f"Директория не существует: {product_dir}")
            return
            
        # Пока что только pdf TODO: добавить xlxs
        pdf_files = [f for f in os.listdir(product_dir) if f.endswith(".pdf")]
        
        if not pdf_files:
            logger.info(f"В директории {product_dir} не найдено PDF-файлов")
            return

        # Инициализируем сервис автоматического чанкинга один раз для всех файлов
        await self.auto_chunking_service.initialize()
            
        for file_name in pdf_files:
            file_path = os.path.join(product_dir, file_name)
            logger.info(f"Обрабатываем файл: {file_path}")

            try:
                # Используем улучшенный метод извлечения текста без лимитов
                from src.services.rag.pdf_extractor import extract_text_from_pdf
                full_text = await extract_text_from_pdf(file_path, max_pages=None, max_length=None)
                
                logger.info(f"Текст из PDF ({file_name}, длина: {len(full_text)} символов): {full_text[:200]}...")
                
                # Обрабатываем файл через автоматический чанкинг
                if full_text and len(full_text) > 100:  # Минимальная длина текста
                    result = await self.auto_chunking_service.process_uploaded_file(
                        product_id=product_id,
                        product_name=product_name, 
                        file_path=file_path,
                        file_title=file_name
                    )
                    logger.info(f"Автоматический чанкинг для файла {file_name} завершен: {result}")
                else:
                    logger.warning(f"Пропускаем обработку {file_name}: текст слишком короткий или отсутствует")
            except Exception as e:
                logger.error(f"Ошибка при обработке PDF файла {file_path}: {e}")

    async def save_product_image(self, product_id: int, file_id: str, is_main: bool = False) -> ProductFile:
        """
        Сохранить фото продукта и скачать его локально
        """
        # Скачиваем файл
        try:
            local_path = await self.download_file_locally(file_id, product_id)
        except Exception as e:
            print(f"Ошибка при скачивании файла: {e}")
            local_path = None
            
        ordering = 0 if is_main else 1
        return await self.file_repo.add_file(
            product_id = product_id,
            file_id = file_id,
            kind = "image",
            ordering = ordering,
            local_path = local_path,
            is_main_image = is_main
        )

    async def save_product_document(self, product_id: int, file_id: str, title: Optional[str] = None) -> ProductFile:
        """
        Сохранить документацию для продукта и скачать его локально
        """
        # Скачиваем файл
        try:
            local_path = await self.download_file_locally(file_id, product_id)
        except Exception as e:
            print(f"Ошибка при скачивании файла: {e}")
            local_path = None
            
        saved_file = await self.file_repo.add_file(
            product_id = product_id,
            file_id = file_id,
            kind = "document",
            title = title,
            local_path = local_path
        )

        if local_path and local_path.endswith('.pdf'):
            product_name = title if title else f"Продукт {product_id}"
            await self.process_pdf_and_create_embeddings(product_id,product_name,os.path.dirname(local_path))
        
        return saved_file
    
    async def get_product_files(self, product_id: int, file_type: Optional[str] = None) -> List[ProductFile]:
        """
        получение файлов продуктов
        """
        from sqlalchemy import select
        
        query = select(ProductFile).where(
            ProductFile.product_id == product_id,
            ProductFile.is_deleted == False
        )
        
        if file_type:
            query = query.where(ProductFile.kind == file_type)
        
        result = await self.session.execute(query.order_by(ProductFile.ordering))
        return list(result.scalars().all())


    async def download_and_store_file(self, file_id: str, product_id: int, is_document: bool, title: Optional[str] = None, 
                                   file_kind: Optional[str] = None, file_size: Optional[int] = None, 
                                   mime_type: Optional[str] = None, original_filename: Optional[str] = None) -> ProductFile:
        """
        Скачивает файл с Telegram, сохраняет его локально, регистрирует в БД 
        и автоматически создает эмбеддинги с чанкингом для PDF файлов
        """
        # Скачиваем файл
        try:
            local_path = await self.download_file_locally(file_id, product_id)
        except Exception as e:
            print(f"Ошибка при скачивании файла: {e}")
            local_path = None

        # Если file_kind передан напрямую, используем его
        kind = file_kind if file_kind else ("document" if is_document else "image")

        # Сохраняем файл в БД
        new_file = await self.file_repo.add_file(
            product_id=product_id,
            file_id=file_id,
            kind=kind,
            title=title,
            local_path=local_path,
            file_size=file_size,
            mime_type=mime_type,
            original_filename=original_filename
        )
        
        # Автоматическое создание эмбеддингов с чанкингом для PDF файлов
        if local_path and mime_type == 'application/pdf':
            try:
                # Получаем название продукта
                from src.database.models import Product
                from sqlalchemy import select
                
                query = select(Product.name).where(Product.id == product_id)
                result = await self.session.execute(query)
                product_name = result.scalar_one_or_none()
                
                if product_name:
                    # Формируем абсолютный путь к файлу
                    if os.path.isabs(local_path):
                        absolute_path = local_path
                    else:
                        absolute_path = os.path.join(DOWNLOAD_FOLDER, local_path)
                    
                    logger.info(f"[FileService] Запускаем автоматический чанкинг для файла {absolute_path}")
                    
                    # Создаем эмбеддинги с чанкингом
                    chunking_result = await self.auto_chunking_service.process_uploaded_file(
                        product_id=product_id,
                        product_name=product_name,
                        file_path=absolute_path,
                        file_title=title
                    )
                    
                    if chunking_result["success"]:
                        logger.info(f"[FileService] Автоматический чанкинг успешен: создано {chunking_result['chunks_created']} эмбеддингов")
                    else:
                        logger.warning(f"[FileService] Ошибка автоматического чанкинга: {chunking_result.get('error', 'Неизвестная ошибка')}")
                else:
                    logger.warning(f"[FileService] Продукт {product_id} не найден для автоматического чанкинга")
                    
            except Exception as e:
                logger.error(f"[FileService] Ошибка при автоматическом чанкинге файла {local_path}: {e}")
        
        return new_file

    async def download_file_locally(self, file_id: str, product_id: int) -> str:
        """
        Скачивает файл с Telegram и сохраняет его локально
        """
        # Проверяем, есть ли уже файл в базе с этим file_id
        from sqlalchemy import select
        
        query = select(ProductFile).where(
            (ProductFile.file_id == file_id) &
            (ProductFile.product_id == product_id)
        )
        
        result = await self.session.execute(query)
        # Используем first() вместо scalar_one_or_none() чтобы избежать ошибки
        # при наличии нескольких записей с одинаковым file_id и product_id
        existing_file = result.scalars().first()
        
        # Если файл уже есть и путь указан и файл существует - просто возвращаем путь
        if existing_file:
            rel_path = getattr(existing_file, 'local_path', None)
            if rel_path and isinstance(rel_path, str):
                # Конвертируем относительный путь в абсолютный для проверки существования файла
                abs_path = os.path.join(DOWNLOAD_FOLDER, rel_path)
                if os.path.exists(abs_path):
                    return rel_path
        
        # Получаем тип файла из существующей записи
        mime_type = None
        kind = None
        if existing_file:
            if hasattr(existing_file, 'mime_type'):
                mime_type = getattr(existing_file, 'mime_type', None)
            if hasattr(existing_file, 'kind'):
                kind = getattr(existing_file, 'kind', None)
        
        # Список MIME типов файлов, которые мы хотим скачивать - только документы
        allowed_mime_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'application/rtf',
            'application/vnd.oasis.opendocument.text',
            'application/vnd.oasis.opendocument.spreadsheet',
            'application/octet-stream',  # для бинарных файлов, которые могут быть документами
            'text/html',
            'text/xml',
            'application/xml',
            'application/json',
            'application/vnd.oasis.opendocument.presentation'
        ]
        
        allowed_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.ppt', '.pptx',
            '.txt', '.rtf', '.odt', '.ods', '.odp', '.xml', '.json', '.md', '.html', '.htm'
            # Убраны видео, архивы и изображения, как и запрошено
        ]
        
        # Проверяем тип файла, если он известен - разрешаем только документы
        if kind is not None and isinstance(kind, str):
            # Разрешаем только документы и связанные с ними типы
            allowed_kinds = ['document', 'pdf', 'word', 'excel', 'presentation', 'other']
            if kind in allowed_kinds:
                pass  # эти типы скачиваем
            # Для изображений - скачиваем только главные
            elif kind == 'image' and existing_file and getattr(existing_file, 'is_main_image', False):
                pass  # главные изображения скачиваем
            # Остальные типы фильтруем
            else:
                raise ValueError(f"Тип файла {kind} не входит в список разрешенных для скачивания.")
            
        # Если mime_type известен и не входит в список разрешенных - пропускаем,
        # но только если kind не указан или не является документом
        if mime_type is not None and isinstance(mime_type, str):
            if kind not in ['document', 'pdf', 'word', 'excel', 'presentation'] and not any(mime_type.startswith(allowed_type) for allowed_type in allowed_mime_types):
                raise ValueError(f"MIME тип {mime_type} не входит в список разрешенных для скачивания.")
            
        if not BOT_TOKEN:
            raise ValueError("Bot token is not set")

        # Используем контекстный менеджер для правильного закрытия сессии
        bot = Bot(token=BOT_TOKEN)
        try:
            file_info = await bot.get_file(file_id)
            if not file_info or not file_info.file_path:
                raise ValueError(f"Не удалось получить информацию о файле с ID: {file_id}")
                
            file_url = file_info.file_path

            # Получаем оригинальное имя файла
            original_filename = file_url.split('/')[-1]
            
            # Определяем расширение файла
            if '.' in original_filename:
                file_extension = original_filename.split('.')[-1].lower()
                extension_with_dot = f".{file_extension}"
            else:
                # Если расширение не определено в имени файла, определяем по MIME-типу
                extension_with_dot = None
                if mime_type:
                    # Маппинг MIME-типов на расширения
                    mime_to_ext = {
                        'application/pdf': '.pdf',
                        'application/msword': '.doc',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                        'application/vnd.ms-excel': '.xls',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
                        'text/csv': '.csv',
                        'application/vnd.ms-powerpoint': '.ppt',
                        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
                        'text/plain': '.txt',
                        'application/rtf': '.rtf',
                        'application/vnd.oasis.opendocument.text': '.odt',
                        'application/vnd.oasis.opendocument.spreadsheet': '.ods',
                        'application/json': '.json',
                        'text/html': '.html',
                        'text/xml': '.xml',
                        'application/xml': '.xml'
                    }
                    
                    # Пытаемся определить расширение по MIME-типу
                    for mime_prefix, ext in mime_to_ext.items():
                        if mime_type.startswith(mime_prefix):
                            extension_with_dot = ext
                            break
                    
                    # Если не определили по MIME, но тип известен - используем тип
                    if not extension_with_dot and kind:
                        kind_to_ext = {
                            'pdf': '.pdf',
                            'word': '.doc',
                            'excel': '.xlsx',
                            'presentation': '.pptx',
                            'document': '.pdf'  # По умолчанию для документов
                        }
                        extension_with_dot = kind_to_ext.get(kind, '.pdf')
                
                # Если не смогли определить расширение - используем .pdf по умолчанию для документов
                if not extension_with_dot:
                    extension_with_dot = '.pdf'
                
                # Обновляем имя файла с новым расширением
                original_filename = f"{original_filename}{extension_with_dot}"
            
            # Проверяем расширение файла
            if extension_with_dot not in allowed_extensions:
                raise ValueError(f"Расширение файла {extension_with_dot} не входит в список разрешенных для скачивания.")

            # Папка для хранения файлов - создаем относительный путь
            rel_product_folder = f"product_{product_id}"
            product_folder = os.path.join(DOWNLOAD_FOLDER, rel_product_folder)
            os.makedirs(product_folder, exist_ok=True)

            # Создаем относительный путь для сохранения файла
            rel_file_path = os.path.join(rel_product_folder, original_filename)
            file_path = os.path.join(DOWNLOAD_FOLDER, rel_file_path)

            # Если файл с таким именем уже существует, добавляем суффикс
            counter = 1
            while os.path.exists(file_path):
                rel_file_path = os.path.join(rel_product_folder, f"{original_filename.split('.')[0]}_{counter}.{file_extension}")
                file_path = os.path.join(DOWNLOAD_FOLDER, rel_file_path)

            # Скачиваем и сохраняем файл
            file_data = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_url}")
            if not file_data.ok:
                raise ValueError(f"Ошибка при скачивании файла: {file_data.status_code}, {file_data.text}")
            
            with open(file_path, "wb") as f:
                f.write(file_data.content)
                
            # Возвращаем относительный путь вместо абсолютного
            return rel_file_path
        finally:
            # Закрываем сессию бота
            await bot.session.close()
    
    async def first_files_download(self) -> dict:
        """
        Скачивает все файлы, которые есть в базе, но не имеют локального пути.
        Возвращает статистику по скачанным файлам.
        """
        from sqlalchemy import select
        import asyncio
        
        # Получаем все записи файлов, у которых нет локального пути или путь None
        query = select(ProductFile).where(
            (ProductFile.local_path.is_(None)) &
            (ProductFile.is_deleted == False)
        )
        
        result = await self.session.execute(query)
        files_to_download = list(result.scalars().all())
        
        stats = {
            "total": len(files_to_download),
            "success": 0,
            "failed": 0,
            "files": []
        }
        
        for file in files_to_download:
            try:
                # Получаем значения атрибутов объекта модели
                file_id_str = getattr(file, 'file_id', None)
                product_id_int = getattr(file, 'product_id', None)
                
                if file_id_str and product_id_int:
                    try:
                        local_path = await self.download_file_locally(str(file_id_str), int(product_id_int))
                        
                        # Обновляем запись в базе данных
                        setattr(file, 'local_path', local_path)
                        await self.session.commit()
                        
                        stats["success"] += 1
                        stats["files"].append({
                            "id": file.id,
                            "product_id": product_id_int,
                            "kind": getattr(file, 'kind', None),
                            "status": "success",
                            "path": local_path
                        })
                        
                        print(f"Скачан файл {file.id} для продукта {product_id_int}")
                    except ValueError as e:
                        # Для ошибок фильтрации типов файлов (не скачиваем видео и т.д.)
                        stats["failed"] += 1
                        stats["files"].append({
                            "id": file.id,
                            "product_id": product_id_int,
                            "kind": getattr(file, 'kind', None),
                            "status": "filtered",
                            "error": str(e)
                        })
                        
                        print(f"Файл {file.id} пропущен: {e}")
                    except Exception as e:
                        stats["failed"] += 1
                        stats["files"].append({
                            "id": file.id,
                            "product_id": product_id_int,
                            "kind": getattr(file, 'kind', None),
                            "status": "failed",
                            "error": str(e)
                        })
                        
                        print(f"Ошибка при скачивании файла {file.id}: {e}")
                    
                    # Небольшая пауза между скачиваниями
                    await asyncio.sleep(0.1)
            except Exception as e:
                stats["failed"] += 1
                stats["files"].append({
                    "id": getattr(file, 'id', 'Unknown'),
                    "product_id": getattr(file, 'product_id', 'Unknown'),
                    "kind": getattr(file, 'kind', None),
                    "status": "failed",
                    "error": f"Ошибка обработки файла: {str(e)}"
                })
        
        return stats
    
    async def is_file_downloaded(self, file_id: int) -> bool:
        """
        Проверяет, скачан ли файл локально
        """
        from sqlalchemy import select
        
        query = select(ProductFile).where(
            ProductFile.id == file_id
        )
        
        result = await self.session.execute(query)
        file = result.scalar_one_or_none()
        
        if not file:
            return False
        
        # Проверяем, что local_path не None и что файл существует
        rel_path = getattr(file, 'local_path', None)
        if rel_path and isinstance(rel_path, str):
            # Конвертируем относительный путь в абсолютный для проверки существования файла
            abs_path = os.path.join(DOWNLOAD_FOLDER, rel_path)
            if os.path.exists(abs_path):
                return True
            
        return False
        
    async def get_files_stats(self) -> dict:
        """
        Возвращает статистику по файлам в базе данных: сколько скачано, сколько не скачано и т.д.
        """
        from sqlalchemy import select, func
        
        # Общее количество файлов
        query = select(func.count()).select_from(ProductFile).where(
            ProductFile.is_deleted == False
        )
        result = await self.session.execute(query)
        total_files = result.scalar() or 0
        
        # Количество скачанных файлов
        query = select(func.count()).select_from(ProductFile).where(
            (ProductFile.local_path.is_not(None)) &
            (ProductFile.is_deleted == False)
        )
        result = await self.session.execute(query)
        downloaded_files = result.scalar() or 0
        
        # Количество файлов по типам
        query = select(ProductFile.kind, func.count()).select_from(ProductFile).where(
            ProductFile.is_deleted == False
        ).group_by(ProductFile.kind)
        result = await self.session.execute(query)
        files_by_type = {kind: count for kind, count in result.all()}
        
        return {
            "total_files": total_files,
            "downloaded_files": downloaded_files,
            "not_downloaded_files": total_files - downloaded_files,
            "files_by_type": files_by_type
        }