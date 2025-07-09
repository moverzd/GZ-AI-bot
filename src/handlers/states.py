from aiogram.fsm.state import StatesGroup, State

"""
FSM (Finite State Machine) - механизм, позволяющий боту помнить
в каком состоянии находится разговор с пользователем.
"""

class AddMainPic(StatesGroup):
    """
    Добавление главного изображения
    """
    waiting_photo = State()


class EditCard(StatesGroup):
    """
    Редактирование карточки продукта
    """
    waiting_product_id = State()  # Ожидание ID продукта для редактирования
    waiting_fields = State() # Ожидание выбора поля для редактирования
    waiting_value = State() # Ожидание нового значения поля


class AddProd(StatesGroup):
    """
    Добавление нового продукта
    """
    waiting_name = State()
    waiting_category = State()
    waiting_sphere = State()
    waiting_description = State()
    waiting_advantages = State()
    waiting_consumption = State()
    waiting_package = State()
    waiting_main_photo = State()


class SearchProduct(StatesGroup):
    """
    Состояние для поиска продуктов
    """
    waiting_query = State()


class DeleteProduct(StatesGroup):
    """
    Удаление продукта
    """
    waiting_product_id = State()  # Ожидание ID продукта для удаления



