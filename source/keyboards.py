# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user_role

def get_main_menu(user_id):
    menu = InlineKeyboardMarkup(row_width=1)
    role = get_user_role(user_id)
    if role == 'superadmin':
        menu.add(
            InlineKeyboardButton("Добавить админа", callback_data="add_admin"),
            InlineKeyboardButton("Удалить админа", callback_data="remove_admin"),
            InlineKeyboardButton("Показать всех админов", callback_data="list_admins")
        )
    if role in ['admin', 'superadmin']:
        menu.add(
            InlineKeyboardButton("Создать объявление", callback_data="create_listing"),
            InlineKeyboardButton("Редактировать объявление", callback_data="edit_listing"),
            InlineKeyboardButton("Просмотреть объявления", callback_data="view_listings")
        )
    # Для обычных пользователей пока ничего
    return menu