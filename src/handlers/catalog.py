from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram import F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.product_service import ProductService
from src.services.category_service import CategoryService
from src.services.sphere_service import SphereService
from src.keyboards.user import get_main_menu_keyboard
from src.core.utils import esc, truncate_caption, fix_html_tags
router = Router()

"""
Логика каталогов по продукции:
- по категориям
- по сфере применения
"""

@router.callback_query(lambda c: c.data == 'menu:catalog')
async def catalog_menu(callback: types.CallbackQuery):
    """
    Показывает выбор между категориями или сферами
    """
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="📂 По сферам применения",
            callback_data="catalog:spheres"
        )],
        [types.InlineKeyboardButton(
            text="📂 По категориям продукции",
            callback_data="catalog:categories"
        )],
        [types.InlineKeyboardButton(
            text="⬅️ Главное меню",
            callback_data="menu:main"
        )]
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое текстовое сообщение
                await callback.message.answer(
                    "<b>📂 Каталог продукции</b>\n\n"
                    "Выберите способ просмотра каталога:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    "<b>📂 Каталог продукции</b>\n\n"
                    "Выберите способ просмотра каталога:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
                "<b>📂 Каталог продукции</b>\n\n"
                "Выберите способ просмотра каталога:",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    await callback.answer()


@router.callback_query(lambda c: c.data == 'catalog:categories')
async def show_categories(callback: types.CallbackQuery, session: AsyncSession):
    """
    - Извлечение id категории из callback_data, 
    - полуечение всех продуктов из категории
    """
    category_service = CategoryService(session)
    categories = await category_service.get_all_categories()

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for category in categories:
        button = types.InlineKeyboardButton(
            text=str(category.name),  # Преобразуем в строку
            callback_data=f"category:{category.id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="menu:catalog"
        )
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое текстовое сообщение
                await callback.message.answer(
                    "<b>📂 Категории продукции:</b>\n\n"
                    "Выберите категорию:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    "<b>📂 Категории продукции:</b>\n\n"
                    "Выберите категорию:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
                "<b>📂 Категории продукции:</b>\n\n"
                "Выберите категорию:",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    await callback.answer()

@router.callback_query(lambda c: c.data == 'catalog:spheres')
async def show_spheres(callback: types.CallbackQuery, session: AsyncSession):
    """
    - Извлечение id сферы из callback_data, 
    - полуечение всех продуктов из сферы
    """
    sphere_service = SphereService(session)
    spheres = await sphere_service.get_all_spheres()

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for sphere in spheres:
        button = types.InlineKeyboardButton(
            text=str(sphere.name),  # Преобразуем в строку
            callback_data=f"sphere:{sphere.id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="menu:catalog"
        )
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое текстовое сообщение
                await callback.message.answer(
                    "<b>📂 Сферы применения:</b>\n\n"
                    "Выберите сферу применения:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    "<b>📂 Сферы применения:</b>\n\n"
                    "Выберите сферу применения:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
                "<b>📂 Сферы применения:</b>\n\n"
                "Выберите сферу применения:",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith('category:'))
async def show_category_products(callback: types.CallbackQuery, session: AsyncSession):
    """
    Показать список продуктов из выбранной категории
    """
    if not callback.data:
        return
        
    category_id = int(callback.data.split(':')[1])

    product_service = ProductService(session)
    products = await product_service.get_products_by_category(category_id)

    if not products:
        if callback.message and isinstance(callback.message, Message):
            try:
                # Проверяем, есть ли медиа в сообщении
                if callback.message.photo or callback.message.document or callback.message.video:
                    # Для сообщений с медиа отправляем новое текстовое сообщение
                    await callback.message.answer(
                        "В этой категории пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад",
                                callback_data="catalog:categories"
                            )
                        ]])
                    )
                else:
                    # Для текстовых сообщений используем edit_text
                    await callback.message.edit_text(
                        "В этой категории пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад",
                                callback_data="catalog:categories"
                            )
                        ]])
                    )
            except Exception as e:
                # В случае ошибки отправляем новое сообщение
                await callback.message.answer(
                    "В этой категории пока нет продуктов.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="catalog:categories"
                        )
                    ]])
                )
        await callback.answer()
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for product in products:
        # product теперь это словарь, а не кортеж
        button = types.InlineKeyboardButton(
            text=f"{str(product['name'])}",  
            callback_data=f"product:{product['id']}:category:{category_id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="catalog:categories"
        )
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое сообщение
                await callback.message.answer(
                    "Выберите продукт:",
                    reply_markup=keyboard
                )
                # По возможности удаляем предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass  # Игнорируем ошибку, если не удалось удалить сообщение
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    "Выберите продукт:",
                    reply_markup=keyboard
                )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
                "Выберите продукт:",
                reply_markup=keyboard
            )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('product:'))
