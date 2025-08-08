import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from src.services.rag import RagService
from src.handlers.states import AskAI
from src.keyboards.user import get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляр RAG-сервиса
rag_service = RagService()

@router.message(AskAI.waiting_question)
async def handle_ai_question(message: Message, state: FSMContext):
    """Обработчик вопросов к AI для всех пользователей."""
    if not message.text:
        await message.answer("Пожалуйста, задайте вопрос текстом.")
        return
    
    query_text = message.text.strip()
    
    # Отправляем сообщение о начале обработки запроса
    processing_msg = await message.answer(
        f"🤖 Обрабатываю ваш вопрос: \n\"{query_text}\"\n"
        "Ищу информацию в базе знаний и формирую ответ..."
    )
    
    try:
        # Инициализируем RAG-сервис если еще не инициализирован
        await rag_service.initialize()
        
        # Выполняем поиск и генерацию ответа
        result = await rag_service.search_and_answer(
            query=query_text,
            top_k=8,  # Больше документов для лучшего контекста
            threshold=0.25,  # Снижаем порог для включения больше документов
            generate_answer=True
        )
        
        # Формируем ответ
        if isinstance(result, dict):
            llm_answer = result.get("llm_answer")
#            search_results = result.get("search_results", [])
            execution_time = result.get("execution_time", 0)
            
            if llm_answer:
                # Редактируем сообщение о загрузке на уведомление о завершении
                await processing_msg.edit_text(
                    f"✅ Обработка завершена за {execution_time:.1f} сек."
                )
                
                # Отправляем ответ от AI отдельным сообщением
                response_text = f"🤖 <b>Ответ AI</b>:\n\n{llm_answer}"
                
                # Добавляем информацию об источниках, если есть
                # if search_results:
                #     response_text += f"\n\n📚 <b>Основано на {len(search_results)} документе(ах):</b> \n"
                #     for i, doc in enumerate(search_results[:3], 1):  # Показываем только топ-3
                #         product_name = doc.get("product_name", f"Документ {i}")
                #         similarity = doc.get("similarity", 0)
                #         response_text += f"• {product_name} (релевантность: {similarity:.0%})\n"
                
                # Отправляем ответ с кнопкой возврата в главное меню
                await message.answer(
                    response_text,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
            else:
                # Редактируем сообщение о загрузке на ошибку
                await processing_msg.edit_text("❌ Обработка завершена с ошибкой")
                
                await message.answer(
                    "❌ Не удалось сгенерировать ответ на ваш вопрос. "
                    "Попробуйте переформулировать запрос или обратитесь к каталогу продукции.",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            # Редактируем сообщение о загрузке на ошибку
            await processing_msg.edit_text("❌ Обработка завершена с ошибкой")
            
            await message.answer(
                "❌ Произошла ошибка при обработке запроса.",
                reply_markup=get_main_menu_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке AI-вопроса: {e}")
        
        # Редактируем сообщение о загрузке на ошибку
        try:
            await processing_msg.edit_text("❌ Обработка завершена с ошибкой")
        except:
            pass  # Игнорируем ошибки редактирования
            
        await message.answer(
            f"❌ Произошла ошибка при обработке вашего вопроса: {str(e)}\n"
            "Попробуйте позже или воспользуйтесь поиском по каталогу.",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()
