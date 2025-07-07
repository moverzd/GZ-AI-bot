from aiogram.fsm.state import StatesGroup, State

class AddMainPic(StatesGroup):
    """
    state on adding main image
    """
    waiting_photo = State()


class EditCard(StatesGroup):
    """
    editing product card
    """
    waiting_fiels = State()
    waiting_value = State()


class AddProd(StatesGroup):
    waiting_name = State()
    waiting_category = State()
    waiting_description = State()


class SearchProduct(StatesGroup):
    """
    Состояние для поиска продуктов
    """
    waiting_query = State()


