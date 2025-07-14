from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from typing import cast

from src.handlers.states import AddProd, DeleteProduct, EditCard, AddFiles
from src.database.models import Product, Category, Sphere, ProductSphere, ProductFile
from src.core.utils import esc

"""
Административная логика бота. 
Все админские функции используют фильтр:
router.message.filter(AdminFilter())

"""
router = Router()

def is_accessible_message(message) -> bool:
    """Проверка, что сообщение можно редактировать"""
    return isinstance(message, types.Message) and hasattr(message, 'edit_text')

@router.callback_query(lambda c: c.data == 'admin:add_product')
async def admin_add_product_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Добавить продукт' из админского меню"""
    if not is_admin:
        await callback.answer("🔴 У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(AddProd.waiting_name)
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text("➕📦 <b>Добавление нового продукта </b>\n\n"
            "Введите название нового продукта:\n\n"
            "ℹ️ Для выхода в панель администратора введите /admin")
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer("➕📦 <b>Добавление нового продукта </b>\n\n"
            "Введите название нового продукта:\n\n"
            "ℹ️ Для выхода в панель администратора введите /admin")
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:edit_product')
async def admin_edit_product_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Отредактировать продукт' из админского меню"""
    if not is_admin:
        await callback.answer("🔴 У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(EditCard.waiting_product_id)
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "✏️📦 <b>Редактирование продукта</b>\n\n"
                "Введите ID продукта, который хотите отредактировать:\n\n"
                "ℹ️ ️ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.\n" "ℹ️ Для выхода в панель администратора введите /admin",
                parse_mode="HTML"
            )
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                "✏️📦 <b>Редактирование продукта</b>\n\n"
                "Введите ID продукта, который хотите отредактировать:\n\n"
                "ℹ️ ️ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.""ℹ️ Для выхода в панель администратора введите /admin",
                parse_mode="HTML"
            )
            return
    await callback.answer()

@router.callback_query(lambda c: c.data == 'admin:delete_product')
async def admin_delete_product_callback(callback: types.CallbackQuery, state: FSMContext, is_admin: bool = False):
    """Обработчик кнопки 'Удалить продукт' из админского меню"""
    if not is_admin:
        await callback.answer("🔴 У вас нет прав администратора", show_alert=True)
        return
    
    await state.set_state(DeleteProduct.waiting_product_id)
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "🗑️📦 <b>Удаление продукта</b>\n\n"
                "Введите ID продукта, который хотите удалить:\n\n"
                "ℹ️ ️ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.\n" "ℹ️ Для выхода в панель администратора введите /admin",
                parse_mode="HTML"
            )
        except Exception:
            # Если не удается отредактировать (например, сообщение с медиа), отправляем новое
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                "🗑️📦 <b>Удаление продукта</b>\n\n"
                "Введите ID продукта, который хотите удалить:\n\n"
                "ℹ️ ️ID продукта можно узнать в каталоге или поиске - он отображается в описании каждого продукта.\n" 
                "ℹ️ Для выхода в панель администратора введите /admin",
                parse_mode="HTML"
            )
            return
    await callback.answer()

@router.message(Command('add_product'))
async def start_add_product(message: types.Message, state: FSMContext, is_admin: bool = False):
    """Добавить продукт в админ меню"""
    if not is_admin:
        await message.answer("🔴 У вас нет прав администратора")
        return
    
    await state.set_state(AddProd.waiting_name)
    await message.answer("Введите название нового продукта:")

