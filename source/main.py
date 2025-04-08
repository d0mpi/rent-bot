from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram import F
from config import API_TOKEN, WELCOME_MESSAGE
from db import init_db
from handlers import superadmin, admin, user
from states import AdminAddState, ListingState, SearchState, EditState, ReferralState, RequestState

import os
os.makedirs("uploads", exist_ok=True)
init_db()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Регистрация обработчиков
dp.message.register(user.start, Command("start"))
dp.message.register(user.search_start, F.text == "Посмотреть варианты")
dp.message.register(admin.show_admin_menu, F.text == "Меню")
dp.message.register(user.create_request_start, F.text == "Оставить заявку")

# Superadmin
dp.callback_query.register(superadmin.add_admin_start, F.data == "add_admin")
dp.message.register(superadmin.process_admin_username, AdminAddState.waiting_for_username)
dp.callback_query.register(superadmin.remove_admin_start, F.data == "remove_admin")
dp.callback_query.register(superadmin.process_admin_removal, F.data.startswith("delete_admin_"))
dp.callback_query.register(superadmin.list_admins, F.data == "list_admins")

# Admin
dp.callback_query.register(admin.create_listing_start, F.data == "create_listing")
dp.callback_query.register(admin.process_listing_type, F.data.startswith("type_"))
dp.callback_query.register(admin.process_listing_option, F.data.startswith("option_"), ListingState.step)
dp.message.register(admin.process_listing_text, ListingState.step, F.text)
dp.message.register(admin.process_listing_image, ListingState.step, F.photo)
dp.callback_query.register(admin.manual_save_listing, F.data == "save_listing", ListingState.step)
dp.callback_query.register(admin.prev_listing_step, F.data == "prev_listing_step", ListingState.step)
dp.callback_query.register(admin.reload_params, F.data == "reload_params")
dp.callback_query.register(admin.edit_listing, F.data.startswith("edit_"))
dp.callback_query.register(admin.process_edit_option, F.data.startswith("edit_option_"), EditState.step)
dp.message.register(admin.process_edit_text, EditState.step, F.text)
dp.message.register(admin.process_edit_image, EditState.step, F.photo)
dp.callback_query.register(admin.manual_save_edit_listing, F.data == "save_edit_listing", EditState.step)
dp.callback_query.register(admin.delete_listing, F.data.startswith("delete_"))
dp.callback_query.register(admin.back_to_start, F.data == "back_to_start")
dp.callback_query.register(admin.referral_program_start, F.data == "referral_program")
dp.callback_query.register(admin.create_referral_start, F.data == "create_referral")
dp.message.register(admin.process_referral_description_create, ReferralState.waiting_for_description_create)
dp.callback_query.register(admin.list_referrals, F.data == "list_referrals")
dp.callback_query.register(admin.referral_options, F.data.startswith("referral_"))
dp.callback_query.register(admin.delete_referral, F.data.startswith("delete_referral_"))
dp.callback_query.register(admin.edit_referral_start, F.data.startswith("edit_referral_"))
dp.message.register(admin.process_referral_description_edit, ReferralState.waiting_for_description_edit)
dp.callback_query.register(admin.sync_data, F.data == "sync_data")

# User
dp.callback_query.register(user.process_search_type, F.data.startswith("search_type_"))
dp.callback_query.register(user.process_search_option, F.data.startswith("search_option_"), SearchState.step)
dp.message.register(user.process_search_text, SearchState.step, F.text)
dp.callback_query.register(user.skip_search_step, F.data == "skip_search_step", SearchState.step)
dp.callback_query.register(user.prev_search_step, F.data == "prev_search_step", SearchState.step)  # Новая регистрация
dp.callback_query.register(user.back_to_start, F.data == "back_to_start")
dp.callback_query.register(user.process_post_link, F.data.startswith("post_"))
dp.callback_query.register(user.start_request_filling, F.data == "start_request_filling")
dp.message.register(user.process_request_name, RequestState.waiting_for_name)
dp.message.register(user.process_request_phone, RequestState.waiting_for_phone)
dp.message.register(user.process_request_district, RequestState.waiting_for_district)
dp.message.register(user.process_request_date, RequestState.waiting_for_date)
dp.message.register(user.process_request_comment, RequestState.waiting_for_comment)

if __name__ == '__main__':
    dp.run_polling(bot)