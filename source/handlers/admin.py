import os
from aiogram import types
from aiogram.fsm.context import FSMContext
from db import add_listing, get_user_role, update_listing, delete_listing, search_listings
from keyboards import get_main_menu, add_back_button
from states import ListingState, EditState
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка Google Sheets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)
sheet = client.open("Бот риэлтор").worksheet("params")

USER_VALUES = None

def load_param_values():
    global USER_VALUES
    data = sheet.get_all_records()
    result = {
        'city': set(),
        'districts_by_city': {},
        'rooms': set(),
        'floor': set(),
        'max_price': set(),
        'min_price': set()
    }
    for row in data:
        result['city'].add(str(row['city']))
        result['districts_by_city'].setdefault(row['city'], set()).add(str(row['district']))
        result['rooms'].add(str(row['rooms']))
        result['floor'].add(str(row['floor']))
        result['max_price'].add(str(row['max_price']))
        result['min_price'].add(str(row['min_price']))
    USER_VALUES = result

load_param_values()

LISTING_STEPS = {
    'Квартира': [
        ('city', 'Какой город', lambda state_data=None: sorted(list(USER_VALUES['city']))),
        ('district', 'Какой район', lambda state_data: sorted(list(USER_VALUES['districts_by_city'].get(state_data.get('params_collected', {}).get('city', ''), set())))),
        ('rooms', 'Сколько комнат', lambda state_data=None: sorted(list(USER_VALUES['rooms']))),
        ('floor', 'Этаж', lambda state_data=None: sorted(list(USER_VALUES['floor']))),
        ('max_price', 'Максимальная стоимость', lambda state_data=None: sorted(list(USER_VALUES['max_price']))),
        ('description', 'Введите описание', lambda state_data=None: None),
        ('image_paths', 'Загрузите до 10 фото (отправляйте по одному)', lambda state_data=None: None)
    ],
    'Дом': [
        ('city', 'Какой город', lambda state_data=None: sorted(list(USER_VALUES['city']))),
        ('district', 'Район', lambda state_data: sorted(list(USER_VALUES['districts_by_city'].get(state_data.get('params_collected', {}).get('city', ''), set())))),
        ('min_price', 'Минимальная стоимость', lambda state_data=None: sorted(list(USER_VALUES['min_price']))),
        ('max_price', 'Максимальная стоимость', lambda state_data=None: sorted(list(USER_VALUES['max_price']))),
        ('description', 'Введите описание', lambda state_data=None: None),
        ('image_paths', 'Загрузите до 10 фото (отправляйте по одному)', lambda state_data=None: None)
    ]
}

async def create_listing_start(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    buttons = [[types.InlineKeyboardButton(text=ht, callback_data=f"type_{ht}")] for ht in LISTING_STEPS.keys()]
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.message.edit_text("Выберите тип жилья:", reply_markup=keyboard)

async def process_listing_type(callback: types.CallbackQuery, state: FSMContext):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    housing_type = callback.data.split("_")[1]
    await state.update_data(type=housing_type, params_collected={'image_paths': []}, step_index=0)
    await state.set_state(ListingState.step)
    await process_listing_step(callback, state)

async def process_listing_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    steps = LISTING_STEPS[data['type']]
    step_index = data['step_index']
    
    if step_index >= len(steps):
        await save_listing(callback, state)
        return
    
    param_key, prompt, options_func = steps[step_index]
    options = options_func(data) if options_func else None
    await state.update_data(current_param=param_key)
    
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"option_{opt}")] for opt in options]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.message.edit_text(prompt + ":", reply_markup=keyboard)
    else:
        keyboard = add_back_button(None)
        if param_key == 'image_paths' and len(data['params_collected']['image_paths']) < 10:
            buttons = [[types.InlineKeyboardButton(text="Сохранить", callback_data="save_listing")]]
            keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.message.edit_text(prompt + ":", reply_markup=keyboard)
        if param_key == 'image_paths':
            await callback.message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте следующее фото.")

