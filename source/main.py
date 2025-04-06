import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram import F
from config import API_TOKEN
from db import init_db
from handlers.superadmin import (add_admin_start, process_admin_username, remove_admin_start,
                                process_admin_removal, list_admins)
from handlers.admin import (create_listing_start, process_listing_type, process_listing_option,
                           process_listing_text, process_listing_image, reload_params,
                           edit_listing, process_edit_option, process_edit_text, process_edit_image,
                           delete_listing, back_to_start, manual_save_listing, manual_save_edit_listing)
from handlers.user import (start, search_start, process_search_type, process_search_option, back_to_start as user_back_to_start)
from states import AdminAddState, ListingState, SearchState, EditState

os.makedirs("uploads", exist_ok=True)
init_db()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# General handlers
dp.message.register(start, Command("start"))

# Superadmin handlers
dp.callback_query.register(add_admin_start, F.data == "add_admin")
dp.message.register(process_admin_username, AdminAddState.waiting_for_username)
dp.callback_query.register(remove_admin_start, F.data == "remove_admin")
dp.callback_query.register(process_admin_removal, F.data.startswith("delete_admin_"))
dp.callback_query.register(list_admins, F.data == "list_admins")

# Admin handlers
dp.callback_query.register(create_listing_start, F.data == "create_listing")
dp.callback_query.register(process_listing_type, F.data.startswith("type_"))
dp.callback_query.register(process_listing_option, F.data.startswith("option_"), ListingState.step)
dp.message.register(process_listing_text, ListingState.step, F.text)
dp.message.register(process_listing_image, ListingState.step, F.photo)
dp.callback_query.register(manual_save_listing, F.data == "save_listing", ListingState.step)
dp.callback_query.register(reload_params, F.data == "reload_params")
dp.callback_query.register(edit_listing, F.data.startswith("edit_"))
dp.callback_query.register(process_edit_option, F.data.startswith("edit_option_"), EditState.step)
dp.message.register(process_edit_text, EditState.step, F.text)
dp.message.register(process_edit_image, EditState.step, F.photo)
dp.callback_query.register(manual_save_edit_listing, F.data == "save_edit_listing", EditState.step)
dp.callback_query.register(delete_listing, F.data.startswith("delete_"))
dp.callback_query.register(back_to_start, F.data == "back_to_start")

# User handlers
dp.callback_query.register(search_start, F.data == "search_start")
dp.callback_query.register(process_search_type, F.data.startswith("search_type_"))
dp.callback_query.register(process_search_option, F.data.startswith("search_option_"), SearchState.step)
dp.callback_query.register(user_back_to_start, F.data == "back_to_start")

if __name__ == '__main__':
    dp.run_polling(bot)