async def show_product_details(callback: types.CallbackQuery, session: AsyncSession):
    """
    Парсинг callback_data для определения источника
    Получение полной информации о продукте
    Форматирование сообщения в HTML разметку
    Добавление кнопки документов
    Кнопка назад, в зависимости от источника
    """    
    if not callback.data:
        return
    
    # Разбираем callback_data для определения источника перехода
    data_parts = callback.data.split(':')
    product_id = int(data_parts[1])
    
    # Проверяем, пришли ли мы из поиска
    from_search = len(data_parts) >= 3 and data_parts[2] == 'search'
    search_query = data_parts[3] if from_search and len(data_parts) >= 4 else None
    
    # Проверяем, пришли ли мы из категории
    from_category = len(data_parts) >= 3 and data_parts[2] == 'category'
    category_id = int(data_parts[3]) if from_category and len(data_parts) >= 4 else None
    
    # Проверяем, пришли ли мы из сферы
    from_sphere = len(data_parts) >= 3 and data_parts[2] == 'sphere'
    sphere_id = int(data_parts[3]) if from_sphere and len(data_parts) >= 4 else None

    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)

    if not product_info:
        if callback.message and isinstance(callback.message, Message):
            # Определяем куда вернуться в зависимости от источника
            navigation_buttons = []
            
            if from_search and search_query:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"search:back:{search_query}"
                )
            elif from_category and category_id is not None:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"back_to_catalog:category:{category_id}"
                )
            elif from_sphere and sphere_id is not None:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"sphere:{sphere_id}"
                )
            else:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="catalog:categories"
                )
            
            navigation_buttons.append(back_button)
            
            # Добавляем кнопку "Главное меню"
            main_menu_button = types.InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="menu:main"
            )
            navigation_buttons.append(main_menu_button)
            
            await callback.message.edit_text(
                "❌ Продукт с данным ID не найден или удален.\n\nПопробуйте ввести другой ID:",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[navigation_buttons])
            )
        await callback.answer()
        return
    
    text = f"<b>{esc(product_info['name'])}</b>\n"
    text += f"<b>ID:</b> {product_info['id']}\n\n"
    
    # Категория (обязательное поле)
    category_name = "Не указана"
    if product_info.get('category'):
        category_name = str(product_info['category'])
    text += f"<b>Категория:</b> {esc(category_name)}\n\n"
    
    # Сфера применения (обязательное поле)
    spheres_text = "Не указана"
    if product_info.get("spheres"):
        spheres_names = []
        for sphere in product_info["spheres"]:
            if sphere.get('name'):
                spheres_names.append(sphere['name'])
        if spheres_names:
            spheres_text = ', '.join(spheres_names)
    text += f"<b>Сфера применения:</b> {esc(spheres_text)}\n\n"
    
    # Описание и преимущества из сфер применения
    if product_info.get("spheres_info"):
        for sphere in product_info["spheres_info"]:
            # Описание
            description = sphere.get("description")
            if description and description.strip() and description.lower() not in ['-', 'null']:
                text += f"<b>Описание:</b>\n{esc(description)}\n\n"
                break  # Берем описание только из первой сферы
    
    if product_info.get("spheres_info"):
        for sphere in product_info["spheres_info"]:
            # Преимущества
            advantages = sphere.get("advantages")
            if advantages and advantages.strip() and advantages.lower() not in ['-', 'null']:
                if "<b>Преимущества:</b>" not in text:  # Добавляем проверку, чтобы не добавлять повторно
                    from src.core.utils import format_advantages_for_telegram
                    formatted_advantages = format_advantages_for_telegram(advantages)
                    if formatted_advantages:
                        text += f"<b>Преимущества:</b>\n{formatted_advantages}\n\n"
                break  # Берем преимущества только из первой сферы
    
    # Отдельный цикл для расхода
    if product_info.get("spheres_info"):
        for sphere in product_info["spheres_info"]:
            # Расход = примечания
            notes = sphere.get("notes")
            if notes and str(notes).strip() and str(notes).strip() not in ['-','нет', 'null']:
                text += f"<b>Расход:</b>\n{esc(str(notes))}\n\n"
                break  # Берем расход только из первой сферы
    
    # Проверяем и исправляем HTML теги перед отправкой
    text = fix_html_tags(text)
    
    # Инициализируем клавиатуру всегда
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    # Проверяем есть ли файлы у продукта (документы или медиа)
    has_files = False
    if product_info.get("all_files"):
        has_files = len(product_info["all_files"]) > 0
    
    if has_files:
        content_button = types.InlineKeyboardButton(
            text="📄 Документация и Медиа",
            callback_data=f"show_content:{product_id}"
        )
        keyboard.inline_keyboard.append([content_button])

    # Кнопки навигации
    navigation_buttons = []
    
    # Определяем кнопку возврата в зависимости от источника
    if from_search and search_query:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"search:back:{search_query}"
        )
    elif from_category and category_id is not None:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"back_to_catalog:category:{category_id}"
        )
    elif from_sphere and sphere_id is not None:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"sphere:{sphere_id}"
        )
    else:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="menu:catalog"
        )
    
    navigation_buttons.append(back_button)
    
    # Добавляем кнопку "Главное меню"
    main_menu_button = types.InlineKeyboardButton(
        text="🏠 Главное меню",
        callback_data="menu:main"
    )
    navigation_buttons.append(main_menu_button)
    
    keyboard.inline_keyboard.append(navigation_buttons)

    # Проверяем и исправляем HTML теги перед отправкой
    text = fix_html_tags(text)

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в текущем сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Если есть медиа и у продукта есть главное изображение - редактируем медиа
                if product_info.get("main_image"):
                    if len(text) > 1024:
                        # Создаем краткое описание для caption (только основная информация)
                        short_caption = f"<b>{esc(product_info['name'])}</b>\n"
                        short_caption += f"<b>ID:</b> {product_info['id']}\n\n"
                        
                        # Категория
                        category_name = "Не указана"
                        if product_info.get('category'):
                            category_name = str(product_info['category'])
                        short_caption += f"<b>Категория:</b> {esc(category_name)}\n"
                        
                        # Сфера применения
                        spheres_text = "Не указана"
                        if product_info.get("spheres"):
                            spheres_names = []
                            for sphere in product_info["spheres"]:
                                if sphere.get('name'):
                                    spheres_names.append(sphere['name'])
                            if spheres_names:
                                spheres_text = ', '.join(spheres_names)
                        short_caption += f"<b>Сфера применения:</b> {esc(spheres_text)}"
                        
                        short_caption = fix_html_tags(short_caption)
                        
                        # Редактируем медиа с кратким описанием
                        await callback.message.edit_media(
                            types.InputMediaPhoto(
                                media=product_info["main_image"],
                                caption=short_caption,
                                parse_mode="HTML"
                            ),
                            reply_markup=keyboard
                        )
                        
                        # Отправляем полную информацию отдельным сообщением
                        await callback.message.answer(
                            text,
                            parse_mode="HTML"
                        )
                    else:
                        # Для коротких текстов редактируем медиа с полной информацией
                        await callback.message.edit_media(
                            types.InputMediaPhoto(
                                media=product_info["main_image"],
                                caption=text,
                                parse_mode="HTML"
                            ),
                            reply_markup=keyboard
                        )
                else:
                    # Если у продукта нет изображения, но в сообщении есть медиа - отправляем новое текстовое сообщение
                    await callback.message.answer(
                        text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
            else:
                # Если в сообщении нет медиа
                if product_info.get("main_image"):
                    # Если у продукта есть изображение - отправляем новое сообщение с медиа
                    if len(text) > 1024:
                        # Создаем краткое описание для caption
                        short_caption = f"<b>{esc(product_info['name'])}</b>\n"
                        short_caption += f"<b>ID:</b> {product_info['id']}\n\n"
                        
                        # Категория
                        category_name = "Не указана"
                        if product_info.get('category'):
                            category_name = str(product_info['category'])
                        short_caption += f"<b>Категория:</b> {esc(category_name)}\n"
                        
                        # Сфера применения
                        spheres_text = "Не указана"
                        if product_info.get("spheres"):
                            spheres_names = []
                            for sphere in product_info["spheres"]:
                                if sphere.get('name'):
                                    spheres_names.append(sphere['name'])
                            if spheres_names:
                                spheres_text = ', '.join(spheres_names)
                        short_caption += f"<b>Сфера применения:</b> {esc(spheres_text)}"
                        
                        short_caption = fix_html_tags(short_caption)
                        
                        # Отправляем картинку с кратким описанием
                        await callback.message.answer_photo(
                            photo=product_info["main_image"],
                            caption=short_caption,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                        
                        # Отправляем полную информацию отдельным сообщением
                        await callback.message.answer(
                            text,
                            parse_mode="HTML"
                        )
                    else:
                        # Для коротких текстов отправляем одно сообщение с полной информацией
                        await callback.message.answer_photo(
                            photo=product_info["main_image"],
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                else:
                    # Если у продукта нет изображения - отправляем новое текстовое сообщение
                    await callback.message.answer(
                        text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            if product_info.get("main_image"):
                await callback.message.answer_photo(
                    photo=product_info["main_image"],
                    caption=text if len(text) <= 1024 else f"<b>{esc(product_info['name'])}</b>\n<b>ID:</b> {product_info['id']}",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                if len(text) > 1024:
                    await callback.message.answer(text, parse_mode="HTML")
            else:
                await callback.message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
    
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith('back_to_catalog:category:'))
async def back_to_category_catalog(callback: types.CallbackQuery, session: AsyncSession):
    """
    Возврат к каталогу категории с отправкой нового сообщения (как в сферах)
    """
    if not callback.data:
        return
        
    category_id = int(callback.data.split(':')[2])

    product_service = ProductService(session)
    products = await product_service.get_products_by_category(category_id)

    if not products:
        if callback.message:
            await callback.message.answer(
                "В этой категории пока нет продуктов.",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="catalog:categories"
                    )
                ]])
            )
        await callback.answer()
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for product in products:
        # product теперь это словарь, а не кортеж
        button = types.InlineKeyboardButton(
            text=f"{str(product['name'])}",
            callback_data=f"product:{product['id']}:category:{category_id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="catalog:categories"
        )
    ])

    # Всегда отправляем новое сообщение (как в сферах)
    if callback.message:
        await callback.message.answer(
            "Выберите продукт:",
            reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('sphere:'))