async def process_listing_option(callback: types.CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[1]
    data = await state.get_data()
    params_collected = data['params_collected']
    params_collected[data['current_param']] = option
    await state.update_data(params_collected=params_collected, step_index=data['step_index'] + 1)
    await process_listing_step(callback, state)

async def process_listing_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data['current_param'] == 'description':
        params_collected = data['params_collected']
        params_collected['description'] = message.text
        await state.update_data(params_collected=params_collected, step_index=data['step_index'] + 1)
        await process_listing_step_after_message(message, state)

async def process_listing_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data['current_param'] == 'image_paths':
        photo = message.photo[-1]
        file_path = f"uploads/{photo.file_id}.jpg"
        await message.bot.download(photo, file_path)
        params_collected = data['params_collected']
        params_collected['image_paths'].append(file_path)
        if len(params_collected['image_paths']) >= 10:
            await save_listing_after_message(message, state)
        else:
            await state.update_data(params_collected=params_collected)
            await process_listing_step_after_message(message, state)

async def process_listing_step_after_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = LISTING_STEPS[data['type']]
    step_index = data['step_index']
    
    if step_index >= len(steps):
        await save_listing_after_message(message, state)
        return
    
    param_key, prompt, options_func = steps[step_index]
    options = options_func(data) if options_func else None
    await state.update_data(current_param=param_key)
    
    keyboard = add_back_button(None)
    if param_key == 'image_paths' and len(data['params_collected']['image_paths']) < 10:
        buttons = [[types.InlineKeyboardButton(text="Сохранить", callback_data="save_listing")]]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"option_{opt}")] for opt in options]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await message.reply(prompt + ":", reply_markup=keyboard)
    else:
        await message.reply(prompt + ":", reply_markup=keyboard)
        if param_key == 'image_paths':
            await message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте следующее фото.")

async def save_listing(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    params = data['params_collected']
    params['type'] = data['type']
    add_listing(params, callback.from_user.id)
    await callback.message.edit_text("Объявление создано!", reply_markup=get_main_menu(callback.from_user.id))
    await state.clear()

async def save_listing_after_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    params = data['params_collected']
    params['type'] = data['type']
    add_listing(params, message.from_user.id)
    await message.reply("Объявление создано!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

async def manual_save_listing(callback: types.CallbackQuery, state: FSMContext):
    await save_listing(callback, state)

async def reload_params(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    try:
        load_param_values()
        await callback.message.edit_text("Параметры перезагружены!", reply_markup=get_main_menu(callback.from_user.id))
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu(callback.from_user.id))

async def edit_listing(callback: types.CallbackQuery, state: FSMContext):
    listing_id = int(callback.data.split("_")[1])
    listings = search_listings({'id': listing_id})
    if not listings:
        await callback.answer("Объявление не найдено!", show_alert=True)
        return
    listing = listings[0]
    role = get_user_role(callback.from_user.id)
    if role != 'superadmin' and listing[8] != callback.from_user.id:
        await callback.answer("Это не ваше объявление!", show_alert=True)
        return
    
    await state.update_data(listing_id=listing_id, type=listing[1], params_collected={
        'city': listing[2], 'district': listing[3], 'rooms': str(listing[4]) if listing[4] else '0',
        'floor': str(listing[5]) if listing[5] else '0', 'max_price': str(listing[6]) if listing[6] else '0',
        'min_price': str(listing[7]) if listing[7] else '0', 'description': listing[9] or '',
        'image_paths': listing[10]  # Список путей
    }, step_index=0)
    await state.set_state(EditState.step)
    await process_edit_step(callback, state)

async def process_edit_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    steps = LISTING_STEPS[data['type']]
    step_index = data['step_index']
    
    if step_index >= len(steps):
        await save_edited_listing(callback, state)
        return
    
    param_key, prompt, options_func = steps[step_index]
    options = options_func(data) if options_func else None
    await state.update_data(current_param=param_key)
    
    keyboard = add_back_button(None)
    if param_key == 'image_paths' and len(data['params_collected']['image_paths']) < 10:
        buttons = [[types.InlineKeyboardButton(text="Сохранить", callback_data="save_edit_listing")]]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"edit_option_{opt}")] for opt in options]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.message.edit_text(f"{prompt} (текущее: {data['params_collected'].get(param_key, 'не указано')}):", 
                                        reply_markup=keyboard)
    else:
        await callback.message.edit_text(f"{prompt} (текущее: {data['params_collected'].get(param_key, 'не указано')}):", 
                                        reply_markup=keyboard)
        if param_key == 'image_paths':
            await callback.message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте следующее фото.")

