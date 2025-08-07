from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.search import HybridSearchService, LexicalSearchService, SemanticSearchService
from src.database.repositories import ProductRepository 
from src.database.product_file_repositories import ProductFileRepository
from src.core.utils import esc
from src.keyboards.user import get_main_menu_keyboard
from src.handlers.states import SearchProduct

router = Router()

"""
Функциональность поиска продуктов по названию.
Использует гибридный поиск с fallback на семантический поиск.
"""


@router.message(SearchProduct.waiting_query)
async def process_search_query(message: types.Message, session: AsyncSession, state: FSMContext):
    """
    Обработка поискового запроса.
    
    - Проверка на отправку текста от пользователя
    - Очистка FSM состояния
    - Использование HybridSearchService для поиска
    """
    if not message.text:
        await message.answer(
            "Пожалуйста, введите текстовый запрос для поиска.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]])
        )
        return
        
    query = message.text.strip()
    if not query:
        await message.answer(
            "Запрос не может быть пустым. Попробуйте еще раз.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]])
        )
        return
    
    # Очищаем состояние
    await state.clear()
    
    # Создаем сервисы для поиска
    search_service = await _create_hybrid_search_service(session)
    
    # Выполняем поиск
    search_results = await search_service.find_products_by_query(
        query=query,
        category_id=None,  # Можно добавить фильтр по категории из контекста
        user_id=message.from_user.id,
        limit=20  # Максимум результатов для лексического поиска
    )
    
    if not search_results:
        await message.answer(
            f"По запросу '{esc(query)}' ничего не найдено.\n"
            "Попробуйте другой запрос или воспользуйтесь меню каталога.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
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
                    text="⬅️ Главное меню",
                    callback_data="menu:main"
                )
            ]])
        )
        return
    
    # Создаем список кнопок с найденными продуктами
    buttons = []
    for product in search_results[:10]:  # Показываем до 10 результатов
        # Получаем название продукта и преобразуем в строку
        product_name = str(product.name) if product.name is not None else "Без названия"
        # Показываем полное название без сокращений
        buttons.append([
            types.InlineKeyboardButton(
                text=f"{product_name}",
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
    result_text = f"<b>Результаты поиска по запросу:</b> {esc(query)}\n\n"
    
    # Добавляем информацию о типе поиска, если был использован семантический
    if len(search_results) <= 3:  # Признак семантического поиска
        result_text += "💡 <i>Показаны наиболее релевантные результаты</i>\n\n"
    
    result_text += "Выберите продукт для просмотра подробной информации:"
    
    await message.answer(
        result_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(lambda c: c.data == 'search:new')
async def new_search(callback: types.CallbackQuery, state: FSMContext):
    """
    Новый запрос на поиск.
    
    Перевод бота в состояние ожидания нового запроса.
    Демонстрация инструкции для ввода запроса.
    """
    # Устанавливаем состояние ожидания поискового запроса
    await state.set_state(SearchProduct.waiting_query)
    
    if callback.message and isinstance(callback.message, types.Message):
        try:
            await callback.message.edit_text(
                "<b>🔍 Поиск продуктов</b>\n\n"
                "Введите название продукта или его часть для поиска:",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ В главное меню",
                        callback_data="menu:main"
                    )
                ]])
            )
        except Exception:
            await callback.answer()
            await callback.message.delete()
            await callback.message.answer(
                "<b>🔍 Поиск продуктов</b>\n\n"
                "Введите название продукта или его часть для поиска:",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ В главное меню",
                        callback_data="menu:main"
                    )
                ]])
            )
            return
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('search:back:'))
async def back_to_search_results(callback: types.CallbackQuery, session: AsyncSession):
    """
    Обработчик кнопки "Назад к результатам поиска".
    Возвращает пользователя к результатам поиска по исходному запросу.
    """
    if not callback.data:
        return
    
    query = callback.data.split(':', 2)[2]
    if not query:
        await callback.answer("Поисковый запрос пуст")
        return
    
    # Создаем сервисы для поиска
    search_service = await _create_hybrid_search_service(session)
    
    # Выполняем поиск
    search_results = await search_service.find_products_by_query(
        query=query,
        category_id=None,
        user_id=callback.from_user.id,
        limit=20
    )
    
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
                text="В главное меню", 
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
    for product in search_results[:10]:  # Показываем до 10 результатов
        # Получаем название продукта и преобразуем в строку
        product_name = str(product.name) if product.name is not None else "Без названия"
        # Показываем полное название без сокращений
        buttons.append([
            types.InlineKeyboardButton(
                text=f"{product_name}",
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
    result_text = f"<b>Результаты поиска по запросу:</b> {esc(query)}\n\n"
    
    # Добавляем информацию о типе поиска, если был использован семантический
    if len(search_results) <= 3:  # Признак семантического поиска
        result_text += "💡 <i>Показаны наиболее релевантные результаты</i>\n\n"
    
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


async def _create_hybrid_search_service(session: AsyncSession) -> HybridSearchService:
    """
    Создает и возвращает настроенный гибридный поисковый сервис.
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Настроенный экземпляр HybridSearchService
    """
    # Создаем гибридный поиск (он теперь сам инициализирует все необходимые сервисы)
    hybrid_search = HybridSearchService(session)
    
    # Инициализируем embedding service для семантического поиска
    await hybrid_search.vector_search.embedding_service.initialize()
    
    return hybrid_search