@router.message(AddProd.waiting_name)
async def process_name(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка названия продукта"""
    if not message.text or not message.text.strip():
        await message.answer("🔴 Название не может быть пустым. Введите название продукта:")
        return
    
    name = message.text.strip()
    await state.update_data(name=name)
    
    # Получаем список категорий
    result = await session.execute(select(Category))
    categories = result.scalars().all()
    
    if not categories:
        await message.answer("🔴 В системе нет категорий. Сначала добавьте категории.")
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
        await callback.answer("🔴 Ошибка обработки")
        return
        
    message = cast(types.Message, callback.message)
    category_id = int(callback.data.split('_')[1])
    await state.update_data(category_id=category_id)
    
    # Получаем название категории
    result = await session.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    
    if not category:
        await message.edit_text("🔴 Категория не найдена")
        await state.clear()
        return
    
    # Получаем список сфер
    result = await session.execute(select(Sphere))
    spheres = result.scalars().all()
    
    if not spheres:
        await message.edit_text("🔴 В системе нет сфер применения.")
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
        await callback.answer("🔴 Ошибка обработки")
        return
        
    message = cast(types.Message, callback.message)
    sphere_id = int(callback.data.split('_')[1])
    
    # Получаем данные из состояния
    data = await state.get_data()
    name = data.get('name')
    category_id = data.get('category_id')
    
    if not name or not category_id:
        await message.edit_text("🔴 Ошибка: данные потеряны")
        await state.clear()
        return
    
    # Получаем название сферы
    result = await session.execute(select(Sphere).where(Sphere.id == sphere_id))
    sphere = result.scalar_one_or_none()
    
    if not sphere:
        await message.edit_text("🔴 Сфера не найдена")
        await state.clear()
        return
    
    # Сохраняем sphere_id и переходим к описанию
    await state.update_data(sphere_id=sphere_id, sphere_name=str(sphere.name))
    await state.set_state(AddProd.waiting_description)
    
    await message.edit_text(
        f"Основные поля заполнены:\n"
        f"Название: {esc(name)}\n"
        f"Категория: выбрана\n"
        f"Сфера: {esc(str(sphere.name))}\n\n"
        f"Описание для выбранной сферы:\n"
        f"<i>(или отправьте '-' чтобы пропустить)</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AddProd.waiting_description)
async def process_description(message: types.Message, state: FSMContext):
    """Обработка подробного описания"""
    if not message.text:
        await message.answer("Отправьте текст или '-' для пропуска:")
        return
    
    description = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(description=description)
    await state.set_state(AddProd.waiting_advantages)
    
    await message.answer(
        "Введите преимущества продукта:\n"
        "<i>(или отправьте '-' чтобы пропустить)</i>",
        parse_mode="HTML"
    )

@router.message(AddProd.waiting_advantages)
async def process_advantages(message: types.Message, state: FSMContext):
    """Обработка преимуществ"""
    if not message.text:
        await message.answer("Отправьте текст или '-' для пропуска:")
        return
    
    advantages = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(advantages=advantages)
    await state.set_state(AddProd.waiting_consumption)
    
    await message.answer(
        "Введите информацию о расходе:\n"
        "<i>(или отправьте '-' чтобы пропустить)</i>",
        parse_mode="HTML"
    )

@router.message(AddProd.waiting_consumption)
async def process_consumption(message: types.Message, state: FSMContext):
    """Обработка расхода"""
    if not message.text:
        await message.answer("Отправьте текст или '-' для пропуска:")
        return
    
    consumption = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(consumption=consumption)
    await state.set_state(AddProd.waiting_package)
    
    await message.answer(
        "Введите информацию об упаковке:\n"
        "<i>(или отправьте '-' чтобы пропустить)</i>",
        parse_mode="HTML"
    )

@router.message(AddProd.waiting_package)
async def process_package(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка упаковки и создание продукта"""
    if not message.text:
        await message.answer("Отправьте текст или '-' для пропуска:")
        return
    
    package = message.text.strip() if message.text.strip() != '-' else None
    
    # Получаем все данные из состояния
    data = await state.get_data()
    name = data.get('name')
    category_id = data.get('category_id')
    sphere_id = data.get('sphere_id')
    sphere_name = data.get('sphere_name')
    description = data.get('description')
    advantages = data.get('advantages')
    consumption = data.get('consumption')
    
    if not name or not category_id or not sphere_id:
        await message.answer("🔴 Ошибка: основные данные потеряны")
        await state.clear()
        return
    
    try:
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
            raise Exception("🔴 Не удалось получить ID созданного продукта")
        
        # Создаем связь со сферой
        insert_sphere = insert(ProductSphere).values(
            product_id=product_id,
            sphere_id=sphere_id,
            sphere_name=sphere_name,
            product_name=name,
            description=description,
            advantages=advantages,
            notes=consumption,  # Сохраняем расход в поле notes
            package=package
        )
        await session.execute(insert_sphere)
        await session.commit()
        
        # Получаем категорию для отображения
        result = await session.execute(select(Category).where(Category.id == category_id))
        category = result.scalar_one()
        
        # Формируем информацию о созданном продукте
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
            product_info.append(f"Преимущества: {esc(advantages[:300])}{'...' if len(advantages) > 300 else ''}")
        
        if consumption:
            product_info.append(f"Расход: {esc(consumption[:100])}{'...' if len(consumption) > 100 else ''}")
        
        if package:
            product_info.append(f"Упаковка: {esc(package[:100])}{'...' if len(package) > 100 else ''}")
        
        await message.answer("\n".join(product_info), parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"Ошибка создания продукта: {str(e)[:100]}")
        await session.rollback()
    
    await state.clear()


@router.message(Command('delete_product'))
async def start_delete_product(message: types.Message, state: FSMContext, command: CommandObject, session: AsyncSession, is_admin: bool = False):
    """Удаление продукта по ID (только для админов)"""
    if not is_admin:
        await message.answer("🔴 У вас нет прав администратора")
        return
    
    # Проверяем, передан ли ID в команде
    if not command.args:
        await message.answer(
            "🗑️📦 <b>Использование команды:</b>\n"
            "<code>/delete_product ID</code>\n\n"
            "Пример: <code>/delete_product 123</code>\n\n"
            "ℹ️ ID продукта можно узнать в каталоге или поиске.",
            parse_mode="HTML"
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
                f"🔴 Продукт с ID {product_id} не найден или уже удален."
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
                types.InlineKeyboardButton(text="🟢 Да, удалить", callback_data=f"delete_confirm:{product_id}"),
                types.InlineKeyboardButton(text="🔴 Нет, отменить", callback_data=f"delete_cancel:{product_id}")
            ]
        ])
        
        await message.answer("\n".join(product_info), parse_mode="HTML", reply_markup=keyboard)
        
    except ValueError:
        await message.answer(
            "🔴 <b>Неверный формат ID</b>\n\n"
            "Используйте: <code>/delete_product ID</code>\n"
            "Пример: <code>/delete_product 123</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"🔴 Ошибка при поиске продукта: {str(e)[:100]}"
        )

