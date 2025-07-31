from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.handlers.states import DeleteFiles
from src.database.models import Product, ProductFile
from src.services.product_service import ProductService
from src.keyboards.admin import get_admin_main_menu_keyboard
from src.core.utils import esc
from src.handlers.search import embedding_service

router = Router()

def get_file_icon(file_kind: str) -> str:
    """Возвращает иконку для типа файла"""
    if file_kind == 'image':
        return "🖼️"
    elif file_kind == 'video':
        return "🎬"
    elif file_kind in ['pdf', 'word', 'excel', 'presentation']:
        return "📄"
    elif file_kind == 'archive':
        return "📦"
    else:
        return "📎"

def format_file_size(file_size) -> str:
    """Форматирует размер файла"""
    if file_size and file_size > 0:
        size_mb = file_size / 1024 / 1024
        return f" ({size_mb:.1f} МБ)"
    return ""

@router.callback_query(lambda c: c.data == 'admin:delete_files')
async def admin_delete_files_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Удалить файлы продукта' из админского меню"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(DeleteFiles.waiting_product_id)
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "<b>🗑📎 Удаление файлов продукта</b>\n\n"
                "Введите ID продукта, файлы которого хотите удалить:\n\n"
                "ℹ️ ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.\n"
                "ℹ️ Для выхода в панель администратора введите /admin",
                parse_mode="HTML"
            )
        except Exception:
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                "<b>🗑📎 Удаление файлов продукта</b>\n\n"
                "Введите ID продукта, файлы которого хотите удалить:\n\n"
                "ℹ️ ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.\n"
                "ℹ️ Для выхода в панель администратора введите /admin",
                parse_mode="HTML"
            )
            return
    await callback.answer()

