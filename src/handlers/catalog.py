from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram import F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.product_service import CategoryService, ProductService, SphereService
from src.keyboards.user import get_main_menu_keyboard
from src.core.utils import esc

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

    try:
        if callback.message and isinstance(callback.message, Message):
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое сообщение
                await callback.message.answer(
                    "<b>📂 Каталог продукции</b>\n\n"
                    "Выберите способ просмотра каталога:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                # По возможности удаляем предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass  # Игнорируем ошибку, если не удалось удалить сообщение
            else:
                # Для текстовых сообщений используем edit_text
                await callback.message.edit_text(
                    "<b>📂 Каталог продукции</b>\n\n"
                    "Выберите способ просмотра каталога:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
    except Exception:
        # Если не удается редактировать, отправляем новое
        if callback.message and isinstance(callback.message, Message) and callback.bot:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.bot.send_message(
                chat_id=callback.message.chat.id,
                text="<b>📂 Каталог продукции</b>\n\n"
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
            text="⬅️ Назад к выбору каталога",
            callback_data="menu:catalog"
        )
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое сообщение
                await callback.message.answer(
                    "<b>📂 Категории продукции:</b>\n\n"
                    "Выберите категорию:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                # По возможности удаляем предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass  # Игнорируем ошибку, если не удалось удалить сообщение
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
            text="⬅️ Назад к выбору каталога",
            callback_data="menu:catalog"
        )
    ])

    if callback.message and isinstance(callback.message, Message):
        try:
            # Проверяем, есть ли медиа в сообщении
            if callback.message.photo or callback.message.document or callback.message.video:
                # Для сообщений с медиа отправляем новое сообщение
                await callback.message.answer(
                    "<b>📂 Сферы применения:</b>\n\n"
                    "Выберите сферу применения:",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                # По возможности удаляем предыдущее сообщение
                try:
                    await callback.message.delete()
                except Exception:
                    pass  # Игнорируем ошибку, если не удалось удалить сообщение
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
                    # Для сообщений с медиа отправляем новое сообщение
                    await callback.message.answer(
                        "В этой категории пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад к категориям",
                                callback_data="catalog:categories"
                            )
                        ]])
                    )
                    # По возможности удаляем предыдущее сообщение
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass  # Игнорируем ошибку, если не удалось удалить сообщение
                else:
                    # Для текстовых сообщений используем edit_text
                    await callback.message.edit_text(
                        "В этой категории пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад к категориям",
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
                            text="⬅️ Назад к категориям",
                            callback_data="catalog:categories"
                        )
                    ]])
                )
        await callback.answer()
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for product, _ in products:
        button = types.InlineKeyboardButton(
            text=f"ID: {product.id} | {str(product.name)}",  # Добавляем ID к названию
            callback_data=f"product:{product.id}:category:{category_id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад к категориям",
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
                    text="⬅️ Назад к результатам поиска",
                    callback_data=f"search:back:{search_query}"
                )
            elif from_category and category_id is not None:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад к категории",
                    callback_data=f"category:{category_id}"
                )
            elif from_sphere and sphere_id is not None:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад к сфере",
                    callback_data=f"sphere:{sphere_id}"
                )
            else:
                back_button = types.InlineKeyboardButton(
                    text="⬅️ Назад к категориям",
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
                "Продукт не найден или удален.",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[navigation_buttons])
            )
        await callback.answer()
        return
    
    text = f"<b>{esc(product_info['name'])}</b>\n"
    text += f"<b>ID:</b> {product_info['id']}\n\n"
    
    # Категория (обязательное поле)
    category_name = "Не указана"
    if product_info.get('category'):
        category_name = str(product_info['category'].name)
    text += f"<b>Категория:</b> {esc(category_name)}\n"
    
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
    
    # Описание
    description = product_info.get('description')
    if description is not None:
        description = str(description).strip()
        if description and description != '-' and description.lower() != 'null':
            text += f"<b>Описание:</b>\n{esc(description)}\n\n"

    # Преимущества, расход и упаковка из сфер применения
    if product_info.get("spheres"):
        for sphere in product_info["spheres"]:
            # Преимущества
            if sphere.get("advantages"):
                text += "<b>Преимущества:</b>\n"
                for adv in sphere["advantages"]:
                    if adv and str(adv).strip():  # Проверяем что преимущество не пустое
                        text += f"• {esc(str(adv))}\n"
                text += "\n"
            
            # Расход = примечания
            notes = sphere.get("notes")
            if notes is not None and str(notes).strip():
                text += f"<b>Расход:</b>\n{esc(str(notes))}\n\n"
            
            # Упаковка
            package = sphere.get("package")
            if package is not None and str(package).strip():
                text += f"<b>Упаковка:</b>\n{esc(str(package))}\n\n"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    # Проверяем есть ли файлы у продукта (документы или медиа)
    has_files = False
    if product_info.get("all_files"):
        has_files = len(product_info["all_files"]) > 0
    
    if has_files:
        content_button = types.InlineKeyboardButton(
            text="📄 Показать доступные файлы",
            callback_data=f"show_content:{product_id}"
        )
        keyboard.inline_keyboard.append([content_button])

    # Кнопки навигации
    navigation_buttons = []
    
    # Определяем кнопку возврата в зависимости от источника
    if from_search and search_query:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад к результатам поиска",
            callback_data=f"search:back:{search_query}"
        )
    elif from_category and category_id is not None:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад к категории",
            callback_data=f"category:{category_id}"
        )
    elif from_sphere and sphere_id is not None:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад к сфере применения",
            callback_data=f"sphere:{sphere_id}"
        )
    else:
        back_button = types.InlineKeyboardButton(
            text="⬅️ Назад к каталогу",
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

    if product_info.get("main_image"):
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_media(
                types.InputMediaPhoto(
                    media=product_info["main_image"],
                    caption=text,
                    parse_mode="HTML"
                ),
                reply_markup=keyboard
            )
    else:
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
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
                    # Для сообщений с медиа отправляем новое сообщение
                    await callback.message.answer(
                        "В этой сфере применения пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад к сферам",
                                callback_data="catalog:spheres"
                            )
                        ]])
                    )
                    # По возможности удаляем предыдущее сообщение
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass  # Игнорируем ошибку, если не удалось удалить сообщение
                else:
                    # Для текстовых сообщений используем edit_text
                    await callback.message.edit_text(
                        "В этой сфере применения пока нет продуктов.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="⬅️ Назад к сферам",
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
                            text="⬅️ Назад к сферам",
                            callback_data="catalog:spheres"
                        )
                    ]])
                )
        await callback.answer()
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

    for product, _ in products:
        button = types.InlineKeyboardButton(
            text=f"ID: {product.id} | {str(product.name)}",  # Добавляем ID к названию
            callback_data=f"product:{product.id}:sphere:{sphere_id}"
        )
        keyboard.inline_keyboard.append([button])
    
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(
            text="⬅️ Назад к сферам",
            callback_data="catalog:spheres"
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
    
    # Создаём кнопки возврата
    back_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[
        types.InlineKeyboardButton(
            text="⬅️ Назад к карточке продукта",
            callback_data=f"product:{product_id}"
        ),
        types.InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="menu:main"
        )
    ]])
    
    # Отправляем документы
    if documents:
        doc_text = f"📄 <b>Документы для {esc(product_info['name'])}</b>\n\n"
        
        doc_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        
        for doc in documents:
            doc_title = doc.title if doc.title else "Документ"
            button = types.InlineKeyboardButton(
                text=f"{doc_title}",
                callback_data=f"file:{doc.id}"
            )
            doc_keyboard.inline_keyboard.append([button])
        
        # Добавляем кнопки возврата
        doc_keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(
                text="⬅️ Назад к карточке продукта",
                callback_data=f"product:{product_id}"
            ),
            types.InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="menu:main"
            )
        ])
        
        await callback.message.answer(
            doc_text,
            parse_mode="HTML",
            reply_markup=doc_keyboard
        ) if callback.message else None
    else:
        await callback.message.answer(
            f"📄 <b>Документы для {esc(product_info['name'])}</b>\n\n"
            "Документы не найдены.",
            parse_mode="HTML",
            reply_markup=back_keyboard
        ) if callback.message else None
    
    # Отправляем медиа файлы
    if media_files:
        media_text = f"🖼️ <b>Медиа для {esc(product_info['name'])}</b>\n\n"
        
        media_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        
        for media in media_files:
            media_title = media.title if media.title else "Медиа файл"
            # Определяем иконку по типу файла
            if media.kind == 'image':
                icon = "📷️"
            elif media.kind == 'video':
                icon = "🎥"
            else:
                icon = "🖼️"
                
            button = types.InlineKeyboardButton(
                text=f"{icon} {media_title}",
                callback_data=f"file:{media.id}"
            )
            media_keyboard.inline_keyboard.append([button])
        
        # Добавляем кнопки возврата
        media_keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(
                text="⬅️ Назад к карточке продукта",
                callback_data=f"product:{product_id}"
            ),
            types.InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="menu:main"
            )
        ])
        
        await callback.message.answer(
            media_text,
            parse_mode="HTML",
            reply_markup=media_keyboard
        ) if callback.message else None
    else:
        await callback.message.answer(
            f"🖼 <b>Медиа для {esc(product_info['name'])}</b>\n\n"
            "Медиа файлы не найдены.",
            parse_mode="HTML",
            reply_markup=back_keyboard
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
        
        # Отправляем файл пользователю
        if callback.message and file_record:
            file_kind = str(file_record.kind)
            file_id = str(file_record.file_id)
            
            if file_kind == 'image':
                await callback.message.answer_photo(photo=file_id)
            elif file_kind == 'video':
                await callback.message.answer_video(video=file_id)
            else:
                await callback.message.answer_document(document=file_id)
        
        await callback.answer("Файл отправлен")
    except Exception as e:
        await callback.answer("Ошибка при отправке файла", show_alert=True)