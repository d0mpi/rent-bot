# handlers/superadmin.py
from aiogram import types
from aiogram.fsm.context import FSMContext
from db import add_admin, remove_admin, get_all_admins, get_user_role
from keyboards import get_main_menu
from states import AdminAddState

async def add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    await state.set_state(AdminAddState.waiting_for_username)
    await callback.message.edit_text("Введите Telegram-ник админа (например, @username):")
    await callback.answer()

async def process_admin_username(message: types.Message, state: FSMContext):
    if get_user_role(message.from_user.id) != 'superadmin':
        await message.reply("Ты не суперадмин!")
        return
    username = message.text.strip()
    if not username.startswith('@'):
        await message.reply("Ник должен начинаться с @!")
        return
    # Временный user_id как хэш username, в будущем можно заменить на реальный ID
    add_admin(hash(username), username)
    await message.reply(f"Админ {username} добавлен!", reply_markup=get_main_menu(message.from_user.id))
    await state.finish()

async def remove_admin_start(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    admins = get_all_admins()
    if not admins:
        await callback.message.edit_text("Админов нет!", reply_markup=get_main_menu(callback.from_user.id))
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for admin_id, username in admins:
        keyboard.add(types.InlineKeyboardButton(username, callback_data=f"delete_admin_{admin_id}"))
    await callback.message.edit_text("Выберите админа для удаления:", reply_markup=keyboard)
    await callback.answer()

async def process_admin_removal(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    admin_id = int(callback.data.split("_")[2])
    remove_admin(admin_id)
    await callback.message.edit_text("Админ удалён!", reply_markup=get_main_menu(callback.from_user.id))
    await callback.answer()

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
    await callback.answer()