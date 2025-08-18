import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.feedback_service import FeedbackService
from src.keyboards.user import get_feedback_submitted_keyboard
from src.handlers.states import FeedbackState

logger = logging.getLogger(__name__)
router = Router()

"""
Обработчики для сбора обратной связи пользователей.
Только пользовательские функции - без админской панели.
"""


@router.callback_query(F.data.startswith('feedback:like:'))
async def handle_positive_feedback(callback: types.CallbackQuery, session: AsyncSession):
    """Обработка положительной обратной связи."""
    if not callback.data:
        await callback.answer("Ошибка обработки данных")
        return
    
    try:
        _, _, message_id_str = callback.data.split(':', 2)
        message_id = int(message_id_str)
        
        feedback_service = FeedbackService(session)
        
        if not callback.from_user:
            await callback.answer("Ошибка определения пользователя")
            return
        
        # Проверяем, есть ли уже feedback от этого пользователя
        existing_feedback = await feedback_service.get_user_feedback_for_message(
            message_id=message_id,
            user_id=callback.from_user.id
        )
        
        if existing_feedback:
            await callback.answer("✅ Вы уже оставили отзыв на этот ответ", show_alert=True)
            return
        
        # Добавляем положительный feedback
        feedback = await feedback_service.add_user_feedback(
            message_id=message_id,
            user_id=callback.from_user.id,
            feedback_type='like'
        )
        
        if feedback:
            # Отправляем новое сообщение с благодарностью (не изменяем ответ AI)
            thank_you_text = (
                "✅ <b>Спасибо за ваш отзыв!</b>\n\n"
                "Ваша оценка поможет нам улучшить качество ответов AI.\n"
                "Чем еще могу помочь?"
            )
            
            # Всегда отправляем новое сообщение, чтобы не изменять ответ AI
            if callback.message:
                await callback.message.answer(
                    thank_you_text,
                    reply_markup=get_feedback_submitted_keyboard(),
                    parse_mode="HTML"
                )
            
            await callback.answer("👍 Спасибо за положительную оценку!")
        else:
            await callback.answer("❌ Не удалось сохранить отзыв", show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке положительного feedback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith('feedback:dislike:'))