@router.message(DeleteFiles.waiting_product_id)
async def process_product_id_for_delete_files(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода ID продукта для удаления файлов"""
    if not message.text:
        await message.answer("🔴 Сообщение не содержит текста. Попробуйте ещё раз.")
        return
        
    try:
        product_id = int(message.text.strip())
        
        product_service = ProductService(session, embedding_service)
        product = await product_service.get_product_by_id(product_id)
        
        if not product:
            await message.answer(
                "🔴 Продукт с таким ID не найден.\n\n"
                "Попробуйте ещё раз или введите /admin для возврата в меню."
            )
            return
        
        result = await session.execute(
            select(ProductFile).where(
                ProductFile.product_id == product_id,
                ProductFile.title.is_not(None) 
            ).order_by(ProductFile.uploaded_at.desc())
        )
        files = list(result.scalars().all())
        
        if not files:
            await message.answer(
                f"📂 <b>Продукт:</b> {esc(product['name'])}\n\n"
                "🔴 У этого продукта нет файлов для удаления.",
                parse_mode="HTML",
                reply_markup=get_admin_main_menu_keyboard()
            )
            await state.clear()
            return
        
        await show_files_list(message, session, product_id, files, product['name'])
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "🔴 Неверный формат ID продукта. Введите числовое значение.\n\n"
            "Или введите /admin для возврата в меню."
        )

async def show_files_list(message_or_callback, session: AsyncSession, product_id: int, files: list, product_name: str, is_callback: bool = False):
    """Показать список файлов для удаления"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    
    files_text = f"🗑️ <b>Удаление файлов продукта:</b> {esc(product_name)}\n\n" \
                f"<b>Всего файлов:</b> {len(files)}\n\n" \
                "<b>Нажмите на кнопку с названием файла, который хотите удалить:</b>\n\n"
    
    for i, file in enumerate(files, 1):
        file_kind = file.kind
        file_size = file.file_size if hasattr(file, 'file_size') else None
        file_title = file.title if file.title else 'Без названия'
        
        icon = get_file_icon(file_kind)
        
        size_text = format_file_size(file_size)
        
        files_text += f"{i}. {icon} <b>{esc(file_title)}</b>{size_text}\n"
        files_text += f"   <i>Тип: {file_kind}</i>\n\n"
        
        button = types.InlineKeyboardButton(
            text=f"🗑️ {i}. {file_title}",
            callback_data=f"delete_file:{file.id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Вернуться в админ меню",
            callback_data="admin:menu"
        )
    ])
    
    if is_callback and hasattr(message_or_callback, 'message'):
        if message_or_callback.message and isinstance(message_or_callback.message, types.Message):
            try:
                await message_or_callback.message.edit_text(
                    files_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception:
                await message_or_callback.answer()
                await message_or_callback.message.delete()
                await message_or_callback.message.answer(
                    files_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return
    else:
        await message_or_callback.answer(
            files_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

@router.callback_query(lambda c: c.data and c.data.startswith('delete_file:'))
async def confirm_file_deletion(callback: types.CallbackQuery, session: AsyncSession):
    """Показать подтверждение удаления файла с информацией"""
    if not callback.data:
        return
    
    file_id = int(callback.data.split(':')[1])
    
    result = await session.execute(
        select(ProductFile).where(ProductFile.id == file_id)
    )
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        await callback.answer("Файл не найден", show_alert=True)
        return
    
    product_service = ProductService(session, embedding_service)
    product = await product_service.get_product_by_id(file_record.product_id)
    
    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    file_kind = str(file_record.kind)
    # лучше безопастно через getattr чем как метод?
    # TODO: узнать об этом :) 
    file_size = getattr(file_record, 'file_size', None)
    file_title = getattr(file_record, 'title', None) or 'Без названия'
    uploaded_at = getattr(file_record, 'uploaded_at', None)
    original_filename = getattr(file_record, 'original_filename', None)
    
    icon = get_file_icon(file_kind)
    
    size_text = "Неизвестно"
    if file_size is not None and file_size > 0:
        size_mb = file_size / 1024 / 1024
        size_text = f"{size_mb:.2f} МБ"
    
    upload_date = "Неизвестно"
    if uploaded_at is not None:
        upload_date = uploaded_at.strftime("%d.%m.%Y %H:%M")
    
    original_name = str(original_filename) if original_filename else "Не указано"
    
    confirmation_text = (
        f"⚠️ <b>Подтверждение удаления файла</b>\n\n"
        f"📦 <b>Продукт:</b> {esc(product['name'])}\n"
        f"{icon} <b>Название:</b> {esc(file_title)}\n"
        f"📝 <b>Тип файла:</b> {file_kind}\n"
        f"📊 <b>Размер:</b> {size_text}\n"
        f"📄 <b>Исходное имя:</b> {esc(original_name)}\n"
        f"📅 <b>Загружено:</b> {upload_date}\n\n"
        f"<b>Вы уверены, что хотите удалить этот файл?</b>\n"
        f"<i>Это действие нельзя отменить!</i>"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(
                text="🟢 Да, удалить",
                callback_data=f"confirm_delete_file:{file_id}"
            ),
            types.InlineKeyboardButton(
                text="🔴 Отмена",
                callback_data=f"cancel_delete_file:{file_record.product_id}"
            )
        ]
    ])
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                confirmation_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception:
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                confirmation_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith('confirm_delete_file:'))
async def delete_file_confirmed(callback: types.CallbackQuery, session: AsyncSession):
    """Физическое удаление файла из БД"""
    if not callback.data:
        return
    
    file_id = int(callback.data.split(':')[1])
    
    try:
        result = await session.execute(
            select(ProductFile).where(ProductFile.id == file_id)
        )
        file_record = result.scalars().first()
        
        if not file_record:
            await callback.answer("Файл не найден", show_alert=True)
            return
        
        file_title = getattr(file_record, 'title', None) or "Без названия"
        product_id = getattr(file_record, 'product_id')
        
        # Физически удаляем файл из БД
        await session.execute(
            delete(ProductFile).where(ProductFile.id == file_id)
        )
        await session.commit()
        
        product_service = ProductService(session, embedding_service)
        product = await product_service.get_product_by_id(product_id)
        
        success_text = (
            f"🟢 <b>Файл успешно удален!</b>\n\n"
            f"📦 <b>Продукт:</b> {esc(product['name'] if product else 'Неизвестен')}\n"
            f"📄 <b>Удаленный файл:</b> {esc(str(file_title))}\n\n"
            f"Выберите дальнейшее действие:"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🗑️ Удалить ещё файлы этого продукта",
                    callback_data=f"delete_more_files:{product_id}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🏠 Вернуться в админ меню",
                    callback_data="admin:menu"
                )
            ]
        ])
        
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    success_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception:
                await callback.answer("Файл удален!")
                await callback.message.delete()
                await callback.message.answer(
                    success_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                return
        await callback.answer("Файл удален!")
        
    except Exception as e:
        await callback.answer(f"Ошибка при удалении файла: {str(e)}", show_alert=True)

@router.callback_query(lambda c: c.data and c.data.startswith('cancel_delete_file:'))
async def cancel_file_deletion(callback: types.CallbackQuery, session: AsyncSession):
    """Отмена удаления файла - возврат к списку файлов"""
    if not callback.data:
        return
    
    product_id = int(callback.data.split(':')[1])
    
    product_service = ProductService(session, embedding_service)
    product = await product_service.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    result = await session.execute(
        select(ProductFile).where(
            ProductFile.product_id == product_id,
            ProductFile.title.is_not(None)  
        ).order_by(ProductFile.uploaded_at.desc())
    )
    files = list(result.scalars().all())
    
    if not files:
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    f"📂 <b>Продукт:</b> {esc(product['name'])}\n\n"
                    "🔴 У этого продукта нет файлов для удаления.",
                    parse_mode="HTML",
                    reply_markup=get_admin_main_menu_keyboard()
                )
            except Exception:
                await callback.answer()
                await callback.message.delete()
                await callback.message.answer(
                    f"📂 <b>Продукт:</b> {esc(product['name'])}\n\n"
                    "🔴 У этого продукта нет файлов для удаления.",
                    parse_mode="HTML",
                    reply_markup=get_admin_main_menu_keyboard()
                )
                return
        return
    
    await show_files_list(callback, session, product_id, files, product['name'], is_callback=True)
    await callback.answer("Удаление отменено")

