# main.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN
from db import init_db
from states import ListingState, AdminAddState
from handlers.superadmin import (add_admin_start, process_admin_username, remove_admin_start,
                                process_admin_removal, list_admins)
from handlers.admin import (create_listing_start, process_listing_type, process_option,
                           process_text_param, view_listings, edit_listing_start)
from handlers.user import start

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация обработчиков
dp.message_handler(commands=['start'])(start)
dp.callback_query_handler(text="add_admin")(add_admin_start)
dp.message_handler(state=AdminAddState.waiting_for_username)(process_admin_username)
dp.callback_query_handler(text="remove_admin")(remove_admin_start)
dp.callback_query_handler(lambda c: c.data.startswith("delete_admin_"))(process_admin_removal)
dp.callback_query_handler(text="list_admins")(list_admins)
dp.callback_query_handler(text="create_listing")(create_listing_start)
dp.callback_query_handler(lambda c: c.data.startswith("type_"))(process_listing_type)
dp.callback_query_handler(lambda c: c.data.startswith("option_"), state=ListingState.dynamic)(process_option)
dp.message_handler(state=ListingState.dynamic)(process_text_param)
dp.callback_query_handler(text="view_listings")(view_listings)
dp.callback_query_handler(text="edit_listing")(edit_listing_start)

if __name__ == '__main__':
    init_db()
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)