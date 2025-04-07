from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(user_id):
    from db import get_user_role 
    buttons = []
    role = get_user_role(user_id)
    
    if role == 'superadmin':
        buttons.extend([
            [InlineKeyboardButton(text="Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton(text="Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton(text="Показать всех админов", callback_data="list_admins")],
            [InlineKeyboardButton(text="Синхронизировать данные с Google Sheets", callback_data="sync_data")]
        ])
    if role in ['admin', 'superadmin']:
        buttons.extend([
            [InlineKeyboardButton(text="Создать объявление", callback_data="create_listing")],
            [InlineKeyboardButton(text="Перезагрузить параметры", callback_data="reload_params")],
            [InlineKeyboardButton(text="Реферальная программа", callback_data="referral_program")]
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в начало", callback_data="back_to_start")]
    ])

def get_request_keyboard(user_id):
    """Создаёт клавиатуру с кнопками 'Подобрать жильё для меня', 'Найти жильё' и 'Меню' (для админов)"""
    from db import get_user_role
    role = get_user_role(user_id)
    
    keyboard = [
        [KeyboardButton(text="Подобрать жильё для меня"), KeyboardButton(text="Найти жильё")]
    ]
    if role in ['admin', 'superadmin']:
        keyboard.append([KeyboardButton(text="Меню")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False  # Клавиатура будет постоянной
    )

def add_back_button(keyboard):
    if not keyboard:
        return get_back_button()
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад в начало", callback_data="back_to_start")])
    return keyboard