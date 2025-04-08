#admin.py
import os
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from db import add_listing, generate_referral_code, get_connection, get_user_role, sync_clients, sync_referral_stats, update_listing, delete_listing, search_listings
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
sheet = client.open("Бот риэлтор").worksheet("Параметры объявления")

USER_VALUES = None

def load_param_values():
    global USER_VALUES
    data = sheet.get_all_records()
    result = {
        'city': set(),
        'districts_by_city': {},
        'rooms': set(),
        'floor': set(),
    }
    for row in data:
        result['city'].add(str(row['city']))
        result['districts_by_city'].setdefault(row['city'], set()).add(str(row['district']))
        result['rooms'].add(str(row['rooms']))
        result['floor'].add(str(row['floor']))
    USER_VALUES = result

load_param_values()

LISTING_STEPS = {
    'Аренда': [
        ('city', 'Какой город', lambda state_data=None: sorted(list(USER_VALUES['city']))),
        ('price', 'Укажите цену (введите число или пропустите)', lambda state_data=None: None),
        ('deposit', 'Наличие кауции (Да/Нет или пропустите)', lambda state_data=None: ['Да', 'Нет']),
        ('district', 'Какой район', lambda state_data: sorted(list(USER_VALUES['districts_by_city'].get(state_data.get('params_collected', {}).get('city', ''), set())))),
        ('address', 'Укажите адрес или ориентир (или пропустите)', lambda state_data=None: None),
        ('room_type', 'Тип комнаты', lambda state_data=None: ['Отдельная', 'Смежная', 'Студия']),
        ('term', 'Формат аренды', lambda state_data=None: ['Краткосрочная', 'Долгосрочная']),
        ('room_area', 'Площадь комнаты (в м², введите число или пропустите)', lambda state_data=None: None),
        ('total_area', 'Площадь квартиры (в м², введите число или пропустите)', lambda state_data=None: None),
        ('floor', 'Этаж', lambda state_data=None: sorted(list(USER_VALUES['floor']))),
        ('rooms', 'Кол-во комнат в квартире', lambda state_data=None: sorted(list(USER_VALUES['rooms']))),
        ('telegram_post_link', 'Ссылка на пост в Telegram (или пропустите)', lambda state_data=None: None),
        ('description', 'Введите описание (или пропустите)', lambda state_data=None: None),
        ('image_paths', 'Загрузите до 10 фото (отправляйте по одному)', lambda state_data=None: None)
    ]
}

# ... (оставляем остальной код без изменений до нужных функций)

async def create_listing_start(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    buttons = [[types.InlineKeyboardButton(text=ht, callback_data=f"type_{ht}")] for ht in LISTING_STEPS.keys()]
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons), is_listing=True)
    await callback.message.edit_text("Выберите тип жилья:", reply_markup=keyboard)

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
    
    buttons = []
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"option_{opt}")] for opt in options]
    buttons.append([types.InlineKeyboardButton(text="Пропустить", callback_data="skip_step")])
    if param_key == 'image_paths' and len(data['params_collected']['image_paths']) > 0:
        buttons.append([types.InlineKeyboardButton(text="Сохранить", callback_data="save_listing")])
    
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons), is_listing=True)
    await callback.message.edit_text(prompt + ":", reply_markup=keyboard)
    if param_key == 'image_paths':
        await callback.message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте фото или пропустите.")

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
    
    buttons = []
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"option_{opt}")] for opt in options]
    buttons.append([types.InlineKeyboardButton(text="Пропустить", callback_data="skip_step")])
    if param_key == 'image_paths' and len(data['params_collected']['image_paths']) > 0:
        buttons.append([types.InlineKeyboardButton(text="Сохранить", callback_data="save_listing")])
    
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons), is_listing=True)
    await message.reply(prompt + ":", reply_markup=keyboard)
    if param_key == 'image_paths':
        await message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте фото или пропустите.")

async def prev_listing_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step_index = data.get('step_index', 1)
    if step_index <= 1:
        buttons = [[types.InlineKeyboardButton(text=ht, callback_data=f"type_{ht}")] for ht in LISTING_STEPS.keys()]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons), is_listing=True)
        await callback.message.edit_text("Выберите тип жилья:", reply_markup=keyboard)
        await state.update_data(step_index=0)
    else:
        await state.update_data(step_index=step_index - 1)
        await process_listing_step(callback, state)
    await callback.answer()

