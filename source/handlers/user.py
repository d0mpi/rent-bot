from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from db import get_connection, search_listings, get_user_role, get_all_admins, track_referral_click
from keyboards import get_main_menu, add_back_button, get_request_keyboard
from states import SearchState, RequestState
from handlers.admin import USER_VALUES
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SEARCH_STEPS = {
    'Аренда': [
        ('type', 'Выберите тип сделки', lambda filters=None: ['Аренда']),
        ('city', 'Какой город', lambda filters: sorted(list(USER_VALUES['city']))),
        ('district', 'Какой район', lambda filters: sorted(list(USER_VALUES['districts_by_city'].get(filters.get('city', ''), set())))),
        ('price', 'Максимальная цена (введите число или пропустите)', lambda filters=None: None),
        ('deposit', 'Наличие кауции', lambda filters=None: ['Да', 'Нет', 'Не важно']),
        ('room_type', 'Тип комнаты', lambda filters=None: ['Отдельная', 'Смежная', 'Студия']),
        ('term', 'Формат аренды', lambda filters=None: ['Краткосрочная', 'Долгосрочная']),
        ('rooms', 'Сколько комнат', lambda filters: sorted(list(USER_VALUES['rooms']))),
        ('floor', 'Этаж', lambda filters: sorted(list(USER_VALUES['floor']))),
    ]
}

# Настройка Google Sheets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)
sheet = client.open("Бот риэлтор")

def get_or_create_worksheet(spreadsheet, title):
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows="100", cols="20")

