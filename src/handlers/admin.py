from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from typing import cast
import logging

from src.handlers.states import AddProd, DeleteProduct, EditCard, AddFiles
from src.database.models import Product, Category, Sphere, ProductSphere, ProductFile
from src.services.category_service import CategoryService
from src.services.sphere_service import SphereService
from src.core.utils import esc

"""
Административная логика бота. 
Все админские функции используют фильтр:
router.message.filter(AdminFilter())

"""
router = Router()
logger = logging.getLogger(__name__)

def is_accessible_message(message) -> bool:
    """Проверка, что сообщение можно редактировать"""
    return isinstance(message, types.Message) and hasattr(message, 'edit_text')

@router.callback_query(lambda c: c.data == 'admin:menu')
async def admin_menu_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик возврата в админское меню"""
    if not is_admin:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    # Очищаем состояние при возврате в меню
    await state.clear()
    
    from src.keyboards.admin import get_admin_main_menu_keyboard
    
    admin_text = (
        '<b>🛠️ Панель администратора продукции</b>\n'
        '📋 Выберите действие:'
    )
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                admin_text,
                reply_markup=get_admin_main_menu_keyboard(),
                parse_mode='HTML'
            )
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.answer(
                admin_text,
                reply_markup=get_admin_main_menu_keyboard(),
                parse_mode='HTML'
            )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:add_product')
async def admin_add_product_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Добавить продукт' из админского меню"""
    if not is_admin:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(AddProd.waiting_name)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
    ]])
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "➕📦 <b>Добавление нового продукта</b>\n\n"
                "Введите название нового продукта:\n\n",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.answer(
                "➕📦 <b>Добавление нового продукта</b>\n\n"
                "Введите название нового продукта:\n\n",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:edit_product')
async def admin_edit_product_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Отредактировать продукт' из админского меню"""
    if not is_admin:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(EditCard.waiting_product_id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
    ]])
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "✏️📦 <b>Редактирование продукта</b>\n\n"
                "🔢 Введите ID продукта для редактирования:\n"
                "💡 <i>ID продукта отображается в карточке продукта и результатах поиска</i>\n",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.answer(
                "✏️📦 <b>Редактирование продукта</b>\n\n"
                "🔢 Введите ID продукта для редактирования:\n\n"
                "💡 <i>ID продукта отображается в карточке продукта и результатах поиска</i>\n",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:delete_product')
async def admin_delete_product_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Удалить продукт' из админского меню"""
    if not is_admin:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(DeleteProduct.waiting_product_id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
    ]])
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "🗑️📦 <b>Удаление продукта</b>\n\n"
                "🔢 Введите ID продукта для удаления:\n\n"
                "⚠️ <i>Внимание: продукт будет помечен как удаленный</i>\n"
                "💡 <i>ID продукта отображается в карточке продукта и результатах поиска</i>\n",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.answer(
                "🗑️📦 <b>Удаление продукта</b>\n\n"
                "🔢 Введите ID продукта для удаления:\n\n"
                "⚠️ <i>Внимание: продукт будет помечен как удаленный</i>\n"
                "💡 <i>ID продукта отображается в карточке продукта и результатах поиска</i>\n",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
    await callback.answer()

@router.message(Command('add_product'))
async def start_add_product(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Добавить продукт в админ-меню"""
    if not is_admin:
        await message.answer(
            "❌ У вас нет прав администратора",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )
        return
    
    await state.set_state(AddProd.waiting_name)
    await message.answer(
        "Введите название нового продукта:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
    )

@router.message(AddProd.waiting_name)
async def process_name(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка названия продукта"""
    if not message.text or not message.text.strip():
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            "❌ Название не может быть пустым. Введите название продукта:", 
            reply_markup=keyboard
        )
        return
    
    name = message.text.strip()
    await state.update_data(name=name)
    
    # Получаем список категорий (исключая скрытые)
    category_service = CategoryService(session)
    categories = await category_service.get_all_categories()
    
    if not categories:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            "❌ В системе нет категорий. Сначала добавьте категории.", 
            reply_markup=keyboard
        )
        await state.clear()
        return
    
    # Создаем кнопки с категориями
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.button(
            text=str(category.name),
            callback_data=f"cat_{category.id}"
        )
    # Добавляем кнопку "Назад"
    builder.button(
        text="⬅️ Назад в админ-меню",
        callback_data="admin:menu"
    )
    builder.adjust(1)
    
    await state.set_state(AddProd.waiting_category)
    await message.answer(
        f"Название: {esc(name)}\n\n"
        "Выберите категорию:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data and c.data.startswith('cat_'))
async def process_category(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора категории при создании продукта"""
    if not callback.data or not callback.message or not is_accessible_message(callback.message):
        await callback.answer("❌ Ошибка обработки")
        return
        
    message = cast(types.Message, callback.message)
    category_id = int(callback.data.split('_')[1])
    
    # Получаем название категории
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    
    if not category:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.edit_text("❌ Категория не найдена", reply_markup=keyboard)
        await state.clear()
        return
    
    # Сохраняем ID и название категории в состояние
    await state.update_data(category_id=category_id, category_name=str(category.name))
    
    # Получаем список сфер (исключая скрытые)
    sphere_service = SphereService(session)
    spheres = await sphere_service.get_all_spheres()
    
    if not spheres:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.edit_text("❌ В системе нет сфер применения.", reply_markup=keyboard)
        await state.clear()
        return
    
    # Создаем кнопки со сферами
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for sphere in spheres:
        builder.button(
            text=str(sphere.name),
            callback_data=f"sph_{sphere.id}"
        )
    # Добавляем кнопку "Назад"
    builder.button(
        text="⬅️ Назад в админ-меню",
        callback_data="admin:menu"
    )
    builder.adjust(1)
    
    await state.set_state(AddProd.waiting_sphere)
    await message.edit_text(
        f"Категория: {esc(str(category.name))}\n\n"
        "Выберите сферу применения:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith('sph_'))
async def process_sphere(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка выбора сферы и переход к дополнительным полям"""
    if not callback.data or not callback.message or not is_accessible_message(callback.message):
        await callback.answer("❌ Ошибка обработки")
        return
        
    message = cast(types.Message, callback.message)
    sphere_id = int(callback.data.split('_')[1])
    
    # Получаем данные из состояния
    data = await state.get_data()
    name = data.get('name')
    category_id = data.get('category_id')
    category_name = data.get('category_name', 'Не указана')
    
    if not name or not category_id:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.edit_text("❌ Ошибка: данные потеряны", reply_markup=keyboard)
        await state.clear()
        return
    
    # Получаем название сферы
    result = await session.execute(select(Sphere).where(Sphere.id == sphere_id))
    sphere = result.scalar_one_or_none()
    
    if not sphere:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.edit_text("❌ Сфера не найдена", reply_markup=keyboard)
        await state.clear()
        return
    
    # Сохраняем sphere_id и переходим к описанию
    await state.update_data(sphere_id=sphere_id, sphere_name=str(sphere.name))
    await state.set_state(AddProd.waiting_description)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
    ]])
    
    await message.edit_text(
        f"Основные поля заполнены:\n"
        f"Название: {esc(name)}\n"
        f"Категория: {esc(category_name)}\n"
        f"Сфера: {esc(str(sphere.name))}\n\n"
        f"Описание продукта для выбранной сферы:\n"
        f"<i>(или отправьте '-' чтобы пропустить)</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.message(AddProd.waiting_description)
async def process_description(message: types.Message, state: FSMContext):
    """Обработка подробного описания"""
    if not message.text:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer("Отправьте текст или '-' для пропуска:", reply_markup=keyboard)
        return
    
    description = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(description=description)
    await state.set_state(AddProd.waiting_advantages)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
    ]])
    await message.answer(
        "Введите преимущества продукта:\n"
        "<i>(или отправьте '-' чтобы пропустить)</i>\n\n"
        "<i>💡 Для создания списка разделяйте преимущества точкой с запятой</i>\n"
        "<b>Пример:</b> <code>Высокое качество; Долговечность; Экономичность</code>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.message(AddProd.waiting_advantages)
async def process_advantages(message: types.Message, state: FSMContext):
    """Обработка преимуществ"""
    if not message.text:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer("Отправьте текст или '-' для пропуска:", reply_markup=keyboard)
        return
    
    advantages = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(advantages=advantages)
    await state.set_state(AddProd.waiting_consumption)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
    ]])
    
    # Показываем отформатированные преимущества, если они были введены
    message_text = ""
    if advantages:
        from src.core.utils import format_advantages_for_telegram
        formatted_advantages = format_advantages_for_telegram(advantages)
        message_text = f"✅ Преимущества сохранены:\n{formatted_advantages}\n\n"
    
    message_text += (
        "Введите информацию о расходе:\n"
        "<i>(или отправьте '-' чтобы пропустить)</i>"
    )
    
    await message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.message(AddProd.waiting_consumption)