async def process_listing_type(callback: types.CallbackQuery, state: FSMContext):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    housing_type = callback.data.split("_")[1]
    await state.update_data(type=housing_type, params_collected={'image_paths': []}, step_index=0)
    await state.set_state(ListingState.step)
    await process_listing_step(callback, state)

async def process_listing_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    param_key = data['current_param']
    params_collected = data['params_collected']
    
    if param_key in ['price', 'room_area', 'total_area']:
        try:
            value = float(message.text)
            params_collected[param_key] = value
        except ValueError:
            await message.reply("Пожалуйста, введите корректное число!")
            return
    elif param_key in ['address', 'description', 'telegram_post_link']:  # Добавили telegram_post_link
        params_collected[param_key] = message.text
    # Район тоже можно вводить текстом, если это нужно, но оставим выбор через кнопки
    
    await state.update_data(params_collected=params_collected, step_index=data['step_index'] + 1)
    await process_listing_step_after_message(message, state)

async def skip_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(step_index=data['step_index'] + 1)
    await process_listing_step(callback, state)
    await callback.answer()  # Подтверждаем обработку callback

async def process_listing_option(callback: types.CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[1]
    data = await state.get_data()
    params_collected = data['params_collected']
    params_collected[data['current_param']] = option
    await state.update_data(params_collected=params_collected, step_index=data['step_index'] + 1)
    await process_listing_step(callback, state)

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
    if role != 'superadmin' and listing[6] != callback.from_user.id:  # Индекс 6 - admin_id
        await callback.answer("Это не ваше объявление!", show_alert=True)
        return
    
    # Используем params из новой структуры
    params = listing[9]  # Индекс 9 - словарь params
    params['image_paths'] = listing[8]  # Индекс 8 - image_paths
    await state.update_data(listing_id=listing_id, type=listing[1], params_collected=params, step_index=0)
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
    
    buttons = []
    if options:
        buttons = [[types.InlineKeyboardButton(text=opt, callback_data=f"edit_option_{opt}")] for opt in options]
        buttons.append([types.InlineKeyboardButton(text="Пропустить", callback_data="skip_edit_step")])
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))  # Без is_search/is_listing
        await callback.message.edit_text(f"{prompt} (текущее: {data['params_collected'].get(param_key, 'не указано')}):", 
                                        reply_markup=keyboard)
    else:
        buttons = [[types.InlineKeyboardButton(text="Пропустить", callback_data="skip_edit_step")]]
        if param_key == 'image_paths' and len(data['params_collected']['image_paths']) < 10:
            buttons.append([types.InlineKeyboardButton(text="Сохранить", callback_data="save_edit_listing")])
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))  # Без is_search/is_listing
        await callback.message.edit_text(f"{prompt} (текущее: {data['params_collected'].get(param_key, 'не указано')}):", 
                                        reply_markup=keyboard)
        if param_key == 'image_paths':
            await callback.message.reply(f"Загружено фото: {len(data['params_collected']['image_paths'])}/10. Отправьте следующее фото.")

async def skip_edit_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    # Оставляем текущий параметр без изменений
    await state.update_data(step_index=data['step_index'] + 1)
    await process_edit_step(callback, state)

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
    params_collected = data['params_collected']
    
    if param_key in ['price', 'room_area', 'total_area']:
        try:
            value = float(message.text)
            params_collected[param_key] = value
        except ValueError:
            await message.reply("Пожалуйста, введите корректное число!")
            return
    elif param_key in ['address', 'description', 'telegram_post_link']:  # Добавили telegram_post_link
        params_collected[param_key] = message.text
    
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
    user_id = callback.from_user.id
    await state.clear()
    await callback.message.bot.send_message(user_id, "Меню администратора:", reply_markup=get_main_menu(user_id))
    await callback.message.delete()

from states import ReferralState