async def start(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or f"User_{user_id}"
    referral_code = None
    
    if message.text and message.text.startswith('/start '):
        referral_code = message.text.split(' ', 1)[1].strip()
    
    referral_link_id = None
    if referral_code:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM referral_links WHERE referral_code=?", (referral_code,))
        result = c.fetchone()
        if result:
            referral_link_id = result[0]
        conn.close()
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT referral_link_id FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if user:
        if user[0] is None and referral_link_id:
            c.execute("UPDATE users SET referral_link_id=? WHERE user_id=?", 
                     (referral_link_id, user_id))
    else:
        role = 'user'
        c.execute("INSERT INTO users (user_id, username, role, referral_link_id) VALUES (?, ?, ?, ?)", 
                  (user_id, username, role, referral_link_id))
    conn.commit()
    conn.close()
    
    # Отправляем только reply-клавиатуру
    await message.reply("Добро пожаловать! Выберите действие:", 
                        reply_markup=get_request_keyboard(user_id))
    
async def search_start(event: types.CallbackQuery | types.Message, state: FSMContext):
    user_id = event.from_user.id
    buttons = []
    for ht in SEARCH_STEPS.keys():
        if search_listings({'type': ht}):
            buttons.append([types.InlineKeyboardButton(text=ht, callback_data=f"search_type_{ht}")])
    if not buttons:
        if isinstance(event, types.CallbackQuery):
            await event.message.edit_text("Нет доступных объявлений для поиска.", 
                                        reply_markup=get_main_menu(user_id))
        else:  # Message
            await event.reply("Нет доступных объявлений для поиска.", 
                            reply_markup=get_main_menu(user_id))
        return
    
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text("Выберите тип сделки для поиска:", reply_markup=keyboard)
    else:  # Message
        await event.reply("Выберите тип сделки для поиска:", reply_markup=keyboard)

async def process_search_type(callback: types.CallbackQuery, state: FSMContext):
    search_type = callback.data.split("_")[2]
    await state.update_data(type=search_type, filters={'type': search_type}, step_index=1)
    await state.set_state(SearchState.step)
    await process_search_step(callback, state)

async def process_search_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    steps = SEARCH_STEPS[data['type']]
    step_index = data['step_index']
    
    if step_index >= len(steps):
        await show_search_results(callback, state)
        return
    
    param_key, prompt, options_func = steps[step_index]
    all_options = options_func(data['filters']) if options_func else None
    await state.update_data(current_param=param_key)
    
    if all_options:
        valid_options = []
        current_filters = data['filters'].copy()
        for option in all_options:
            temp_filters = current_filters.copy()
            if option != 'Не важно':
                temp_filters[param_key] = option
            if search_listings(temp_filters):
                valid_options.append(option)
        
        if not valid_options:
            await callback.message.edit_text("Нет доступных вариантов для продолжения поиска.", 
                                            reply_markup=get_main_menu(callback.from_user.id))
            await state.clear()
            return
            
        buttons = [[types.InlineKeyboardButton(text=str(opt), callback_data=f"search_option_{opt}")] for opt in valid_options]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.message.edit_text(prompt + ":", reply_markup=keyboard)
    else:
        buttons = [[types.InlineKeyboardButton(text="Пропустить", callback_data="skip_search_step")]]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.message.edit_text(prompt + ":", reply_markup=keyboard)

async def process_search_option(callback: types.CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[2]
    data = await state.get_data()
    filters = data['filters']
    if option != 'Не важно':
        filters[data['current_param']] = option
    await state.update_data(filters=filters, step_index=data['step_index'] + 1)
    await process_search_step(callback, state)

async def skip_search_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(step_index=data['step_index'] + 1)
    await process_search_step(callback, state)

async def process_search_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    param_key = data['current_param']
    filters = data['filters']
    
    if param_key == 'price':
        try:
            value = float(message.text)
            filters[param_key] = value
            await message.reply(f"Максимальная цена установлена: {value}.", reply_markup=get_request_keyboard())
        except ValueError:
            await message.reply("Пожалуйста, введите корректное число!", reply_markup=get_request_keyboard())
            return
    
    await state.update_data(filters=filters, step_index=data['step_index'] + 1)
    await process_search_step_after_message(message, state)

async def process_search_step_after_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = SEARCH_STEPS[data['type']]
    step_index = data['step_index']
    
    if step_index >= len(steps):
        await show_search_results_after_message(message, state)
        return
    
    param_key, prompt, options_func = steps[step_index]
    all_options = options_func(data['filters']) if options_func else None
    await state.update_data(current_param=param_key)
    
    if all_options:
        valid_options = []
        current_filters = data['filters'].copy()
        for option in all_options:
            temp_filters = current_filters.copy()
            if option != 'Не важно':
                temp_filters[param_key] = option
            if search_listings(temp_filters):
                valid_options.append(option)
        
        if not valid_options:
            await message.reply("Нет доступных вариантов для продолжения поиска.", 
                                reply_markup=get_main_menu(message.from_user.id))
            await state.clear()
            return
            
        buttons = [[types.InlineKeyboardButton(text=str(opt), callback_data=f"search_option_{opt}")] for opt in valid_options]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await message.reply(prompt + ":", reply_markup=keyboard)
    else:
        buttons = [[types.InlineKeyboardButton(text="Пропустить", callback_data="skip_search_step")]]
        keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
        await message.reply(prompt + ":", reply_markup=keyboard)

async def show_search_results_after_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    listings = search_listings(data['filters'])
    user_id = message.from_user.id
    role = get_user_role(user_id)
    
    if not listings:
        await message.reply("Объявлений не найдено.", reply_markup=get_main_menu(user_id))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, '..', 'uploads')
        
        for listing in listings:
            listing_id, listing_type, _, _, _, _, admin_id, _, image_paths, params, telegram_post_link = listing
            text = f"{listing_type}"
            if 'city' in params: text += f" в {params['city']}"
            if 'district' in params: text += f", район: {params['district']}"
            if 'price' in params: text += f"\nЦена: {params['price']}"
            if 'deposit' in params: text += f"\nКауция: {params['deposit']}"
            if 'address' in params: text += f"\nАдрес: {params['address']}"
            if 'room_type' in params: text += f"\nТип комнаты: {params['room_type']}"
            if 'term' in params: text += f"\nФормат: {params['term']}"
            if 'room_area' in params: text += f"\nПлощадь комнаты: {params['room_area']} м²"
            if 'total_area' in params: text += f"\nПлощадь квартиры: {params['total_area']} м²"
            if 'floor' in params: text += f"\nЭтаж: {params['floor']}"
            if 'rooms' in params: text += f"\nКомнат: {params['rooms']}"
            if 'description' in params: text += f"\nОписание: {params['description']}"
            
            buttons = []
            if role == 'superadmin' or (role == 'admin' and admin_id == user_id):
                buttons.append([
                    types.InlineKeyboardButton(text="Редактировать", callback_data=f"edit_{listing_id}"),
                    types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_{listing_id}")
                ])
            if telegram_post_link:  # Проверяем наличие ссылки
                buttons.append([
                    types.InlineKeyboardButton(text="Перейти к посту", callback_data=f"post_{listing_id}")
                ])
            keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None)
            
            if image_paths:
                media_group = []
                for i, path in enumerate(image_paths[:10]):
                    absolute_path = os.path.join(uploads_dir, os.path.basename(path))
                    if os.path.exists(absolute_path):
                        media_group.append(
                            types.InputMediaPhoto(
                                media=types.FSInputFile(path=absolute_path),
                                caption=text if i == 0 else None
                            )
                        )
                if media_group:
                    await message.bot.send_media_group(user_id, media=media_group)
                    if buttons:  # Отправляем клавиатуру отдельным сообщением после медиа
                        await message.bot.send_message(user_id, "Действия:", reply_markup=keyboard)
                    continue
            await message.bot.send_message(user_id, text, reply_markup=keyboard)
        
        await message.reply("Поиск завершён.", reply_markup=get_main_menu(user_id))
    await state.clear()

