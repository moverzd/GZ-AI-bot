from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.filters.admin import AdminFilter
from src.keyboards.admin import get_edit_field_keyboard
from src.services.product_service import ProductService
from src.handlers.states import EditCard

router = Router()
router.message.filter(AdminFilter())

@router.message(Command('edit'))
assync def cmd_edit(message: types.Message, state: FSMContext, command:
                    CommandObject, session: AsyncSession):
    """
    /edit <id>
    """

    if not command.args:
        await message.answer("❌ Не указан ID продукта. Используйте: /edit <id продукта>")
        return
    
    try:
        product_id = int(command.args)
    except ValueError:
        await message.answer("❌ Некорректный ID продукта. Используйте число.")
        return
    
    # Получаем информацию о продукте
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await message.answer(f"❌ Продукт с ID {product_id} не найден или удален.")
        return
    
    # Сохраняем ID продукта в состоянии
    await state.update_data(product_id=product_id)
    
    # Показываем меню выбора поля для редактирования
    await message.answer(
        f"📝 Редактирование продукта: <b>{product_info['name']}</b>\n\n"
        "Выберите поле для редактирования:",
        reply_markup=get_edit_field_keyboard(product_id),
        parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data.startswith("field:"))
async def choose_field(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработчик выбора поля для редактирования
    """
    # Парсим callback_data: field:имя_поля:id_продукта
    parts = callback.data.split(':')
    field_name = parts[1]
    product_id = int(parts[2])
    
    # Сохраняем информацию в состоянии
    await state.update_data(field=field_name, product_id=product_id)
    await state.set_state(EditCard.waiting_value)
    
    # Определяем понятное название поля
    field_names = {
        "name": "название",
        "short_desc": "краткое описание",
        "description": "полное описание",
        "advantages": "преимущества",
        "notes": "примечания",
        "package": "упаковку"
    }
    
    field_display = field_names.get(field_name, field_name)
    
    # Запрашиваем новое значение
    await callback.message.answer(f"Введите новое {field_display} для продукта:")
    await callback.answer()

@router.message(EditCard.waiting_value)
async def save_value(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Сохранение нового значения поля продукта
    """
    # Получаем данные из состояния
    data = await state.get_data()
    product_id = data.get("product_id")
    field = data.get("field")
    
    # Получаем новое значение
    new_value = message.text
    
    # Обновляем значение в базе данных
    product_service = ProductService(session)
    success = await product_service.update_product_field(product_id, field, new_value)
    
    if success:
        await message.answer(f"✅ Значение поля успешно обновлено!")
    else:
        await message.answer("❌ Произошла ошибка при обновлении поля.")
    
    # Сбрасываем состояние
    await state.clear()