from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime

from src.handlers.states import UploadMainImage
from src.database.models import Product, ProductFile
from src.services.product_service import ProductService
from src.keyboards.admin import get_admin_main_menu_keyboard
from src.core.utils import esc

router = Router()

@router.callback_query(lambda c: c.data == 'admin:upload_main_image')
async def admin_upload_main_image_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Загрузить главное фото' из админского меню"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(UploadMainImage.waiting_product_id)
    if callback.message and isinstance(callback.message, types.Message):
        try:
            # Пытаемся отредактировать как текстовое сообщение
            await callback.message.edit_text(
                "<b>📷 Загрузка главного изображения</b>\n\n"
                "Введите ID продукта, для которого хотите загрузить главное изображение:\n\n"
                "ℹ️ ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.",
                parse_mode="HTML"
            )
        except Exception:
            # Если не получилось (например, сообщение с медиа), отправляем новое
            await callback.message.answer(
                "<b>📷 Загрузка главного изображения</b>\n\n"
                "Введите ID продукта, для которого хотите загрузить главное изображение:\n\n"
                "ℹ️ ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.",
                parse_mode="HTML"
            )
            # Пытаемся удалить предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception:
                pass  # Игнорируем ошибку удаления
    await callback.answer()

@router.message(UploadMainImage.waiting_product_id)
async def process_product_id_for_main_image(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода ID продукта для загрузки или удаления главного изображения"""
    if not message.text:
        await message.answer("🔴 Сообщение не содержит текста. Попробуйте ещё раз.")
        return
        
    try:
        product_id = int(message.text.strip())
        
        # Проверяем существование продукта
        product_service = ProductService(session)
        product = await product_service.get_product_by_id(product_id)
        
        if not product:
            await message.answer(
                "🔴 Продукт с таким ID не найден.\n\n"
                "Попробуйте ещё раз или введите /admin для возврата в меню."
            )
            return
        
        # Получаем данные из состояния
        state_data = await state.get_data()
        action = state_data.get('action', 'upload')  # По умолчанию - загрузка
        
        # Проверяем, есть ли уже главное изображение у этого продукта
        result = await session.execute(
            select(ProductFile).where(
                ProductFile.product_id == product_id,
                ProductFile.is_main_image == True,
                ProductFile.is_deleted == False
            )
        )
        current_main_image = result.scalars().first()
        
        if action == "delete":
            # Логика удаления главного изображения
            if not current_main_image:
                await message.answer(
                    f"📦 <b>Продукт:</b> {esc(product['name'])}\n\n"
                    "🔴 У этого продукта нет главного изображения для удаления.",
                    parse_mode="HTML",
                    reply_markup=get_admin_main_menu_keyboard()
                )
                await state.clear()
                return
            
            # Показываем текущее изображение и просим подтверждение
            confirmation_text = (
                f"⚠️ <b>Подтверждение удаления главного изображения</b>\n\n"
                f"📦 <b>Продукт:</b> {esc(product['name'])}\n\n"
                f"<b>Вы уверены, что хотите удалить главное изображение?</b>\n"
                f"<i>Это действие нельзя отменить!</i>"
            )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🟢 Да, удалить",
                        callback_data=f"confirm_delete_main_image:{product_id}"
                    ),
                    types.InlineKeyboardButton(
                        text="🔴 Отмена",
                        callback_data=f"cancel_delete_main_image:{product_id}"
                    )
                ]
            ])
            
            # Показываем изображение с подтверждением
            try:
                file_id = str(current_main_image.file_id)
                await message.answer_photo(
                    photo=file_id,
                    caption=confirmation_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception:
                # Если не удалось показать изображение, отправляем только текст
                await message.answer(
                    confirmation_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            
            await state.clear()
            return
        
        # Логика загрузки главного изображения (существующий код)
        # Сохраняем ID продукта в состоянии
        await state.update_data(product_id=product_id, product_name=product['name'])
        
        response_text = f"📦 <b>Продукт:</b> {esc(product['name'])}\n\n"
        
        if current_main_image:
            # Если есть главное изображение, предлагаем выбор
            response_text += (
                "🖼️ <b>У продукта уже есть главное изображение</b>\n\n"
                "Выберите действие:"
            )
 
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🖼️🔄 Заменить изображение",
                        callback_data=f"replace_main_image:{product_id}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="🖼️🗑️ Удалить изображение",
                        callback_data=f"confirm_delete_main_image:{product_id}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="⬅️ Назад в админ меню",
                        callback_data="menu:main"
                    )
                ]
            ])
            
            # Показываем текущее изображение с выбором
            try:
                file_id = str(current_main_image.file_id)
                await message.answer_photo(
                    photo=file_id,
                    caption=response_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception:
                # Если не удалось показать изображение, отправляем только текст
                await message.answer(
                    response_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            
            await state.clear()
            return
        else:
            response_text += "📷 <b>У продукта пока нет главного изображения</b>\n\n"
        
        response_text += (
            "<b>Пришлите изображение, которое станет главным для этого продукта</b>\n\n"
            "⚠️ <i>Принимаются только изображения (JPG, PNG, GIF и т.д.)</i>"
        )
        
        await message.answer(response_text, parse_mode="HTML")
        await state.set_state(UploadMainImage.waiting_image)
        
    except ValueError:
        await message.answer(
            "🔴 Неверный формат ID продукта. Введите числовое значение.\n\n"
            "Или введите /admin для возврата в меню."
        )

@router.message(UploadMainImage.waiting_image)
async def process_main_image_upload(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка загрузки главного изображения"""
    
    # Проверяем, что это изображение
    if not message.photo:
        await message.answer(
            "🔴 Пожалуйста, пришлите изображение.\n\n"
            "Поддерживаются форматы: JPG, PNG, GIF и другие изображения."
        )
        return
    
    try:
        # Получаем данные из состояния
        state_data = await state.get_data()
        product_id = state_data.get('product_id')
        product_name = state_data.get('product_name', 'Неизвестный продукт')
        
        if not product_id:
            await message.answer("🔴 Ошибка: не найден ID продукта. Начните заново с команды /admin.")
            await state.clear()
            return
        
        # Получаем наибольшее изображение из присланного
        photo = message.photo[-1]  # Берем изображение наибольшего размера
        
        # Сначала физически удаляем текущее главное изображение, если оно есть
        await session.execute(
            delete(ProductFile).where(
                ProductFile.product_id == product_id,
                ProductFile.is_main_image == True
            )
        )
        
        # Создаем новую запись для главного изображения
        # Используем timestamp для уникального ordering
        unique_ordering = int(datetime.now().timestamp())
        
        new_main_image = ProductFile(
            product_id=product_id,
            file_id=photo.file_id,
            kind='image',
            ordering=unique_ordering,
            is_main_image=True,
            is_deleted=False,
            uploaded_by=message.from_user.id if message.from_user else None,
            uploaded_at=datetime.now(),
            file_size=photo.file_size,
            title=None,  # У главного изображения нет title
            mime_type='image',
            original_filename=f"main_image_{product_id}.jpg"
        )
        
        session.add(new_main_image)
        await session.commit()
        
        file_size_text = ""
        if photo.file_size:
            file_size_kb = photo.file_size / 1024
            file_size_text = f"📷 <b>Размер файла:</b> {file_size_kb:.1f} КБ\n"
        
        success_text = (
            f"🟢 <b>Главное изображение успешно загружено!</b>\n\n"
            f"📦 <b>Продукт:</b> {esc(product_name)}\n"
            f"{file_size_text}\n"
            f"Теперь это изображение будет отображаться в карточке продукта."
        )
        
        # Отправляем загруженное изображение как подтверждение
        await message.answer_photo(
            photo=photo.file_id,
            caption=success_text,
            parse_mode="HTML",
            reply_markup=get_admin_main_menu_keyboard()
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(
            f"🔴 Ошибка при загрузке изображения: {str(e)}\n\n"
            "Попробуйте ещё раз или обратитесь к администратору.",
            reply_markup=get_admin_main_menu_keyboard()
        )
        await state.clear()

@router.callback_query(lambda c: c.data == 'admin:delete_main_image')
async def admin_delete_main_image_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Удалить главное фото' из админского меню"""
    if not is_admin:
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(UploadMainImage.waiting_product_id)
    await state.update_data(action="delete")  # Отмечаем, что это удаление
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            # Пытаемся отредактировать как текстовое сообщение
            await callback.message.edit_text(
                "<b>🗑️🖼️ Удаление главного изображения</b>\n\n"
                "Введите ID продукта, у которого хотите удалить главное изображение:\n\n"
                "ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.",
                parse_mode="HTML"
            )
        except Exception:
            # Если не получилось (например, сообщение с медиа), отправляем новое
            await callback.message.answer(
                "<b>🗑️🖼️ Удаление главного изображения</b>\n\n"
                "Введите ID продукта, у которого хотите удалить главное изображение:\n\n"
                "ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.",
                parse_mode="HTML"
            )
            # Пытаемся удалить предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception:
                pass  # Игнорируем ошибку удаления
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('confirm_delete_main_image:'))
async def confirm_delete_main_image(callback: types.CallbackQuery, session: AsyncSession):
    """Подтверждение удаления главного изображения"""
    if not callback.data:
        return
    
    product_id = int(callback.data.split(':')[1])
    
    try:
        # Физически удаляем главное изображение
        await session.execute(
            delete(ProductFile).where(
                ProductFile.product_id == product_id,
                ProductFile.is_main_image == True
            )
        )
        await session.commit()
        
        # Получаем информацию о продукте
        product_service = ProductService(session)
        product = await product_service.get_product_by_id(product_id)
        
        success_text = (
            f"🟢 <b>Главное изображение успешно удалено!</b>\n\n"
            f"📦 <b>Продукт:</b> {esc(product['name'] if product else 'Неизвестен')}\n\n"
            f"Теперь карточка продукта будет отображаться без изображения."
        )
        
        if callback.message and isinstance(callback.message, types.Message):
            try:
                # Пытаемся отредактировать как текстовое сообщение
                await callback.message.edit_text(
                    success_text,
                    parse_mode="HTML",
                    reply_markup=get_admin_main_menu_keyboard()
                )
            except Exception:
                # Если не получилось (например, сообщение с медиа), отправляем новое
                await callback.message.answer(
                    success_text,
                    parse_mode="HTML",
                    reply_markup=get_admin_main_menu_keyboard()
                )
                # Пытаемся удалить предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass  # Игнорируем ошибку удаления
        await callback.answer("Главное изображение удалено!")
        
    except Exception as e:
        await callback.answer(f"Ошибка при удалении изображения: {str(e)}", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith('cancel_delete_main_image:'))
async def cancel_delete_main_image(callback: types.CallbackQuery):
    """Отмена удаления главного изображения"""
    if callback.message and isinstance(callback.message, types.Message):
        try:
            # Пытаемся отредактировать как текстовое сообщение
            await callback.message.edit_text(
                "<b>Администрирование</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_admin_main_menu_keyboard()
            )
        except Exception:
            # Если не получилось (например, сообщение с медиа), отправляем новое
            await callback.message.answer(
                "<b>Администрирование</b>\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=get_admin_main_menu_keyboard()
            )
            # Пытаемся удалить предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception:
                pass  # Игнорируем ошибку удаления
    await callback.answer("Удаление отменено")

@router.callback_query(lambda c: c.data and c.data.startswith('replace_main_image:'))
async def replace_main_image(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработчик замены главного изображения"""
    if not callback.data:
        return
    
    product_id = int(callback.data.split(':')[1])
    
    # Получаем информацию о продукте
    product_service = ProductService(session)
    product = await product_service.get_product_by_id(product_id)
    
    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    # Устанавливаем состояние ожидания изображения
    await state.set_state(UploadMainImage.waiting_image)
    await state.update_data(product_id=product_id, product_name=product['name'])
    
    response_text = (
        f"📦 <b>Продукт:</b> {esc(product['name'])}\n\n"
        f"🔄 <b>Замена главного изображения</b>\n\n"
        f"Пришлите новое изображение, которое заменит текущее главное изображение:\n\n"
        f"⚠️ <i>Принимаются только изображения (JPG, PNG, GIF и т.д.)</i>"
    )
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            # Пытаемся отредактировать как текстовое сообщение
            await callback.message.edit_text(
                response_text,
                parse_mode="HTML"
            )
        except Exception:
            # Если не получилось (например, сообщение с медиа), отправляем новое
            await callback.message.answer(
                response_text,
                parse_mode="HTML"
            )
            # Пытаемся удалить предыдущее сообщение
            try:
                await callback.message.delete()
            except Exception:
                pass  # Игнорируем ошибку удаления
    
    await callback.answer()