# Удаляем старый обработчик состояния DeleteProduct.waiting_product_id
# @router.message(DeleteProduct.waiting_product_id)  # <-- УДАЛЯЕМ ЭТУ ФУНКЦИЮ

# Обработчик кнопки подтверждения удаления (остается без изменений)
@router.callback_query(lambda c: c.data and c.data.startswith('delete_confirm:'))

async def confirm_delete_product_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение удаления продукта через кнопку"""
    if not callback.data:
        await callback.answer("🔴 Ошибка обработки")
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
                    await callback.message.edit_text("🔴 Продукт не найден или уже удален.")
                except Exception:
                    await callback.answer()
                    await callback.message.delete()
                    await callback.message.answer("🔴 Продукт не найден или уже удален.")
                    return
            await callback.answer()
            return
        
        # Выполняем мягкое удаление
        await session.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(is_deleted=True)
        )
        await session.commit()
        
        # Логируем удаление
        import logging
        logger = logging.getLogger(__name__)
        user_id = callback.from_user.id if callback.from_user else "Unknown"
        logger.info(f"Админ {user_id} мягко удалил продукт {product_id}: {product.name}")
        
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    f"🟢 <b>Продукт успешно удален!</b>\n\n"
                    f"ID: {product_id}\n"
                    f"Название: {esc(str(product.name))}\n"
                    f"Статус: Удален\n\n"
                    f"Продукт помечен как удаленный и больше не отображается в каталоге.",
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")
                    ]])
                )
            except Exception:
                await callback.answer("🟢 Продукт удален")
                await callback.message.delete()
                await callback.message.answer(
                    f"🟢 <b>Продукт успешно удален!</b>\n\n"
                    f"ID: {product_id}\n"
                    f"Название: {esc(str(product.name))}\n"
                    f"Статус: Удален\n\n"
                    f"Продукт помечен как удаленный и больше не отображается в каталоге.",
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")
                    ]])
                )
                return
        await callback.answer("🟢 Продукт удален")
        
    except Exception as e:
        if callback.message and isinstance(callback.message, types.Message):
            try:
                await callback.message.edit_text(
                    f"🔴 Ошибка при удалении продукта: {str(e)[:100]}\n"
                    "Попробуйте еще раз.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="Главное меню", callback_data="menu:main")
                    ]])
                )
            except Exception:
                await callback.answer("🔴 Ошибка удаления")
                await callback.message.delete()
                await callback.message.answer(
                    f"🔴 Ошибка при удалении продукта: {str(e)[:100]}\n"
                    "Попробуйте еще раз.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="Главное меню", callback_data="menu:main")
                    ]])
                )
                await session.rollback()
                return
        await callback.answer("🔴 Ошибка удаления")
        await session.rollback()

# Обработчик кнопки отмены удаления
@router.callback_query(lambda c: c.data and c.data.startswith('delete_cancel:'))
async def cancel_delete_product_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена удаления продукта через кнопку"""
    if not callback.data:
        await callback.answer("🔴 Ошибка обработки")
        return
    
    product_id = callback.data.split(':')[1]
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                f"<b>Удаление отменено!</b>\n\n"
                f"Продукт с ID {product_id} остался без изменений.",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="Главное меню", callback_data="menu:main")
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
                    types.InlineKeyboardButton(text="Главное меню", callback_data="menu:main")
                ]])
            )
            return
    await callback.answer("Удаление отменено")