async def process_consumption(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка расхода и создание продукта"""
    if not message.text:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer("Отправьте текст или '-' для пропуска:", reply_markup=keyboard)
        return
    
    consumption = message.text.strip() if message.text.strip() != '-' else None
    
    # Получаем все данные из состояния
    data = await state.get_data()
    name = data.get('name')
    category_id = data.get('category_id')
    sphere_id = data.get('sphere_id')
    sphere_name = data.get('sphere_name')
    description = data.get('description')
    advantages = data.get('advantages')
    
    if not name or not category_id or not sphere_id:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer("❌ Ошибка: основные данные потеряны", reply_markup=keyboard)
        await state.clear()
        return
    
    try:
        from sqlalchemy import insert
        from src.services.auto_chunking_service import AutoChunkingService
        
        # Создаем продукт
        insert_product = insert(Product).values(
            name=name,
            category_id=category_id,
            is_deleted=False
        )
        result = await session.execute(insert_product)
        await session.flush()  # Заставляем получить ID
        
        # Получаем ID созданного продукта
        product_result = await session.execute(
            select(Product.id).where(Product.name == name).where(Product.category_id == category_id).order_by(Product.id.desc()).limit(1)
        )
        product_id = product_result.scalar()
        
        if not product_id:
            raise Exception("❌ Не удалось получить ID созданного продукта")
        
        # Создаем связь со сферой
        insert_sphere = insert(ProductSphere).values(
            product_id=product_id,
            sphere_id=sphere_id,
            sphere_name=sphere_name,
            product_name=name,
            description=description,
            advantages=advantages,
            notes=consumption  # Сохраняем расход в поле notes
        )
        await session.execute(insert_sphere)
        await session.commit()
        
        # Получаем объект категории для отображения
        category_result = await session.execute(select(Category).where(Category.id == category_id))
        category = category_result.scalar_one()
        
        # Индексируем продукт в векторной базе данных
        try:
            auto_chunking_service = AutoChunkingService()
            await auto_chunking_service.reindex_product(product_id, name, session)
            logger.info(f"Product {product_id} indexed in vector database")
        except Exception as e:
            logger.error(f"Failed to index product {product_id}: {str(e)}")
        
        # Формируем сообщение об успешном создании с форматированием преимуществ
        product_info = [
            f"<b>Продукт успешно создан!</b>\n",
            f"<b>ID</b>: {product_id}",
            f"<b>Название</b>: {esc(name)}",
            f"<b>Категория</b>: {esc(str(category.name))}",
            f"<b>Сфера</b>: {esc(sphere_name)}"
        ]
        
        if description:
            product_info.append(f"Описание: {esc(description[:300])}{'...' if len(description) > 300 else ''}")
        
        if advantages:
            from src.core.utils import format_advantages_for_telegram
            formatted_advantages = format_advantages_for_telegram(advantages)
            # Ограничиваем длину для сообщения подтверждения
            if len(formatted_advantages) > 300:
                formatted_advantages = formatted_advantages[:300] + '...'
            product_info.append(f"Преимущества:\n{esc(formatted_advantages)}")
        
        if consumption:
            product_info.append(f"Расход: {esc(consumption[:100])}{'...' if len(consumption) > 100 else ''}")
        
        # Добавляем кнопку "Назад в админ-меню" к сообщению об успехе
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer("\n".join(product_info), parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(f"Ошибка создания продукта: {str(e)[:100]}", reply_markup=keyboard)
        await session.rollback()
    
    await state.clear()


@router.message(Command('delete_product'))
async def start_delete_product(message: types.Message, state: FSMContext, command: CommandObject, session: AsyncSession, is_admin: bool = False):
    """Удаление продукта по ID (только для админов)"""
    if not is_admin:
        await message.answer(
            "❌ У вас нет прав администратора",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )
        return
    
    # Проверяем, передан ли ID в команде
    if not command.args:
        await message.answer(
            "🗑️📦 <b>Использование команды:</b>\n"
            "<code>/delete_product ID</code>\n\n"
            "Пример: <code>/delete_product 123</code>\n\n"
            "ℹ️ ID продукта можно узнать в каталоге или поиске.",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )
        return
    
    try:
        product_id = int(command.args.strip())
        
        # Проверяем существование продукта и что он не удален
        result = await session.execute(
            select(Product, Category).join(Category).where(
                Product.id == product_id
            ).where(Product.is_deleted == False)
        )
        product_data = result.first()
        
        if not product_data:
            await message.answer(
                f"❌ Продукт с ID {product_id} не найден или уже удален.",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                ]])
            )
            return
        
        product, category = product_data
        
        # Получаем информацию о сферах продукта
        spheres_result = await session.execute(
            select(ProductSphere).where(ProductSphere.product_id == product_id)
        )
        product_spheres = spheres_result.scalars().all()
        
        # Формируем информацию о продукте
        product_info = [
            f"🗑️📦 <b>Подтверждение удаления</b>\n",
            f"ID: {product.id}",
            f"Название: {esc(str(product.name))}",
            f"Категория: {esc(str(category.name))}"
        ]
        
        if product_spheres:
            spheres_names = [str(ps.sphere_name) for ps in product_spheres if ps.sphere_name is not None]
            if spheres_names:
                product_info.append(f"🎯 Сферы: {esc(', '.join(spheres_names))}")
        
        product_info.extend([
            "",
            "⚠️ <b>Внимание!</b> Продукт будет помечен как удаленный.",
            "Это значит, что продукт больше не будет доступен в каталоге и поиске.",
            "",
            "Подтвердите действие:"
        ])
        
        # Создаем клавиатуру с кнопками подтверждения
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{product_id}"),
                types.InlineKeyboardButton(text="❌ Нет, отменить", callback_data=f"delete_cancel:{product_id}")
            ]
        ])
        
        await message.answer("\n".join(product_info), parse_mode="HTML", reply_markup=keyboard)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат ID</b>\n\n"
            "Используйте: <code>/delete_product ID</code>\n"
            "Пример: <code>/delete_product 123</code>",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при поиске продукта: {str(e)[:100]}",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )


# Обработчик кнопки подтверждения удаления 
@router.callback_query(lambda c: c.data and c.data.startswith('delete_confirm:'))

async def confirm_delete_product_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение удаления продукта через кнопку"""
    if not callback.data:
        await callback.answer("❌ Ошибка обработки")
        return
    
    try:
        # Извлекаем ID продукта из callback_data
        product_id = int(callback.data.split(':')[1])
        
        # Получаем информацию о продукте перед удалением
        result = await session.execute(
            select(Product).where(Product.id == product_id).where(Product.is_deleted == False)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            if callback.message and isinstance(callback.message, types.Message):
                try:
                    await callback.message.edit_text("❌ Продукт не найден или уже удален.")
                except Exception:
                    await callback.answer()
                    await callback.message.delete()
                    await callback.message.answer("❌ Продукт не найден или уже удален.")
                    return
            await callback.answer()
            return
        
        # Выполняем мягкое удаление
        await session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(is_deleted=True)
        )
        
        # Автоматически удаляем все файлы продукта (БД + физические файлы)
        try:
            from src.services.file_service import FileService
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info(f"[AdminDeleteProduct] Запуск удаления файлов для продукта {product_id}")
            
            file_service = FileService(session)
            file_deletion_stats = await file_service.delete_product_files(product_id)
            
            logger.info(f"[AdminDeleteProduct] Статистика удаления файлов продукта {product_id}: {file_deletion_stats}")
            
            # Логируем результаты
            if file_deletion_stats["errors"]:
                logger.warning(f"[AdminDeleteProduct] Ошибки при удалении файлов: {file_deletion_stats['errors']}")
            else:
                logger.info(f"[AdminDeleteProduct] Успешно удалено: {file_deletion_stats['db_files_marked_deleted']} записей в БД, {file_deletion_stats['physical_files_deleted']} физических файлов")
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[AdminDeleteProduct] Ошибка при удалении файлов продукта {product_id}: {e}")
            # Не прерываем выполнение, если удаление файлов не удалось
        
        # Автоматически удаляем все эмбеддинги продукта
        try:
            from src.services.auto_chunking_service import AutoChunkingService
            import logging
            
            logger = logging.getLogger(__name__)
            logger.info(f"[AdminDeleteProduct] Запуск автоматического удаления эмбеддингов для продукта {product_id}")
            
            auto_chunking = AutoChunkingService()
            await auto_chunking.initialize()
            
            # Удаляем все эмбеддинги продукта
            await auto_chunking.embedding_service.delete_product_embeddings(product_id)
            logger.info(f"[AdminDeleteProduct] Эмбеддинги продукта {product_id} удалены")
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[AdminDeleteProduct] Ошибка при удалении эмбеддингов продукта {product_id}: {e}")
            # Не прерываем выполнение, если удаление эмбеддингов не удалось
        
        await session.commit()
        
        # Логируем удаление
        import logging
        logger = logging.getLogger(__name__)
        user_id = callback.from_user.id if callback.from_user else "Unknown"
        logger.info(f"Админ {user_id} мягко удалил продукт {product_id}: {product.name}")
        
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    f"✅ <b>Продукт успешно удален!</b>\n\n"
                    f"ID: {product_id}\n"
                    f"Название: {esc(str(product.name))}\n"
                    f"Статус: Удален\n\n"
                    f"Продукт помечен как удаленный\n"
                    f"Все связанные файлы удалены\n"
                    f"Эмбеддинги удалены из векторной БД\n"
                    f"Физические файлы удалены с диска\n\n"
                    f"✅ Продукт больше не отображается в каталоге.",
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                    ]])
                )
            except Exception:
                await callback.answer("✅ Продукт удален")
                await callback.message.delete()
                await callback.message.answer(
                    f"✅ <b>Продукт успешно удален!</b>\n\n"
                    f"ID: {product_id}\n"
                    f"Название: {esc(str(product.name))}\n"
                    f"Статус: Удален\n\n"
                    f"✅ Продукт помечен как удаленный\n"
                    f"✅ Все связанные файлы удалены\n"
                    f"✅ Эмбеддинги удалены из векторной БД\n"
                    f"✅ Физические файлы удалены с диска\n\n"
                    f"Продукт больше не отображается в каталоге.",
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                    ]])
                )
                return
        await callback.answer("✅ Продукт удален")
        
    except Exception as e:
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    f"❌ Ошибка при удалении продукта: {str(e)[:100]}\n"
                    "Попробуйте еще раз.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                    ]])
                )
            except Exception:
                await callback.answer("❌ Ошибка удаления")
                await callback.message.delete()
                await callback.message.answer(
                    f"❌ Ошибка при удалении продукта: {str(e)[:100]}\n"
                    "Попробуйте еще раз.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                    ]])
                )
                await session.rollback()
                return
        await callback.answer("❌ Ошибка удаления")
        await session.rollback()