async def show_search_results(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    listings = search_listings(data['filters'])
    user_id = callback.from_user.id
    role = get_user_role(user_id)
    
    if not listings:
        await callback.message.edit_text("Объявлений не найдено.", reply_markup=get_main_menu(user_id))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, '..', 'uploads')
        
        for listing in listings:
            listing_id, listing_type, _, _, _, _, admin_id, _, image_paths, params, telegram_post_link = listing
            text = f"{listing_type}"
            if 'city' in params: text += f" в {params['city']}"
            if 'district' in params: text += f", район: {params['district']}"
            if 'price' in params: text += f"\nЦена: {params['price']}"
            if 'deposit' in params: text += f"\nКауция: {params['deposit']}"
            if 'address' in params: text += f"\nАдрес: {params['address']}"
            if 'room_type' in params: text += f"\nТип комнаты: {params['room_type']}"
            if 'term' in params: text += f"\nФормат: {params['term']}"
            if 'room_area' in params: text += f"\nПлощадь комнаты: {params['room_area']} м²"
            if 'total_area' in params: text += f"\nПлощадь квартиры: {params['total_area']} м²"
            if 'floor' in params: text += f"\nЭтаж: {params['floor']}"
            if 'rooms' in params: text += f"\nКомнат: {params['rooms']}"
            if 'description' in params: text += f"\nОписание: {params['description']}"
            
            buttons = []
            if role == 'superadmin' or (role == 'admin' and admin_id == user_id):
                buttons.append([
                    types.InlineKeyboardButton(text="Редактировать", callback_data=f"edit_{listing_id}"),
                    types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_{listing_id}")
                ])
            if telegram_post_link:  # Проверяем наличие ссылки
                buttons.append([
                    types.InlineKeyboardButton(text="Перейти к посту", callback_data=f"post_{listing_id}")
                ])
            keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None)
            
            if image_paths:
                media_group = []
                for i, path in enumerate(image_paths[:10]):
                    absolute_path = os.path.join(uploads_dir, os.path.basename(path))
                    if os.path.exists(absolute_path):
                        media_group.append(
                            types.InputMediaPhoto(
                                media=types.FSInputFile(path=absolute_path),
                                caption=text if i == 0 else None
                            )
                        )
                if media_group:
                    await callback.message.bot.send_media_group(user_id, media=media_group)
                    if buttons:  # Отправляем клавиатуру отдельным сообщением после медиа
                        await callback.message.bot.send_message(user_id, "Действия:", reply_markup=keyboard)
                    continue
            await callback.message.bot.send_message(user_id, text, reply_markup=keyboard)
        
        await callback.message.edit_text("Поиск завершён.", reply_markup=get_main_menu(user_id))
    await state.clear()

