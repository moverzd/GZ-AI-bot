from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.handlers.states import AddFiles
from src.database.models import Product, ProductFile
from src.services.product_service import ProductService
from src.keyboards.admin import get_admin_main_menu_keyboard
from src.core.utils import esc

router = Router()

# Определяем типы файлов и их категории
DOCUMENT_TYPES = {
    'application/pdf': 'pdf',
    'application/msword': 'word', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
    'application/vnd.ms-excel': 'excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
    'application/vnd.ms-powerpoint': 'presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'presentation',
    'application/zip': 'archive',
    'application/x-rar-compressed': 'archive',
    'application/x-7z-compressed': 'archive',
}

MEDIA_TYPES = {
    'image/jpeg': 'image',
    'image/png': 'image',
    'image/gif': 'image',
    'image/webp': 'image',
    'video/mp4': 'video',
    'video/avi': 'video',
    'video/mov': 'video',
    'video/wmv': 'video',
    'video/webm': 'video',
}

def get_file_kind(mime_type: str) -> str:
    """Определяет тип файла по MIME типу"""
    if mime_type in DOCUMENT_TYPES:
        return DOCUMENT_TYPES[mime_type]
    elif mime_type in MEDIA_TYPES:
        return MEDIA_TYPES[mime_type]
    else:
        return 'other'

@router.callback_query(lambda c: c.data == 'admin:add_files')
async def admin_add_files_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Добавить файлы' из админского меню"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(AddFiles.waiting_product_id)
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "<b>Добавление файлов к продукту</b>\n\n"
            "Введите ID продукта, к которому хотите добавить файлы:\n\n"
            "ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.",
            parse_mode="HTML"
        )
    await callback.answer()

