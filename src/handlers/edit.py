from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, delete

from src.filters.admin import AdminFilter
from src.services.product_service import ProductService
from src.handlers.states import EditCard
from src.core.utils import esc
from src.keyboards.admin import get_edit_field_keyboard

router = Router()
router.message.filter(AdminFilter())

# Команда /edit_product удалена - используйте админ-панель


@router.callback_query(lambda c: c.data.startswith("field:"))
async def choose_field(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик выбора поля для редактирования
    """
    if not callback.data or not callback.message:
        await callback.answer("Ошибка обработки")
        return
        
    # Парсим callback_data: field:имя_поля:id_продукта
    parts = callback.data.split(':')
    if len(parts) < 3:
        await callback.answer("Неверный формат данных")
        return
        
    field_name = parts[1]
    try:
        product_id = int(parts[2])
    except ValueError:
        await callback.answer("Неверный ID продукта")
        return
    
    # Сохраняем информацию в состоянии
    await state.update_data(field=field_name, product_id=product_id)
    await state.set_state(EditCard.waiting_value)
    
    # Определяем понятное название поля
    field_names = {
        "name": "название",
        "description": "описание",
        "advantages": "преимущества",
        "notes": "расход"
    }
    
    field_display = field_names.get(field_name, field_name)
    
    # Получаем информацию о продукте для отображения текущего значения
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        if callback.message and isinstance(callback.message, types.Message):
            await callback.message.edit_text("❌ Продукт с данным ID не найден или удален.\n\nПопробуйте ввести другой ID:")
        await callback.answer()
        return
    
    # Получаем текущее значение поля
    current_value = ""
    if field_name == "name":
        current_value = product_info.get("name", "")
    elif field_name in ["description", "advantages", "notes"]:
        # Эти поля берем из spheres_info (первая сфера)
        spheres_info = product_info.get("spheres_info", [])
        if spheres_info:
            current_value = spheres_info[0].get(field_name, "")
    
    # Форматируем текущее значение для отображения
    if field_name == "advantages" and current_value:
        from src.core.utils import format_advantages_for_telegram
        formatted_current = format_advantages_for_telegram(current_value)
        current_text = f"<b>Текущее значение:</b>\n{formatted_current}"
    else:
        current_text = f"<b>Текущее значение:</b> {esc(current_value)}" if current_value else "<b>Текущее значение:</b> не задано"
    
    # Формируем базовое сообщение
    message_text = (
        f"<b>Редактирование поля:</b> {field_display}\n"
        f"<b>Продукт:</b> {esc(product_info['name'])} (ID: {product_id})\n\n"
        f"{current_text}\n\n"
        f"Введите новое значение для поля <b>\"{field_display}\"</b>:"
    )
    
    # Добавляем инструкции для преимуществ
    if field_name == "advantages":
        message_text += (
            "\n\n<i>💡 Для создания списка разделяйте преимущества точкой с запятой</i>\n"
            "<b>Пример:</b> <code>Высокое качество; Долговечность; Экономичность</code>"
        )
    
    # Создаем кнопку "Назад к выбору поля"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад к выбору поля", callback_data=f"edit_card:{product_id}")
    ]])
    
    # Запрашиваем новое значение
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            message_text,
            reply_markup=back_keyboard,
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("edit_card:"))
async def back_to_edit_menu(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Назад к выбору поля" - возвращает к меню редактирования
    """
    if not callback.data:
        await callback.answer("Ошибка обработки")
        return
        
    # Парсим callback_data: edit_card:id_продукта
    parts = callback.data.split(':')
    if len(parts) < 2:
        await callback.answer("Неверный формат данных")
        return
        
    try:
        product_id = int(parts[1])
    except ValueError:
        await callback.answer("Неверный ID продукта")
        return
    
    # Получаем информацию о продукте
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await callback.answer("❌ Продукт с данным ID не найден или удален.\n\nПопробуйте ввести другой ID:")
        return
    
    # Очищаем состояние редактирования поля
    await state.clear()
    
    # Возвращаемся к меню выбора полей для редактирования
    message_text = (
        f"✏️📦 Редактирование продукта: <b>{esc(product_info['name'])}</b>\n\n"
        "Выберите поле для редактирования:"
    )
    
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            message_text,
            reply_markup=get_edit_field_keyboard(product_id),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("edit_menu:"))