async def process_edit_option(callback: types.CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[2]
    data = await state.get_data()
    params_collected = data['params_collected']
    params_collected[data['current_param']] = option
    await state.update_data(params_collected=params_collected, step_index=data['step_index'] + 1)
    await process_edit_step(callback, state)

async def process_edit_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    param_key = data['current_param']
    if param_key == 'description':
        params_collected = data['params_collected']
        params_collected['description'] = message.text
        await state.update_data(params_collected=params_collected, step_index=data['step_index'] + 1)
        await process_edit_step_after_message(message, state)

async def process_edit_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data['current_param'] == 'image_paths':
        photo = message.photo[-1]
        file_path = f"uploads/{photo.file_id}.jpg"
        await message.bot.download(photo, file_path)
        params_collected = data['params_collected']
        params_collected['image_paths'].append(file_path)
        if len(params_collected['image_paths']) >= 10:
            await save_edited_listing_after_message(message, state)
        else:
            await state.update_data(params_collected=params_collected)
            await process_edit_step_after_message(message, state)

async def process_edit_step_after_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = LISTING_STEPS[data['type']]
    step_index = data['step_index']
    
    if step_index >= len(steps):
        await save_edited_listing_after_message(message, state)
        return
    
    param_key, prompt, options_func = steps[step_index]
    options = options_func(data) if options_func else None
    await state.update_data(current_param=param_key)
    
    keyboard = add_back_button(None)
    if param_key == 'image_paths' and len(data['params_collected']['image_paths']) < 10:
        buttons = [[types.InlineKeyboardButton(text="Сохранить", callback_data="save_edit_listing")]]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"edit_option_{opt}")] for opt in options]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await message.reply(f"{prompt} (текущее: {data['params_collected'].get(param_key, 'не указано')}):", 
                           reply_markup=keyboard)
    else:
        await message.reply(f"{prompt} (текущее: {data['params_collected'].get(param_key, 'не указано')}):", 
                           reply_markup=keyboard)
        if param_key == 'image_paths':
            await message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте следующее фото.")

async def save_edited_listing(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    params = data['params_collected']
    params['type'] = data['type']
    update_listing(data['listing_id'], params)
    await callback.message.edit_text("Объявление обновлено!", reply_markup=get_main_menu(callback.from_user.id))
    await state.clear()

async def save_edited_listing_after_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    params = data['params_collected']
    params['type'] = data['type']
    update_listing(data['listing_id'], params)
    await message.reply("Объявление обновлено!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

async def manual_save_edit_listing(callback: types.CallbackQuery, state: FSMContext):
    await save_edited_listing(callback, state)

async def delete_listing(callback: types.CallbackQuery):
    listing_id = int(callback.data.split("_")[1])
    listings = search_listings({'id': listing_id})
    if not listings:
        await callback.answer("Объявление не найдено!", show_alert=True)
        return
    role = get_user_role(callback.from_user.id)
    if role != 'superadmin' and listings[0][8] != callback.from_user.id:
        await callback.answer("Это не ваше объявление!", show_alert=True)
        return
    delete_listing(listing_id)
    await callback.message.edit_text("Объявление удалено!", reply_markup=get_main_menu(callback.from_user.id))

async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu(callback.from_user.id))