async def show_sphere_products(callback: types.CallbackQuery, session: AsyncSession):
    """
    Показать карточку продукта из списка продукции по сферам
    """
    if not callback.data:
        return
        
    sphere_id = int(callback.data.split(':')[1])

    sphere_service = SphereService(session)
    products = await sphere_service.get_products_by_sphere(sphere_id)

    if not products:
        if callback.message and isinstance(callback.message, Message):
            try:
                # Проверяем, есть ли медиа в сообщении
                if callback.message.photo or callback.message.document or callback.message.video:
                    # Для сообщений с медиа отправляем новое текстовое сообщение
                    await callback.message.answer(
                        "В этой сфере применения пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад",
                                callback_data="catalog:spheres"
                            )
                        ]])
                    )
                else:
                    # Для текстовых сообщений используем edit_text
                    await callback.message.edit_text(
                        "В этой сфере применения пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад",
                                callback_data="catalog:spheres"
                            )
                        ]])
                    )
            except Exception as e:
                # В случае ошибки отправляем новое сообщение
                await callback.message.answer(
                    "В этой сфере применения пока нет продуктов.",
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="⬅️ Назад",
                            callback_data="catalog:spheres"
                        )
                    ]])
                )
        await callback.answer()
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for product, _ in products:
        button = types.InlineKeyboardButton(
            text=f"{str(product.name)}",  
            callback_data=f"product:{product.id}:sphere:{sphere_id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="catalog:spheres"
        )
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое текстовое сообщение
                await callback.message.answer(
                    "Выберите продукт:",
                    reply_markup=keyboard
                )
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    "Выберите продукт:",
                    reply_markup=keyboard
                )
        except Exception as e:
            # В случае ошибки отправляем новое сообщение
            await callback.message.answer(
                "Выберите продукт:",
                reply_markup=keyboard
            )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('hide_content:'))