# Начало работы с реферальной программой
async def referral_program_start(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    buttons = [
        [types.InlineKeyboardButton(text="Создать реферальную ссылку", callback_data="create_referral")],
        [types.InlineKeyboardButton(text="Мои реферальные ссылки", callback_data="list_referrals")]
    ]
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.message.edit_text("Реферальная программа:", reply_markup=keyboard)

# Создание новой реферальной ссылки
async def create_referral_start(callback: types.CallbackQuery, state: FSMContext):
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    await state.set_state(ReferralState.waiting_for_description_create)
    await callback.message.edit_text("Введите описание для реферальной ссылки:")

async def process_referral_description_create(message: types.Message, state: FSMContext, bot: Bot):
    description = message.text
    admin_id = message.from_user.id
    referral_code = generate_referral_code()
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO referral_links (admin_id, referral_code, description) VALUES (?, ?, ?)", 
              (admin_id, referral_code, description))
    conn.commit()
    conn.close()
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={referral_code}"
    await message.reply(f"Реферальная ссылка создана! Ссылка: {link}\nОписание: {description}", 
                       reply_markup=get_main_menu(admin_id))
    await state.clear()

async def list_referrals(callback: types.CallbackQuery, bot: Bot):  # Добавляем bot как параметр
    if get_user_role(callback.from_user.id) not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    admin_id = callback.from_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, referral_code, description FROM referral_links WHERE admin_id=?", (admin_id,))
    referrals = c.fetchall()
    conn.close()
    if not referrals:
        await callback.message.edit_text("У вас нет реферальных ссылок.", 
                                       reply_markup=get_main_menu(admin_id))
        return
    bot_username = (await bot.get_me()).username  # Получаем имя бота
    buttons = []
    for ref_id, code, desc in referrals:
        link = f"https://t.me/{bot_username}?start={code}"
        # Обновляем текст кнопки, чтобы включить полную ссылку
        buttons.append([types.InlineKeyboardButton(text=f"{desc}: {link}", callback_data=f"referral_{ref_id}")])
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.message.edit_text("Ваши реферальные ссылки:", reply_markup=keyboard)

# Опции для конкретной ссылки
async def referral_options(callback: types.CallbackQuery):
    ref_id = int(callback.data.split("_")[1])
    buttons = [
        [types.InlineKeyboardButton(text="Редактировать", callback_data=f"edit_referral_{ref_id}")],
        [types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_referral_{ref_id}")]
    ]
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.message.edit_text("Выберите действие:", reply_markup=keyboard)

# Удаление ссылки
async def delete_referral(callback: types.CallbackQuery):
    ref_id = int(callback.data.split("_")[2])
    admin_id = callback.from_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM referral_links WHERE id=? AND admin_id=?", (ref_id, admin_id))
    conn.commit()
    conn.close()
    await callback.message.edit_text("Реферальная ссылка удалена!", 
                                   reply_markup=get_main_menu(admin_id))

# Редактирование ссылки
async def edit_referral_start(callback: types.CallbackQuery, state: FSMContext):
    ref_id = int(callback.data.split("_")[2])
    await state.update_data(ref_id=ref_id)
    await state.set_state(ReferralState.waiting_for_description_edit)
    await callback.message.edit_text("Введите новое описание для реферальной ссылки:")

async def process_referral_description_edit(message: types.Message, state: FSMContext):
    description = message.text
    data = await state.get_data()
    ref_id = data['ref_id']
    admin_id = message.from_user.id
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE referral_links SET description=? WHERE id=? AND admin_id=?", 
              (description, ref_id, admin_id))
    conn.commit()
    conn.close()
    await message.reply("Описание обновлено!", reply_markup=get_main_menu(admin_id))
    await state.clear()


async def sync_data(callback: types.CallbackQuery):
    if get_user_role(callback.from_user.id) != 'superadmin':
        await callback.answer("Ты не суперадмин!", show_alert=True)
        return
    try:
        sync_clients()
        sync_referral_stats()
        await callback.message.edit_text("Данные синхронизированы!", 
                                       reply_markup=get_main_menu(callback.from_user.id))
    except Exception as e:
        await callback.message.edit_text(f"Ошибка: {str(e)}", 
                                       reply_markup=get_main_menu(callback.from_user.id))

async def show_admin_menu(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role in ['admin', 'superadmin']:
        await message.reply("Меню администратора:", reply_markup=get_main_menu(user_id))
    else:
        await message.reply("Эта команда доступна только администраторам.", reply_markup=get_request_keyboard(user_id))