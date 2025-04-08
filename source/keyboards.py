from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from db import get_user_role

def get_main_menu(user_id):
    buttons = []
    role = get_user_role(user_id)
    
    if role == 'superadmin':
        buttons.extend([
            [InlineKeyboardButton(text="Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton(text="Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton(text="Показать всех админов", callback_data="list_admins")],
            [InlineKeyboardButton(text="Обновить данные в таблицах", callback_data="sync_data")]
        ])
    if role in ['admin', 'superadmin']:
        buttons.extend([
            [InlineKeyboardButton(text="Создать объявление", callback_data="create_listing")],
            [InlineKeyboardButton(text="Вытащить данные из таблиц", callback_data="reload_params")],
            [InlineKeyboardButton(text="Реферальная программа", callback_data="referral_program")]
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

def get_request_keyboard(user_id):
    role = get_user_role(user_id)
    keyboard = [
        [KeyboardButton(text="Оставить заявку"), KeyboardButton(text="Посмотреть варианты")]
    ]
    if role in ['admin', 'superadmin']:
        keyboard.append([KeyboardButton(text="Меню")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def add_back_button(keyboard, is_search=False, is_listing=False):
    if not keyboard:
        if is_search:
            return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="prev_search_step")]])
        elif is_listing:
            return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="prev_listing_step")]])
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад", callback_data="back_to_start")]])
    
    if is_search:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="prev_search_step")])
    elif is_listing:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="prev_listing_step")])
    else:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_to_start")])
    return keyboard