async def hide_product_content(callback: types.CallbackQuery, session: AsyncSession):
    """
    Скрыть файлы продукта - возвращается к карточке продукта
    """
    if not callback.data:
        return
        
    product_id = int(callback.data.split(':')[1])
    
    # Просто отвечаем что файлы скрыты
    await callback.answer("Файлы остаются доступны выше ⬆️")


@router.callback_query(lambda c: c.data and c.data.startswith('show_content:'))
async def show_product_content(callback: types.CallbackQuery, session: AsyncSession):
    """
    Показать файлы продукта (документы и медиа отдельными сообщениями)
    """
    if not callback.data:
        return
        
    product_id = int(callback.data.split(':')[1])
    
    product_service = ProductService(session)
    product_info = await product_service.get_product_by_id(product_id)
    
    if not product_info:
        await callback.answer("Продукт не найден", show_alert=True)
        return
    
    documents = product_info.get("documents", [])
    media_files = product_info.get("media_files", [])
    
    # Проверяем, есть ли вообще файлы
    if not documents and not media_files:
        await callback.message.answer(
            f"📂 <b>Файлы для {esc(product_info['name'])}</b>\n\n"
            "У этого продукта пока нет файлов.",
            parse_mode="HTML"
        ) if callback.message else None
        await callback.answer()
        return
    
    # Отправляем документы ТОЛЬКО если они есть
    if documents:
        doc_text = f"📄 <b>Документы для {esc(product_info['name'])}</b>\n\n"
        
        doc_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        
        for doc in documents:
            doc_title = doc.title if doc.title else "Документ"
            button = types.InlineKeyboardButton(
                text=f"📄 {doc_title}",
                callback_data=f"file:{doc.id}"
            )
            doc_keyboard.inline_keyboard.append([button])
        
        await callback.message.answer(
            doc_text,
            parse_mode="HTML",
            reply_markup=doc_keyboard
        ) if callback.message else None
    
    # Отправляем медиа файлы ТОЛЬКО если они есть
    if media_files:
        media_text = f"🖼️ <b>Медиа для {esc(product_info['name'])}</b>\n\n"
        
        media_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        
        for media in media_files:
            media_title = media.title if media.title else "Медиа файл"
            # Определяем иконку по типу файла
            if media.kind == 'image':
                icon = "📷"
            elif media.kind == 'video':
                icon = "🎥"
            else:
                icon = "🖼️"
            
            button = types.InlineKeyboardButton(
                text=f"{icon} {media_title}",
                callback_data=f"file:{media.id}"
            )
            media_keyboard.inline_keyboard.append([button])
        
        await callback.message.answer(
            media_text,
            parse_mode="HTML",
            reply_markup=media_keyboard
        ) if callback.message else None
    
    await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith('file:'))
async def send_file(callback: types.CallbackQuery, session: AsyncSession):
    """
    Отправить файл пользователю
    """
    if not callback.data:
        return
        
    file_record_id = int(callback.data.split(':')[1])
    
    try:
        # Получаем запись файла из БД
        from sqlalchemy import select
        from src.database.models import ProductFile
        
        result = await session.execute(
            select(ProductFile).where(ProductFile.id == file_record_id, ProductFile.is_deleted == False)
        )
        file_record = result.scalars().first()
        
        if not file_record:
            await callback.answer("Файл не найден", show_alert=True)
            return
        
        # Отправляем файл пользователю без кнопок навигации
        if callback.message and file_record:
            file_kind = str(file_record.kind)
            file_id = str(file_record.file_id)
            
            # Все файлы отправляем без кнопок навигации
            if file_kind == 'image':
                await callback.message.answer_photo(photo=file_id)
            elif file_kind == 'video':
                await callback.message.answer_video(video=file_id)
            else:
                await callback.message.answer_document(document=file_id)
        
        await callback.answer("Файл отправлен")
    except Exception as e:
        await callback.answer("Ошибка при отправке файла", show_alert=True)