# Обработчик кнопки отмены удаления
@router.callback_query(lambda c: c.data and c.data.startswith('delete_cancel:'))
async def cancel_delete_product_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена удаления продукта через кнопку"""
    if not callback.data:
        await callback.answer("❌ Ошибка обработки")
        return
    
    product_id = callback.data.split(':')[1]
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                f"<b>Удаление отменено!</b>\n\n"
                f"Продукт с ID {product_id} остался без изменений.",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                ]])
            )
        except Exception:
            await callback.answer("❌ Удаление отменено")
            await callback.message.delete()
            await callback.message.answer(
                f"<b>Удаление отменено!</b>\n\n"
                f"Продукт с ID {product_id} остался без изменений.",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                ]])
            )
            return
    await callback.answer("Удаление отменено")


@router.message(DeleteProduct.waiting_product_id)
async def process_delete_product_id_fsm(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ID продукта для удаления через FSM (кнопка в админском меню)"""
    if not message.text:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            "Пожалуйста, отправьте текст с ID продукта.\n",
            reply_markup=keyboard
        )
        return
        
    try:
        product_id = int(message.text.strip())
        
        # Проверяем существование продукта и что он не удален
        result = await session.execute(
            select(Product, Category).join(Category).where(
                Product.id == product_id
            ).where(Product.is_deleted == False)
        )
        product_data = result.first()
        
        if not product_data:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
            await message.answer(
                f"❌ Продукт с ID {product_id} не найден или уже удален.\n",
                reply_markup=keyboard
            )
            return
        
        product, category = product_data
        
        # Получаем информацию о сферах продукта
        spheres_result = await session.execute(
            select(ProductSphere).where(ProductSphere.product_id == product_id)
        )
        product_spheres = spheres_result.scalars().all()
        
        # Формируем информацию о продукте
        product_info = [
            f"<b>Подтверждение удаления</b>\n",
            f"<b>ID</b>: {product.id}",
            f"<b>Название</b>: {esc(str(product.name))}",
            f"<b>Категория</b>: {esc(str(category.name))}",
        ]
        
        if product_spheres:
            spheres_names = [str(ps.sphere_name) for ps in product_spheres if ps.sphere_name is not None]
            if spheres_names:
                product_info.append(f"Сферы: {esc(', '.join(spheres_names))}")
        
        product_info.extend([
            "",
            "⚠️ <b>Внимание!</b> Продукт будет помечен как удаленный.",
            "Это действие удалит продукт из каталога.",
            "",
            "Подтвердите действие:"
        ])
        
        # Создаем клавиатуру с кнопками подтверждения
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{product_id}"),
                types.InlineKeyboardButton(text="❌ Нет, отменить", callback_data=f"delete_cancel:{product_id}")
            ]
        ])
        
        await message.answer("\n".join(product_info), parse_mode="HTML", reply_markup=keyboard)
        await state.clear()  # Очищаем состояние после показа подтверждения
        
    except ValueError:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            "<b>Неверный формат ID</b>\n\n"
            "Введите число.\n",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            f"❌ Ошибка при поиске продукта: {str(e)[:100]}\n"
            "Попробуйте еще раз.",
            reply_markup=keyboard
        )