async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    await callback.message.edit_text("Добро пожаловать! Выберите действие:", 
                                     reply_markup=get_main_menu(user_id))

async def create_request_start(message: types.Message, state: FSMContext):
    buttons = [[types.InlineKeyboardButton(text="Начать заполнение заявки", callback_data="start_request_filling")]]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.reply("Нажмите, чтобы начать заполнение заявки:", reply_markup=keyboard)

async def start_request_filling(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(RequestState.waiting_for_name)
    await callback.message.edit_text("Введите ваше имя:", reply_markup=None)
    await callback.answer()

async def process_request_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(RequestState.waiting_for_phone)
    user_id = message.from_user.id  # Получаем user_id из сообщения
    await message.reply("Введите ваш номер телефона:", reply_markup=get_request_keyboard(user_id))

async def process_request_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(RequestState.waiting_for_district)
    user_id = message.from_user.id  # Получаем user_id из сообщения
    await message.reply("Введите район, который вас интересует:", reply_markup=get_request_keyboard(user_id))

async def process_request_district(message: types.Message, state: FSMContext):
    district = message.text.strip()
    await state.update_data(district=district)
    await state.set_state(RequestState.waiting_for_date)
    user_id = message.from_user.id  # Получаем user_id из сообщения
    await message.reply("Укажите дату, когда вам нужно жильё (например, 15.10.2025):", reply_markup=get_request_keyboard(user_id))

async def process_request_date(message: types.Message, state: FSMContext):
    date = message.text.strip()
    await state.update_data(date=date)
    await state.set_state(RequestState.waiting_for_comment)
    user_id = message.from_user.id  # Получаем user_id из сообщения
    await message.reply("Оставьте комментарий (или напишите 'нет', если комментария нет):", reply_markup=get_request_keyboard(user_id))

async def process_request_comment(message: types.Message, state: FSMContext, bot: Bot):
    comment = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    username = message.from_user.username or f"User_{user_id}"

    # Формируем текст заявки
    request_text = (
        f"Новая заявка от @{username} (ID: {user_id}):\n"
        f"Имя: {data['name']}\n"
        f"Номер телефона: {data['phone']}\n"
        f"Район: {data['district']}\n"
        f"Дата: {data['date']}\n"
        f"Комментарий: {comment if comment.lower() != 'нет' else 'Нет комментария'}"
    )

    # Отправляем заявку всем админам
    admins = get_all_admins()
    for admin_id, _ in admins:
        try:
            await bot.send_message(admin_id, request_text)
        except Exception as e:
            print(f"Не удалось отправить сообщение админу {admin_id}: {e}")

    # Сохраняем в Google Sheets
    worksheet = get_or_create_worksheet(sheet, "Заявки")
    row = [str(user_id), username, data['name'], data['phone'], data['district'], data['date'], comment if comment.lower() != 'нет' else '']
    worksheet.append_row(row)

    # Подтверждение пользователю
    await message.reply("Ваша заявка отправлена! Мы скоро свяжемся с вами.", reply_markup=get_main_menu(user_id))
    await state.clear()

async def process_post_link(callback: types.CallbackQuery):
    listing_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Получаем информацию о листинге и реферальной ссылке пользователя
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT telegram_post_link FROM listings WHERE id=?", (listing_id,))
    result = c.fetchone()
    telegram_post_link = result[0] if result else None
    
    c.execute("SELECT referral_link_id FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    referral_link_id = result[0] if result else None
    
    if telegram_post_link:
        # Записываем клик
        if referral_link_id:
            track_referral_click(referral_link_id, listing_id, user_id)
        
        # Отправляем ссылку пользователю
        await callback.message.bot.send_message(user_id, f"Ссылка на пост: {telegram_post_link}")
    else:
        await callback.message.bot.send_message(user_id, "У этого объявления нет ссылки на пост.")
    
    conn.close()
    await callback.answer()