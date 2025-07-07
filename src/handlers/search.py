from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.search_service import SearchService
from src.database.repositories import ProductRepository, ProductFileRepository
from src.core.utils import esc
from src.keyboards.user import get_main_menu_keyboard

router = Router()


@router.message()
async def universal_search(message: types.Message, session: AsyncSession):
    """
    universal handler for searching products by name
    working with every text message
    """
    if not message.text:
        return
        
    query = message.text.strip()
    if not query:
        return
    
    search_service = SearchService(session)
    search_results = await search_service.search_products(query)
    
    if not search_results:
        await message.answer(
            f"По запросу '{esc(query)}' ничего не найдено.\n"
            "Попробуйте другой запрос или воспользуйтесь меню каталога.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Создаем список кнопок с найденными продуктами
    buttons = []
    for product, main_image in search_results[:10]:  # Показываем до 10 результатов
        # Получаем название продукта и преобразуем в строку
        product_name = str(product.name) if product.name is not None else "Без названия"
        # Показываем полное название без сокращений
        buttons.append([
            types.InlineKeyboardButton(
                text=f"📦 {product_name}",
                # Добавляем информацию об источнике (search) и запросе
                callback_data=f"product:{product.id}:search:{query}"
            )
        ])
    
    # Добавляем кнопки навигации
    buttons.append([
        types.InlineKeyboardButton(
            text="🔍 Новый поиск", 
            callback_data="search:new"
        ),
        types.InlineKeyboardButton(
            text="📂 Каталог", 
            callback_data="menu:catalog"
        )
    ])
    buttons.append([
        types.InlineKeyboardButton(
            text="⬅️ В главное меню", 
            callback_data="menu:main"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Показываем список найденных продуктов
    result_text = f"🔍 <b>Результаты поиска по запросу:</b> {esc(query)}\n\n"
    result_text += f"Найдено продуктов: <b>{len(search_results)}</b>\n"
    result_text += "Выберите продукт для просмотра подробной информации:"
    
    await message.answer(
        result_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data == 'search:new')
async def new_search(callback: types.CallbackQuery):
    """
    Обработчик кнопки "Новый поиск"
    """
    if callback.message and isinstance(callback.message, types.Message):
        await callback.message.edit_text(
            "🔍 <b>Поиск продуктов</b>\n\n"
            "Введите название продукта или его часть для поиска:",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ В главное меню",
                    callback_data="menu:main"
                )
            ]])
        )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('search:back:'))
async def back_to_search_results(callback: types.CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Назад к результатам поиска"
    Возвращает пользователя к результатам поиска по исходному запросу
    """
    if not callback.data:
        return
    
    query = callback.data.split(':', 2)[2]
    if not query:
        await callback.answer("Поисковый запрос пуст")
        return
    
    search_service = SearchService(session)
    search_results = await search_service.search_products(query)
    
    if not search_results:
        no_results_text = f"По запросу '{esc(query)}' больше нет результатов.\n" \
                        "Попробуйте новый поиск или воспользуйтесь каталогом."
        no_results_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(
                text="🔍 Новый поиск", 
                callback_data="search:new"
            ),
            types.InlineKeyboardButton(
                text="📂 Каталог", 
                callback_data="menu:catalog"
            )
        ], [
            types.InlineKeyboardButton(
                text="⬅️ В главное меню", 
                callback_data="menu:main"
            )
        ]])
        
        if callback.message and isinstance(callback.message, types.Message):
            try:
                # Проверяем, есть ли медиа в сообщении
                if callback.message.photo or callback.message.document or callback.message.video:
                    # Для сообщений с медиа отправляем новое сообщение
                    await callback.message.answer(
                        no_results_text,
                        reply_markup=no_results_keyboard,
                        parse_mode="HTML"
                    )
                    # По возможности удаляем предыдущее сообщение
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass  # Игнорируем ошибку, если не удалось удалить сообщение
                else:
                    # Для текстовых сообщений используем edit_text
                    await callback.message.edit_text(
                        no_results_text,
                        reply_markup=no_results_keyboard,
                        parse_mode="HTML"
                    )
            except Exception as e:
                # В случае ошибки отправляем новое сообщение
                await callback.message.answer(
                    no_results_text,
                    reply_markup=no_results_keyboard,
                    parse_mode="HTML"
                )
        await callback.answer()
        return
    
    # Создаем список кнопок с найденными продуктами
    buttons = []
    for product, main_image in search_results[:10]:  # Показываем до 10 результатов
        # Получаем название продукта и преобразуем в строку
        product_name = str(product.name) if product.name is not None else "Без названия"
        # Показываем полное название без сокращений
        buttons.append([
            types.InlineKeyboardButton(
                text=f"📦 {product_name}",
                # Добавляем информацию об источнике (search) и запросе
                callback_data=f"product:{product.id}:search:{query}"
            )
        ])
    
    # Добавляем кнопки навигации
    buttons.append([
        types.InlineKeyboardButton(
            text="🔍 Новый поиск", 
            callback_data="search:new"
        ),
        types.InlineKeyboardButton(
            text="📂 Каталог", 
            callback_data="menu:catalog"
        )
    ])
    buttons.append([
        types.InlineKeyboardButton(
            text="⬅️ В главное меню", 
            callback_data="menu:main"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Показываем список найденных продуктов
    result_text = f"🔍 <b>Результаты поиска по запросу:</b> {esc(query)}\n\n"
    result_text += f"Найдено продуктов: <b>{len(search_results)}</b>\n"
    result_text += "Выберите продукт для просмотра подробной информации:"
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое сообщение
                await callback.message.answer(
                    result_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                # По возможности удаляем предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass  # Игнорируем ошибку, если не удалось удалить сообщение
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    result_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
                result_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    await callback.answer()