@router.message(DeleteProduct.waiting_product_id)
async def process_delete_product_id_fsm(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ID продукта для удаления через FSM (кнопка в админском меню)"""
    if not message.text:
        await message.answer(
            "Пожалуйста, отправьте текст с ID продукта.\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
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
            await message.answer(
                f"🔴 Продукт с ID {product_id} не найден или уже удален.\n"
                "Попробуйте еще раз или отправьте /cancel для отмены."
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
                types.InlineKeyboardButton(text="🟢 Да, удалить", callback_data=f"delete_confirm:{product_id}"),
                types.InlineKeyboardButton(text="🔴 Нет, отменить", callback_data=f"delete_cancel:{product_id}")
            ]
        ])
        
        await message.answer("\n".join(product_info), parse_mode="HTML", reply_markup=keyboard)
        await state.clear()  # Очищаем состояние после показа подтверждения
        
    except ValueError:
        await message.answer(
            "<b>Неверный формат ID</b>\n\n"
            "Введите число.\n"
            "Попробуйте еще раз или отправьте /cancel для отмены.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"🔴 Ошибка при поиске продукта: {str(e)[:100]}\n"
            "Попробуйте еще раз."
        )


@router.message(Command("cancel"))
async def cancel_operation(message: types.Message, state: FSMContext):
    """Отмена текущей операции"""
    await state.clear()
    await message.answer(
        "Операция отменена.",
        parse_mode="HTML"
    )

# Обработчик ввода ID продукта для редактирования
@router.message(EditCard.waiting_product_id)
async def process_edit_product_id(message: types.Message, state: FSMContext, session: AsyncSession):
    """Обработка ID продукта для редактирования"""
    if not message.text:
        await message.answer(
            "Пожалуйста, отправьте текст с ID продукта.\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
        return
        
    try:
        product_id = int(message.text.strip())
        
        # Проверяем существование продукта
        from src.services.product_service import ProductService
        product_service = ProductService(session)
        product_info = await product_service.get_product_by_id(product_id)
        
        if not product_info:
            await message.answer(
                f"🔴 Продукт с ID {product_id} не найден или удален.\n"
                "Попробуйте еще раз или отправьте /cancel для отмены."
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
        await message.answer(
            "🔴 Неверный формат ID. Введите число.\n"
            "Попробуйте еще раз или отправьте /cancel для отмены."
        )
    except Exception as e:
        await message.answer(
            f"🔴 Ошибка при поиске продукта: {str(e)[:100]}\n"
            "Попробуйте еще раз."
        )
