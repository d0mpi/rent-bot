#superadmin.py
from aiogram import types
from aiogram.fsm.context import FSMContext
from db import add_user, remove_user, get_all_admins, get_user_role
from keyboards import get_main_menu
from states import AdminAddState

async def add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    await state.set_state(AdminAddState.waiting_for_username)
    await callback.message.edit_text("Введите Telegram-ник админа (например, @username):")

async def process_admin_username(message: types.Message, state: FSMContext):
    if get_user_role(message.from_user.id) != 'superadmin':
        await message.reply("Ты не суперадмин!")
        return
    username = message.text.strip()
    if not username.startswith('@'):
        await message.reply("Ник должен начинаться с @!")
        return
    add_user(hash(username), username)
    await message.reply(f"Админ {username} добавлен!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

async def remove_admin_start(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    admins = get_all_admins()
    if not admins:
        await callback.message.edit_text("Админов нет!", reply_markup=get_main_menu(callback.from_user.id))
        return
    buttons = [[types.InlineKeyboardButton(text=username, callback_data=f"delete_admin_{admin_id}")] for admin_id, username in admins]
    await callback.message.edit_text("Выберите админа для удаления:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons))

async def process_admin_removal(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    admin_id = int(callback.data.split("_")[2])
    remove_user(admin_id)
    await callback.message.edit_text("Админ удалён!", reply_markup=get_main_menu(callback.from_user.id))

async def list_admins(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    admins = get_all_admins()
    if not admins:
        await callback.message.edit_text("Админов нет!", reply_markup=get_main_menu(callback.from_user.id))
    else:
        admin_list = "\n".join([admin[1] for admin in admins])
        await callback.message.edit_text(f"Список админов:\n{admin_list}", reply_markup=get_main_menu(callback.from_user.id))