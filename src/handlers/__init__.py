from aiogram import Dispatcher
from .common import router as common_router
from .catalog import router as catalog_router
from .search import router as search_router

def register_all_handlers(dp:Dispatcher) -> None:
    """
    registering all handlers
    """
    dp.include_router(common_router)
    dp.include_router(catalog_router)
    dp.include_router(search_router)