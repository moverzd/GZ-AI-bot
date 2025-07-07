from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder 


router = Router()
@router.callback_query(lambda c: c.data.startswith("addmain:"), F.from_user.id.in_(ADMIN_IDS))
async def add_main_request(cb: types.CallbackQuery, state: FSMContext):
    """
    Admin pressed button related to changing main picture of product
    """
    prod_id= int(cb.data.split(":", 1)[1])
    await state.update_data(prod_id = prod_id)
    await state.set_state(AddMainPic.waiting_photo)
    await state.cb.message.answer("Оправьте фото, которое станет *главным*.")
    await cb.answer()


async def add_main_save(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["prod_id"]
    file_id = msg.photo[-1].file_id
    async with AsyncSessionLocal() as session:
        await insert_image(session, pro)

@router.callback_query(F.data == "admin:add_prod")
async def add_product_request(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработчик запроса на добавление товара
    """
    from src.handlers.states import AddProd
    
    await state.set_state(AddProd.waiting_name)
    await callback.message.answer("Введите название нового товара:")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete:"))
async def confirm_delete(callback: types.CallbackQuery):
    """
    Обработчик запроса на удаление товара
    """
    product_id = int(callback.data.split(':')[1])
    
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить товар с ID {product_id}?",
        reply_markup=get_delete_confirm_keyboard(product_id)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("confirm_delete:"))
async def do_delete(callback: types.CallbackQuery, session: AsyncSession):
    """
    Обработчик подтверждения удаления товара
    """
    product_id = int(callback.data.split(':')[1])
    
    # Мягкое удаление продукта
    product_service = ProductService(session)
    await product_service.delete_product(product_id)
    
    await callback.message.edit_text(
        f"✅ Товар с ID {product_id} успешно удален!"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("cancel_delete:"))
async def cancel_delete(callback: types.CallbackQuery):
    """
    Обработчик отмены удаления товара
    """
    product_id = int(callback.data.split(':')[1])
    
    await callback.message.edit_text(
        f"❌ Удаление товара с ID {product_id} отменено.",
        reply_markup=get_admin_product_keyboard(product_id)
    )
    await callback.answer()

# TODO:
# import TG_ADMIN_IDS
# import AsyncSessionLocal
# import insert_image_insert_doc,soft_delete_product
# import AddMainPic
# import esc