@router.callback_query(lambda c: c.data and c.data.startswith('delete_more_files:'))
async def delete_more_files_same_product(callback: types.CallbackQuery, session: AsyncSession):
    """
    Продолжение удаление файла у продукта.
    """
    if not callback.data:
        return
    
    product_id = int(callback.data.split(':')[1])

    product_service = ProductService(session, embedding_service)
    product = await product_service.get_product_by_id(product_id)

    if not product:
        await callback.answer("Продукт не найден!", show_alert = True)
        return
    
    result = await session.execute(
        select(ProductFile).where(ProductFile.product_id == product_id,
                                  ProductFile.title.is_not(None)).order_by(ProductFile.uploaded_at.desc())
    )
    files = list(result.scalars().all())

    if not files:
            if callback.message and isinstance(callback.message, types.Message):
                try:
                    await callback.message.edit_text(
                        f"📂 <b>Продукт:</b> {esc(product['name'])}\n\n"
                        "🔴 У этого продукта больше нет файлов для удаления.",
                        parse_mode="HTML",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="🏠 Вернуться в админ меню",
                                callback_data="admin:menu"
                            )
                        ]])
                    )
                except Exception:
                    await callback.answer()
                    await callback.message.delete()
                    await callback.message.answer(
                     f"📂 <b>Продукт:</b> {esc(product['name'])}\n\n"
                    "🔴 У этого продукта больше нет файлов для удаления.",
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🏠 Вернуться в админ меню",
                            callback_data="admin:menu"
                        )
                    ]])
                )

                await callback.answer("Файлов больше нет")
                return   
    
    await show_files_list(callback, session, product_id, files, product['name'], is_callback= True)
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:menu')
async def return_to_admin_menu_from_delete(callback: types.CallbackQuery):
    """Возврат в админское меню из функции удаления"""
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "<b>Администрирование</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_admin_main_menu_keyboard()
            )
        except Exception:
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                "<b>Администрирование</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_admin_main_menu_keyboard()
            )
            return
    await callback.answer()
