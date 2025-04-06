from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user_role

def get_main_menu(user_id):
    buttons = []
    role = get_user_role(user_id)
    
    if role == 'superadmin':
        buttons.extend([
            [InlineKeyboardButton(text="Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton(text="Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton(text="Показать всех админов", callback_data="list_admins")]
        ])
    if role in ['admin', 'superadmin']:
        buttons.extend([
            [InlineKeyboardButton(text="Создать объявление", callback_data="create_listing")],
            [InlineKeyboardButton(text="Перезагрузить параметры", callback_data="reload_params")]
        ])
    buttons.append([InlineKeyboardButton(text="Найти жильё", callback_data="search_start")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в начало", callback_data="back_to_start")]
    ])

def add_back_button(keyboard):
    if not keyboard:
        return get_back_button()
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад в начало", callback_data="back_to_start")])
    return keyboard