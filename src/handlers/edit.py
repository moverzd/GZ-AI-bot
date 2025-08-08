from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.filters.admin import AdminFilter
from src.services.product_service import ProductService
from src.handlers.states import EditCard, EditPackage
from src.core.utils import esc
from src.keyboards.admin import get_edit_field_keyboard

router = Router()
router.message.filter(AdminFilter())

@router.message(Command('edit_product'))
async def cmd_edit(message: types.Message, state: FSMContext, command:
                    CommandObject, session: AsyncSession):
    """
    /edit <id> или /edit_product <id> - редактирование продукта
    """

    if not command.args:
        await message.answer(
            "🔴 Не указан ID продукта.\n\n"
            "<b>Использование:</b>\n"
            "• <code>/edit_product id_продукта</code>\n"
            "ℹ️ ID продукта можно найти в карточке продукта.",
            parse_mode="HTML"
        )
        return
    
    try:
        product_id = int(command.args)
    except ValueError:
        await message.answer(
            "🔴 Некорректный ID продукта. Используйте число.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
        return
    
    # Получаем информацию о продукте
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await message.answer(
            f"🔴 Продукт с ID {product_id} не найден или удален.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
        return
    
    # Сохраняем ID продукта в состоянии
    await state.update_data(product_id=product_id)
    
    # Показываем меню выбора поля для редактирования
    await message.answer(
        f"Редактирование продукта: <b>{product_info['name']}</b>\n\n"
        "Выберите поле для редактирования:",
        reply_markup=get_edit_field_keyboard(product_id),
        parse_mode="HTML"
    )


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
        "description": "полное описание",
        "advantages": "преимущества",
        "notes": "расход"
    }
    
    field_display = field_names.get(field_name, field_name)
    
    # Получаем информацию о продукте для отображения текущего значения
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await callback.message.edit_text("Продукт не найден или удален")
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
    
    current_text = f"<b>Текущее значение:</b> {esc(current_value)}" if current_value else "<b>Текущее значение:</b> не задано"
    
    # Запрашиваем новое значение
    await callback.message.edit_text(
        f"<b>Редактирование поля:</b> {field_display}\n"
        f"<b>Продукт:</b> {esc(product_info['name'])} (ID: {product_id})\n\n"
        f"{current_text}\n\n"
        f"Введите новое значение для поля <b>\"{field_display}\"</b>:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(EditCard.waiting_value)
async def save_value(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Сохранение нового значения поля продукта
    """
    if not message.text:
        await message.answer(
            "🔴 Введите текстовое значение:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    field = data.get("field")
    
    if not product_id or not field:
        await message.answer(
            "🔴 Ошибка состояния. Начните редактирование заново.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
        await state.clear()
        return
    
    # Получаем новое значение
    new_value = message.text.strip()
    
    # Обновляем значение в базе данных
    product_service = ProductService(session)
    success = await product_service.update_product_field(int(product_id), str(field), new_value)
    
    if success:       # Получаем обновленную информацию о продукте
        updated_product_info = await product_service.get_product_by_id(int(product_id))
        
        if updated_product_info:
            # Показываем сообщение об успешном обновлении и возвращаем к меню редактирования
            await message.answer(
                f"🟢 Значение поля успешно обновлено!\n\n"
                f"Продолжить редактирование продукта: <b>{esc(updated_product_info['name'])}</b>",
                reply_markup=get_edit_field_keyboard(int(product_id)),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🟢 Значение поля успешно обновлено!",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
                ]])
            )
    else:
        await message.answer(
            "🔴 Произошла ошибка при обновлении поля.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
    
    # Сбрасываем состояние
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("edit_package:"))
async def start_edit_package(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """
    Начинает процесс редактирования упаковки продукта (новая таблица product_package)
    """
    if not callback.data or not callback.message:
        await callback.answer("Ошибка обработки")
        return
    
    # Парсим callback_data: edit_package:id_продукта
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
        await callback.message.edit_text("Продукт не найден или удален")
        await callback.answer()
        return
    
    # Получаем текущую информацию об упаковке
    current_package = await product_service.get_product_package(product_id)
    
    # Сохраняем ID продукта в состоянии
    await state.update_data(product_id=product_id)
    await state.set_state(EditPackage.waiting_package_type)
    
    # Показываем текущее значение и запрашиваем новое
    current_type = str(current_package.package_type) if current_package else "не задан"
    
    await callback.message.edit_text(
        f"<b>Редактирование упаковки продукта:</b>\n"
        f"<b>Продукт:</b> {esc(product_info['name'])} (ID: {product_id})\n\n"
        f"<b>Текущий тип упаковки:</b> {esc(current_type)}\n\n"
        f"Введите новый <b>тип упаковки</b> (например: ведро, мешок, канистра):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditPackage.waiting_package_type)
async def receive_package_type(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Получает тип упаковки и переходит к весу
    """
    if not message.text:
        await message.answer("🔴 Введите текстовое значение для типа упаковки")
        return
    
    package_type = message.text.strip()
    
    # Сохраняем тип упаковки и переходим к весу
    await state.update_data(package_type=package_type)
    await state.set_state(EditPackage.waiting_package_weight)
    
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer("🔴 Ошибка состояния. Начните редактирование заново.")
        await state.clear()
        return
    
    # Получаем текущую информацию об упаковке
    product_service = ProductService(session)
    current_package = await product_service.get_product_package(int(product_id))
    current_weight = current_package.package_weight if current_package else "не задан"
    
    await message.answer(
        f"✅ Тип упаковки сохранен: <b>{esc(package_type)}</b>\n\n"
        f"<b>Текущий вес одного продукта:</b> {current_weight} кг\n\n"
        f"Введите новый <b>вес одного продукта</b> в килограммах (например: 25.0):",
        parse_mode="HTML"
    )


@router.message(EditPackage.waiting_package_weight)
async def receive_package_weight(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Получает вес упаковки и переходит к количеству на паллете
    """
    if not message.text:
        await message.answer("🔴 Введите числовое значение для веса")
        return
    
    try:
        package_weight = float(message.text.strip())
        if package_weight <= 0:
            raise ValueError("Вес должен быть положительным числом")
    except ValueError:
        await message.answer("🔴 Введите корректное положительное число для веса (например: 25.0)")
        return
    
    # Сохраняем вес и переходим к количеству на паллете
    await state.update_data(package_weight=package_weight)
    await state.set_state(EditPackage.waiting_packages_per_pallet)
    
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer("🔴 Ошибка состояния. Начните редактирование заново.")
        await state.clear()
        return
    
    # Получаем текущую информацию об упаковке
    product_service = ProductService(session)
    current_package = await product_service.get_product_package(int(product_id))
    current_pallet = current_package.packages_per_pallet if current_package else "не задано"
    
    await message.answer(
        f"✅ Вес упаковки сохранен: <b>{package_weight} кг</b>\n\n"
        f"<b>Текущее количество в одном паллете:</b> {current_pallet} шт\n\n"
        f"Введите новое <b>количество упаковок в одном паллете</b> (например: 33):",
        parse_mode="HTML"
    )


@router.message(EditPackage.waiting_packages_per_pallet)
async def receive_packages_per_pallet(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Получает количество на паллете и переходит к массе нетто
    """
    if not message.text:
        await message.answer("🔴 Введите числовое значение для количества")
        return
    
    try:
        packages_per_pallet = int(message.text.strip())
        if packages_per_pallet <= 0:
            raise ValueError("Количество должно быть положительным числом")
    except ValueError:
        await message.answer("🔴 Введите корректное положительное целое число (например: 33)")
        return
    
    # Сохраняем количество и переходим к массе нетто
    await state.update_data(packages_per_pallet=packages_per_pallet)
    await state.set_state(EditPackage.waiting_net_weight)
    
    data = await state.get_data()
    product_id = data.get("product_id")
    
    if not product_id:
        await message.answer("🔴 Ошибка состояния. Начните редактирование заново.")
        await state.clear()
        return
    
    # Получаем текущую информацию об упаковке
    product_service = ProductService(session)
    current_package = await product_service.get_product_package(int(product_id))
    current_net = current_package.net_weight if current_package else "не задана"
    
    await message.answer(
        f"✅ Количество на паллете сохранено: <b>{packages_per_pallet} шт</b>\n\n"
        f"<b>Текущая масса нетто:</b> {current_net} кг\n\n"
        f"Введите новую <b>массу нетто</b> в килограммах (например: 825.0):",
        parse_mode="HTML"
    )


@router.message(EditPackage.waiting_net_weight)
async def receive_net_weight(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Получает массу нетто и сохраняет всю информацию об упаковке
    """
    if not message.text:
        await message.answer("🔴 Введите числовое значение для массы нетто")
        return
    
    try:
        net_weight = float(message.text.strip())
        if net_weight <= 0:
            raise ValueError("Масса должна быть положительным числом")
    except ValueError:
        await message.answer("🔴 Введите корректное положительное число для массы нетто (например: 825.0)")
        return
    
    # Получаем все данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    package_type = data.get("package_type")
    package_weight = data.get("package_weight")
    packages_per_pallet = data.get("packages_per_pallet")
    
    if not all([product_id, package_type, package_weight, packages_per_pallet]):
        await message.answer(
            "🔴 Ошибка состояния. Начните редактирование заново.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
        await state.clear()
        return
    
    # Сохраняем информацию об упаковке в базе данных
    product_service = ProductService(session)
    success = await product_service.update_or_create_product_package(
        product_id=int(product_id),
        package_type=str(package_type),
        package_weight=float(package_weight),
        packages_per_pallet=int(packages_per_pallet),
        net_weight=net_weight
    )
    
    if success:
        # Получаем обновленную информацию о продукте
        updated_product_info = await product_service.get_product_by_id(int(product_id))
        
        if updated_product_info:
            await message.answer(
                f"🟢 Информация об упаковке успешно обновлена!\n\n"
                f"<b>Продукт:</b> {esc(updated_product_info['name'])}\n"
                f"<b>Тип упаковки:</b> {esc(str(package_type))}\n"
                f"<b>Вес одного продукта:</b> {package_weight} кг\n"
                f"<b>Количество на паллете:</b> {packages_per_pallet} шт\n"
                f"<b>Масса нетто:</b> {net_weight} кг\n\n"
                f"Продолжить редактирование продукта?",
                reply_markup=get_edit_field_keyboard(int(product_id)),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🟢 Информация об упаковке успешно обновлена!",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
                ]])
            )
    else:
        await message.answer(
            "🔴 Произошла ошибка при обновлении информации об упаковке.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="⬅️ Назад в админ меню", callback_data="admin:menu")
            ]])
        )
    
    # Сбрасываем состояние
    await state.clear()