async def handle_negative_feedback(callback: types.CallbackQuery, session: AsyncSession):
    """Обработка отрицательной обратной связи - сразу сохраняем дизлайк."""
    if not callback.data:
        await callback.answer("Ошибка обработки данных")
        return
    
    try:
        _, _, message_id_str = callback.data.split(':', 2)
        message_id = int(message_id_str)
        
        feedback_service = FeedbackService(session)
        
        if not callback.from_user:
            await callback.answer("Ошибка определения пользователя")
            return
            
        # Проверяем, есть ли уже feedback от этого пользователя
        existing_feedback = await feedback_service.get_user_feedback_for_message(
            message_id=message_id,
            user_id=callback.from_user.id
        )
        
        if existing_feedback:
            await callback.answer("✅ Вы уже оставили отзыв на этот ответ", show_alert=True)
            return
        
        # Добавляем отрицательный feedback без комментария
        feedback = await feedback_service.add_user_feedback(
            message_id=message_id,
            user_id=callback.from_user.id,
            feedback_type='dislike'
        )
        
        if feedback:
            # Создаем клавиатуру с возможностью добавить комментарий
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="💬 Добавить комментарий",
                        callback_data=f"feedback:add_comment:{message_id}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="🔍 Каталог продукции",
                        callback_data="search:new"
                    ),
                    types.InlineKeyboardButton(
                        text="🤖 Спросить AI",
                        callback_data="menu:question"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="⬅️ В главное меню",
                        callback_data="menu:main"
                    )
                ]
            ])
            
            thank_you_text = (
                "👎 <b>Спасибо за ваш отзыв!</b>\n\n"
                "Ваша оценка поможет нам улучшить качество ответов AI.\n\n"
                "Хотите добавить комментарий, чтобы помочь нам понять, "
                "что именно можно улучшить?"
            )
            
            # Всегда отправляем новое сообщение, чтобы не изменять ответ AI
            if callback.message:
                await callback.message.answer(
                    thank_you_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
            await callback.answer("👎 Отзыв сохранен")
        else:
            await callback.answer("❌ Не удалось сохранить отзыв", show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка при обработке отрицательного feedback: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith('feedback:add_comment:'))
async def request_comment(callback: types.CallbackQuery, state: FSMContext):
    """Запрос комментария к отрицательному отзыву."""
    if not callback.data:
        await callback.answer("Ошибка обработки данных")
        return
    
    try:
        _, _, message_id_str = callback.data.split(':', 2)
        message_id = int(message_id_str)
        
        # Сохраняем message_id в состоянии для последующего использования
        await state.update_data(feedback_message_id=message_id)
        await state.set_state(FeedbackState.waiting_comment)
        
        # Просим пользователя написать комментарий
        comment_text = (
            "💬 <b>Расскажите, что не так?</b>\n\n"
            "Пожалуйста, опишите, почему ответ не был полезен.\n"
            "Ваши комментарии помогут улучшить работу AI.\n\n"
            "<i>Напишите ваш комментарий в следующем сообщении:</i>"
        )
        
        # Всегда отправляем новое сообщение
        if callback.message:
            await callback.message.answer(
                comment_text,
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data="feedback:cancel"
                    )
                ]]),
                parse_mode="HTML"
            )
        
        await callback.answer("💬 Оставьте комментарий")
    
    except Exception as e:
        logger.error(f"Ошибка при запросе комментария: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.message(FeedbackState.waiting_comment)
async def handle_feedback_comment(message: types.Message, session: AsyncSession, state: FSMContext):
    """Обработка комментария к отрицательной обратной связи."""
    if not message.text:
        await message.answer("Пожалуйста, напишите текстовый комментарий.")
        return
    
    try:
        # Получаем данные из состояния
        state_data = await state.get_data()
        message_id = state_data.get('feedback_message_id')
        
        if not message_id:
            await message.answer("❌ Ошибка: не найден ID сообщения для отзыва.")
            await state.clear()
            return
        
        comment = message.text.strip()
        if len(comment) < 5:
            await message.answer(
                "Комментарий слишком короткий. Пожалуйста, опишите проблему подробнее (минимум 5 символов)."
            )
            return
        
        feedback_service = FeedbackService(session)
        
        if not message.from_user:
            await message.answer("Ошибка определения пользователя.")
            await state.clear()
            return
        
        # Обновляем комментарий (через повторное создание feedback с комментарием)
        updated_feedback = await feedback_service.add_user_feedback(
            message_id=message_id,
            user_id=message.from_user.id,
            feedback_type='dislike',
            comment=comment
        )
        
        if updated_feedback:
            thank_you_text = (
                "✅ <b>Спасибо за подробный отзыв!</b>\n\n"
                f"Ваш комментарий: <i>'{comment[:100]}{'...' if len(comment) > 100 else ''}'</i>\n\n"
                "Мы обязательно учтем ваши замечания для улучшения работы AI.\n"
                "Чем еще могу помочь?"
            )
            
            await message.answer(
                thank_you_text,
                reply_markup=get_feedback_submitted_keyboard(),
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Не удалось сохранить комментарий. Попробуйте позже.")
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Ошибка при сохранении комментария feedback: {e}")
        await message.answer("❌ Произошла ошибка при сохранении комментария.")
        await state.clear()


@router.callback_query(F.data == 'feedback:cancel')
async def handle_feedback_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена добавления комментария."""
    await state.clear()
    
    cancel_text = (
        "❌ <b>Добавление комментария отменено</b>\n\n"
        "Ваш отзыв уже сохранен.\n"
        "Чем еще могу помочь?"
    )
    
    # Всегда отправляем новое сообщение
    if callback.message:
        await callback.message.answer(
            cancel_text,
            reply_markup=get_feedback_submitted_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer("Отмена")