# Обработчик ввода ID продукта для редактирования
@router.message(EditCard.waiting_product_id)
async def process_edit_product_id(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ID продукта для редактирования"""
    if not message.text:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            "Пожалуйста, отправьте текст с ID продукта.\n",
            reply_markup=keyboard
        )
        return
        
    try:
        product_id = int(message.text.strip())
        
        # Проверяем существование продукта
        from src.services.product_service import ProductService
        product_service = ProductService(session)
        product_info = await product_service.get_product_by_id(product_id)
        
        if not product_info:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
            await message.answer(
                f"❌ Продукт с ID {product_id} не найден или удален.\n",
                reply_markup=keyboard
            )
            return
        
        # Сохраняем ID продукта и переходим к выбору поля
        await state.update_data(product_id=product_id)
        await state.set_state(EditCard.waiting_fields)
        
        from src.keyboards.admin import get_edit_field_keyboard
        
        await message.answer(
            f"<b>Продукт найден!</b>\n\n"
            f"<b>Название:</b> {esc(product_info['name'])}\n"
            f"<b>ID:</b> {product_id}\n\n"
            f"Выберите поле для редактирования:",
            reply_markup=get_edit_field_keyboard(product_id),
            parse_mode="HTML"
        )
        
    except ValueError:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            "❌ Неверный формат ID. Введите число.\n",
            reply_markup=keyboard
        )
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(
            f"❌ Ошибка при поиске продукта: {str(e)[:100]}\n"
            "Попробуйте еще раз.",
            reply_markup=keyboard
        )


@router.message(Command('get_products'))
async def get_all_products(message: types.Message, session: AsyncSession, is_admin: bool = False):
    """Команда для получения всех ID продуктов с их названиями"""
    if not is_admin:
        await message.answer(
            "❌ У вас нет прав администратора",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
        )
        return
    
    try:
        # Получаем все продукты
        result = await session.execute(select(Product).order_by(Product.id))
        products = result.scalars().all()
        
        if not products:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
            await message.answer("📦 В базе данных нет продуктов", reply_markup=keyboard)
            return
        
        # Формируем список продуктов
        text = "<b>📋 Список всех продуктов:</b>\n\n"
        
        for product in products:
            text += f"<b>ID:</b> {product.id} - {esc(str(product.name))}\n"
        
        # Если сообщение слишком длинное, разбиваем на части
        if len(text) > 4000:
            # Отправляем по частям
            messages = []
            current_message = "<b>📋 Список всех продуктов:</b>\n\n"
            
            for product in products:
                line = f"<b>ID:</b> {product.id} - {esc(str(product.name))}\n"
                
                if len(current_message + line) > 4000:
                    messages.append(current_message)
                    current_message = line
                else:
                    current_message += line
            
            if current_message:
                messages.append(current_message)
            
            # Отправляем все части
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
            for i, msg_text in enumerate(messages):
                if i == 0:
                    await message.answer(msg_text, parse_mode="HTML")
                elif i == len(messages) - 1:  # Последнее сообщение с кнопкой
                    await message.answer(f"<b>📋 Продолжение списка:</b>\n\n{msg_text}", parse_mode="HTML", reply_markup=keyboard)
                else:
                    await message.answer(f"<b>📋 Продолжение списка:</b>\n\n{msg_text}", parse_mode="HTML", reply_markup=keyboard)
        else:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
            ]])
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            
    except Exception as e:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
        ]])
        await message.answer(f"❌ Ошибка при получении списка продуктов: {str(e)}", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == 'admin:get_products')
async def admin_get_products_callback(callback: types.CallbackQuery, session: AsyncSession, is_admin: bool = False):
    """
    Обработчик кнопки 'Показать список продукции' из админ-меню
    """
    if not is_admin:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        # Получаем только неудаленные продукты
        result = await session.execute(select(Product).where(Product.is_deleted == False).order_by(Product.id))
        products = result.scalars().all()
        
        if not products:
            if callback.message and isinstance(callback.message, types.Message):
                try:
                    await callback.message.edit_text(
                        "📦 В базе данных нет продуктов",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                        ]])
                    )
                except Exception:
                    await callback.answer()
                    await callback.message.delete()
                    await callback.message.answer(
                        "📦 В базе данных нет продуктов",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                        ]])
                    )
            await callback.answer()
            return
        
        # Формируем список продуктов
        text = "<b>📋📦 Список активных продуктов:</b>\n\n"
        
        for product in products:
            text += f"<b>ID:</b> {product.id} - {esc(str(product.name))}\n"
        
        # Статистика
        text += f"\n<b>📊 Статистика:</b>\n"
        text += f"Всего уникальных продуктов: {len(products)}"
        
        # Создаем клавиатуру
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")]
        ])
        
        # Если сообщение слишком длинное, разбиваем на части
        if len(text) > 4000:
            if callback.message and isinstance(callback.message, types.Message):
                # Отправляем заголовок
                try:
                    await callback.message.edit_text(
                        "<b>📦📋 Список активных продуктов:</b>\n\n"
                        "Список большой, отправляю по частям...",
                        parse_mode="HTML"
                    )
                except Exception:
                    await callback.answer()
                    await callback.message.delete()
                    await callback.message.answer(
                        "<b>📋📦 Список активных продуктов:</b>\n\n"
                        "Список большой, отправляю по частям...",
                        parse_mode="HTML"
                    )
                
                # Отправляем по частям
                messages = []
                current_message = ""
                
                for product in products:
                    line = f"<b>ID:</b> {product.id} - {esc(str(product.name))}\n"
                    
                    if len(current_message + line) > 4000:  
                        messages.append(current_message)
                        current_message = line
                    else:
                        current_message += line
                
                if current_message:
                    messages.append(current_message)
                
                # Отправляем все части
                for i, msg_text in enumerate(messages):
                    if i == len(messages) - 1:  # Последнее сообщение с кнопкой
                        await callback.message.answer(f"<b>📋 Продолжение списка:</b>\n\n{msg_text}", parse_mode="HTML", reply_markup=keyboard)
                    else:
                        await callback.message.answer(f"<b>📋 Продолжение списка:</b>\n\n{msg_text}", parse_mode="HTML")
        else:
            if callback.message and isinstance(callback.message, types.Message):
                try:
                    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
                except Exception:
                    await callback.answer()
                    await callback.message.delete()
                    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        
        await callback.answer()
            
    except Exception as e:
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    f"❌ Ошибка при получении списка продуктов: {str(e)[:100]}",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                    ]])
                )
            except Exception:
                await callback.answer("❌ Ошибка получения списка", show_alert=True)
                await callback.message.delete()
                await callback.message.answer(
                    f"❌ Ошибка при получении списка продуктов: {str(e)[:100]}",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="⬅️ Назад в админ-меню", callback_data="admin:menu")
                    ]])
                )
        else:
            await callback.answer("❌ Ошибка получения списка", show_alert=True)