@router.message(AddFiles.waiting_product_id)
async def process_product_id_for_files(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода ID продукта для добавления файлов"""
    if not message.text:
        await message.answer("❌ Сообщение не содержит текста. Попробуйте ещё раз.")
        return
        
    try:
        product_id = int(message.text.strip())
        
        # Проверяем существование продукта
        product_service = ProductService(session)
        product = await product_service.get_product_by_id(product_id)
        
        if not product:
            await message.answer(
                "❌ Продукт с таким ID не найден.\n\n"
                "Попробуйте ещё раз или введите /admin для возврата в меню."
            )
            return
        
        # Сохраняем ID продукта и переходим к ожиданию файла
        await state.update_data(product_id=product_id, product_name=product['name'])
        await state.set_state(AddFiles.waiting_file)
        
        await message.answer(
            f"<b>Продукт найден:</b> {esc(product['name'])}\n\n"
            "Теперь отправьте файл, который хотите добавить к этому продукту.\n\n"
            "<b>Поддерживаемые форматы:</b>\n"
            "<b>Документы:</b> PDF, Word, Excel, PowerPoint, архивы\n"
            "<b>Медиа:</b> изображения (JPG, PNG, GIF, WebP), видео (MP4, AVI, MOV, WMV, WebM)\n\n"
            "Или введите /admin для возврата в меню.",
            parse_mode="HTML"
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID продукта. Введите числовое значение.\n\n"
            "Или введите /admin для возврата в меню."
        )

@router.message(AddFiles.waiting_file, F.document)
async def process_document_file(message: types.Message, state: FSMContext):
    """Обработка загруженного документа"""
    document = message.document
    if not document:
        return
    
    file_size_mb = (document.file_size or 0) / 1024 / 1024
    
    # Сохраняем информацию о файле
    await state.update_data(
        file_id=document.file_id,
        file_size=document.file_size,
        mime_type=document.mime_type,
        original_filename=document.file_name,
        file_type='document'
    )
    
    await state.set_state(AddFiles.waiting_title)
    
    await message.answer(
        f"<b>Документ получен:</b> {esc(document.file_name or 'Без названия')}\n"
        f"<b>Размер:</b> {file_size_mb:.2f} МБ\n\n"
        "Теперь введите название для этого файла, которое будет отображаться пользователям:",
        parse_mode="HTML"
    )

@router.message(AddFiles.waiting_file, F.photo)
async def process_photo_file(message: types.Message, state: FSMContext):
    """Обработка загруженного изображения"""
    if not message.photo:
        return
        
    photo = message.photo[-1]  # Берём самое большое разрешение
    file_size_mb = (photo.file_size or 0) / 1024 / 1024
    
    # Сохраняем информацию о файле
    await state.update_data(
        file_id=photo.file_id,
        file_size=photo.file_size,
        mime_type='image/jpeg',  # Telegram всегда конвертирует в JPEG
        original_filename=None,
        file_type='media'
    )
    
    await state.set_state(AddFiles.waiting_title)
    
    await message.answer(
        f"<b>Изображение получено</b>\n"
        f"<b>Размер:</b> {file_size_mb:.2f} МБ\n\n"
        "Теперь введите название для этого изображения, которое будет отображаться пользователям:",
        parse_mode="HTML"
    )

@router.message(AddFiles.waiting_file, F.video)
async def process_video_file(message: types.Message, state: FSMContext):
    """Обработка загруженного видео"""
    video = message.video
    if not video:
        return
    
    file_size_mb = (video.file_size or 0) / 1024 / 1024
    
    # Сохраняем информацию о файле
    await state.update_data(
        file_id=video.file_id,
        file_size=video.file_size,
        mime_type=video.mime_type,
        original_filename=video.file_name,
        file_type='media'
    )
    
    await state.set_state(AddFiles.waiting_title)
    
    await message.answer(
        f"<b>Видео получено:</b> {esc(video.file_name or 'Без названия')}\n"
        f"<b>Размер:</b> {file_size_mb:.2f} МБ\n"
        f" <b>Длительность:</b> {video.duration or 0} сек\n\n"
        "Теперь введите название для этого видео, которое будет отображаться пользователям:",
        parse_mode="HTML"
    )

@router.message(AddFiles.waiting_file)
async def process_unsupported_file(message: types.Message, state: FSMContext):
    """Обработка неподдерживаемого типа файла"""
    await message.answer(
        "❌ <b>Неподдерживаемый тип файла</b>\n\n"
        "<b>Поддерживаемые форматы:</b>\n"
        "<b>Документы:</b> PDF, Word, Excel, PowerPoint, архивы\n"
        "<b>Медиа:</b> изображения (JPG, PNG, GIF, WebP), видео (MP4, AVI, MOV, WMV, WebM)\n\n"
        "Попробуйте загрузить файл другого формата или введите /admin для возврата в меню.",
        parse_mode="HTML"
    )

@router.message(AddFiles.waiting_title)
async def process_file_title(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка названия файла и сохранение в БД"""
    if not message.text:
        await message.answer("❌ Сообщение не содержит текста. Попробуйте ещё раз:")
        return
        
    title = message.text.strip()
    
    if not title:
        await message.answer(
            "❌ Название не может быть пустым. Попробуйте ещё раз:"
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    
    try:
        # Определяем тип файла по MIME типу
        file_kind = get_file_kind(data.get('mime_type', ''))
        
        # Получаем ID пользователя
        user_id = message.from_user.id if message.from_user else None
        
        # Создаём запись в БД
        new_file = ProductFile(
            product_id=data['product_id'],
            file_id=data['file_id'],
            kind=file_kind,
            title=title,
            file_size=data.get('file_size'),
            mime_type=data.get('mime_type'),
            original_filename=data.get('original_filename'),
            uploaded_by=user_id,
            uploaded_at=datetime.now(),
            ordering=1  # Не главное изображение
        )
        
        session.add(new_file)
        await session.commit()
        
        
        await message.answer(
            f"<b>Файл успешно добавлен!</b>\n\n"
            f"<b>Название:</b> {esc(title)}\n"
            f"<b>Продукт:</b> {esc(data['product_name'])}\n"
            f"<b>Тип:</b> {file_kind}\n\n"
            "Хотите добавить ещё файлы к этому продукту?",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(
                    text="Добавить ещё файл", 
                    callback_data=f"add_more_files:{data['product_id']}"
                )],
                [types.InlineKeyboardButton(
                    text="Админ меню", 
                    callback_data="admin:menu"
                )]
            ])
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при сохранении файла: {str(e)}\n\n"
            "Попробуйте ещё раз",
            reply_markup=get_admin_main_menu_keyboard()
        )
        await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith('add_more_files:'))
async def add_more_files_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Добавление ещё одного файла к тому же продукту"""
    if not callback.data:
        return
        
    product_id = int(callback.data.split(':')[1])
    
    # Получаем информацию о продукте
    product_service = ProductService(session)
    product = await product_service.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    await state.update_data(product_id=product_id, product_name=product['name'])
    await state.set_state(AddFiles.waiting_file)
    
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            f"<b>Добавление файла к продукту:</b> {esc(product['name'])}\n\n"
            "Отправьте файл, который хотите добавить к этому продукту.\n\n"
            "<b>Поддерживаемые форматы:</b>\n"
            "<b>Документы:</b> PDF, Word, Excel, PowerPoint, архивы\n"
            "<b>Медиа:</b> изображения (JPG, PNG, GIF, WebP), видео (MP4, AVI, MOV, WMV, WebM)",
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:menu')
async def return_to_admin_menu(callback: types.CallbackQuery):
    """Возврат в админское меню"""
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "<b>Панель Администратора</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=get_admin_main_menu_keyboard()
        )
    await callback.answer()
