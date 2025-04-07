# main.py
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
                           delete_listing, back_to_start, manual_save_listing, manual_save_edit_listing,
                           referral_program_start, create_referral_start, process_referral_description_create,
                           list_referrals, referral_options, delete_referral, edit_referral_start,
                           process_referral_description_edit, show_admin_menu, skip_edit_step, skip_step, sync_data)
from handlers.user import (process_post_link, start, search_start, process_search_type, process_search_option, 
                          skip_search_step, process_search_text, back_to_start as user_back_to_start,
                          create_request_start, process_request_name, process_request_phone,
                          process_request_district, process_request_date, process_request_comment, start_request_filling)
from states import AdminAddState, ListingState, SearchState, EditState, ReferralState, RequestState

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

# Referral program handlers
dp.callback_query.register(referral_program_start, F.data == "referral_program")
dp.callback_query.register(create_referral_start, F.data == "create_referral")
dp.message.register(process_referral_description_create, ReferralState.waiting_for_description_create)
dp.callback_query.register(list_referrals, F.data == "list_referrals")
dp.callback_query.register(referral_options, F.data.startswith("referral_"))
dp.callback_query.register(delete_referral, F.data.startswith("delete_referral_"))
dp.callback_query.register(edit_referral_start, F.data.startswith("edit_referral_"))
dp.message.register(process_referral_description_edit, ReferralState.waiting_for_description_edit)
dp.callback_query.register(sync_data, F.data == "sync_data")

# User handlers
dp.message.register(search_start, F.text == "Найти жильё")
dp.message.register(show_admin_menu, F.text == "Меню")
dp.callback_query.register(process_search_type, F.data.startswith("search_type_"))
dp.callback_query.register(process_search_option, F.data.startswith("search_option_"), SearchState.step)
dp.message.register(process_search_text, SearchState.step, F.text)
dp.callback_query.register(skip_search_step, F.data == "skip_search_step", SearchState.step)
dp.callback_query.register(user_back_to_start, F.data == "back_to_start")
dp.callback_query.register(process_post_link, F.data.startswith("post_"))

# Request handlers
dp.message.register(create_request_start, F.text == "Подобрать жильё для меня")
dp.callback_query.register(start_request_filling, F.data == "start_request_filling")
dp.message.register(process_request_name, RequestState.waiting_for_name)
dp.message.register(process_request_phone, RequestState.waiting_for_phone)
dp.message.register(process_request_district, RequestState.waiting_for_district)
dp.message.register(process_request_date, RequestState.waiting_for_date)
dp.message.register(process_request_comment, RequestState.waiting_for_comment)

if __name__ == '__main__':
    dp.run_polling(bot)