async def back_to_edit_menu_old(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Обработчик кнопки "Назад к списку полей" - возвращает к меню редактирования (старая версия)
    """
    if not callback.data:
        await callback.answer("Ошибка обработки")
        return
        
    # Парсим callback_data: edit_menu:id_продукта
    parts = callback.data.split(':')
    if len(parts) < 2:
        await callback.answer("Неверный формат данных")
        return
        
    try:
        product_id = int(parts[1])
    except ValueError:
        await callback.answer("Неверный ID продукта")
        return
    
    # Получаем информацию о продукте
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await callback.answer("❌ Продукт с данным ID не найден или удален.\n\nПопробуйте ввести другой ID:")
        return
    
    # Очищаем состояние редактирования поля
    await state.clear()
    
    # Возвращаемся к меню выбора полей для редактирования
    message_text = (
        f"✏️📦 Редактирование продукта: <b>{esc(product_info['name'])}</b>\n\n"
        "Выберите поле для редактирования:"
    )
    
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            message_text,
            reply_markup=get_edit_field_keyboard(product_id),
            parse_mode="HTML"
        )
    await callback.answer()

@router.message(EditCard.waiting_value)
async def save_value(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Сохранение нового значения поля продукта
    """
    if not message.text:
        # Получаем данные из состояния
        data = await state.get_data()
        product_id = data.get("product_id")
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад к выбору поля", callback_data=f"edit_card:{product_id}") if product_id else
            InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        
        await message.answer(
            "❌ Введите текстовое значение:",
            reply_markup=back_keyboard
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    field = data.get("field")
    
    if not product_id or not field:
        await message.answer(
            "❌ Ошибка состояния. Начните редактирование заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )
        await state.clear()
        return
    
    # Получаем новое значение
    new_value = message.text.strip()
    
    # Обновляем значение в базе данных
    product_service = ProductService(session)
    success = await product_service.update_product_field(int(product_id), str(field), new_value)
    
    if success:
        # Получаем обновленную информацию о продукте
        updated_product_info = await product_service.get_product_by_id(int(product_id))
        
        if updated_product_info:
            # Формируем сообщение с отображением обновленного поля
            success_text = f"✅ Значение поля успешно обновлено!\n\n"
            
            # Показываем обновленное значение в зависимости от типа поля
            if field == "advantages":
                from src.core.utils import format_advantages_for_telegram
                formatted_advantages = format_advantages_for_telegram(new_value)
                success_text += f"<b>Новые преимущества:</b>\n{formatted_advantages}\n\n"
            elif field == "description":
                success_text += f"<b>Новое описание:</b>\n{esc(new_value)}\n\n"
            elif field == "notes":
                success_text += f"<b>Новый расход:</b>\n{esc(new_value)}\n\n"
            elif field == "name":
                success_text += f"<b>Новое название:</b> {esc(new_value)}\n\n"
            
            success_text += f"Продолжить редактирование продукта: <b>{esc(updated_product_info['name'])}</b>"
            
            # Показываем сообщение об успешном обновлении и возвращаем к меню редактирования
            await message.answer(
                success_text,
                reply_markup=get_edit_field_keyboard(int(product_id)),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "✅ Значение поля успешно обновлено!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                ]])
            )
    else:
        # Проверяем, в чем причина ошибки
        if field in ["description", "advantages", "notes"]:
            # Если это поле из ProductSphere, проверяем наличие записи
            from src.database.repositories import ProductRepository
            product_repo = ProductRepository(session)
            product_sphere = await product_repo.get_product_sphere_by_product_id(int(product_id))
            
            if not product_sphere:
                error_message = (
                    f"❌ <b>Ошибка редактирования поля '{field}'</b>\n\n"
                    f"У продукта не настроены сферы применения.\n"
                    f"Для редактирования описания, преимуществ и расхода необходимо сначала назначить продукту сферу применения.\n\n"
                    f"💡 <i>Обратитесь к администратору для настройки сфер применения.</i>"
                )
            else:
                error_message = "❌ Произошла ошибка при обновлении поля."
        else:
            error_message = "❌ Произошла ошибка при обновлении поля."
        
        await message.answer(
            error_message,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]]),
            parse_mode="HTML"
        )
    
    # Сбрасываем состояние
    await state.clear()
