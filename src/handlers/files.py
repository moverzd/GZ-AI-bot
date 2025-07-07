from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.filters.admin import AdminFilter
from src.services.file_service import FileService
from src.services.product_service import ProductService

router = Router()
router.message.filter(AdminFilter())  # Все обработчики доступны только админам

@router.message(Command('add_photo'))
async def cmd_add_photo(message: types.Message, command: CommandObject, session: AsyncSession):
    """
    Обработчик команды добавления фото к продукту
    Формат: /add_photo <id продукта>
    """
    # Проверяем, указан ли ID продукта
    if not command.args:
        await message.answer("❌ Не указан ID продукта. Используйте: /add_photo <id продукта>")
        return
    
    try:
        product_id = int(command.args)
    except ValueError:
        await message.answer("❌ Некорректный ID продукта. Используйте число.")
        return
    
    # Проверяем существование продукта
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await message.answer(f"❌ Продукт с ID {product_id} не найден или удален.")
        return
    
    # Запрашиваем фотографию
    await message.answer(f"📎 Отправьте фотографию для продукта {product_info['name']}:")

@router.message(lambda message: message.photo and hasattr(message, 'reply_to_message') and message.reply_to_message.text and '📎 Отправьте фотографию для продукта' in message.reply_to_message.text)
async def add_photo(message: types.Message, session: AsyncSession):
    """
    Обработчик получения фото для продукта
    """
    # Извлекаем ID продукта из текста сообщения
    reply_text = message.reply_to_message.text
    product_name = reply_text.replace('📎 Отправьте фотографию для продукта ', '').replace(':', '')
    
    # Ищем продукт по имени
    from sqlalchemy import select
    from src.database.models import Product
    
    result = await session.execute(
        select(Product).where(Product.name == product_name, Product.is_deleted == False)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        await message.answer("❌ Не удалось найти продукт.")
        return
    
    # Получаем ID файла
    photo = message.photo[-1]  # Берем наибольший размер фото
    file_id = photo.file_id
    
    # Сохраняем фото
    file_service = FileService(session)
    await file_service.save_product_image(product.id, file_id)
    
    await message.answer(f"✅ Фотография успешно добавлена к продукту {product.name}!")

@router.message(Command('add_doc'))
async def admin_add_doc(message: types.Message, command: CommandObject, session: AsyncSession):
    """
    Обработчик команды добавления документа к продукту
    Формат: /add_doc <id продукта>
    """
    # Проверяем, указан ли ID продукта
    if not command.args:
        await message.answer("❌ Не указан ID продукта. Используйте: /add_doc <id продукта>")
        return
    
    try:
        product_id = int(command.args)
    except ValueError:
        await message.answer("❌ Некорректный ID продукта. Используйте число.")
        return
    
    # Проверяем существование продукта
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await message.answer(f"❌ Продукт с ID {product_id} не найден или удален.")
        return
    
    # Запрашиваем документ
    await message.answer(f"📎 Отправьте документ для продукта {product_info['name']}:")

@router.message(lambda message: message.document and hasattr(message, 'reply_to_message') and message.reply_to_message.text and '📎 Отправьте документ для продукта' in message.reply_to_message.text)
async def add_document(message: types.Message, session: AsyncSession):
    """
    Обработчик получения документа для продукта
    """
    # Извлекаем ID продукта из текста сообщения
    reply_text = message.reply_to_message.text
    product_name = reply_text.replace('📎 Отправьте документ для продукта ', '').replace(':', '')
    
    # Ищем продукт по имени
    from sqlalchemy import select
    from src.database.models import Product
    
    result = await session.execute(
        select(Product).where(Product.name == product_name, Product.is_deleted == False)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        await message.answer("❌ Не удалось найти продукт.")
        return
    
    # Получаем информацию о документе
    document = message.document
    file_id = document.file_id
    file_name = document.file_name
    
    # Сохраняем документ
    file_service = FileService(session)
    await file_service.save_product_document(product.id, file_id, title=file_name)
    
    await message.answer(f"✅ Документ '{file_name}' успешно добавлен к продукту {product.name}!")