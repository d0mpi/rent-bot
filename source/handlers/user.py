from aiogram import types
from aiogram.fsm.context import FSMContext
from db import search_listings, get_user_role
from keyboards import get_main_menu, add_back_button
from states import SearchState
from handlers.admin import USER_VALUES
import os

SEARCH_STEPS = {
    'Квартира': [
        ('type', 'Выберите тип жилья', lambda filters=None: ['Квартира']),
        ('city', 'Какой город', lambda filters: sorted(list(USER_VALUES['city']))),
        ('district', 'Какой район', lambda filters: sorted(list(USER_VALUES['districts_by_city'].get(filters.get('city', ''), set())))),
        ('rooms', 'Сколько комнат', lambda filters: sorted(list(USER_VALUES['rooms']))),
        ('floor', 'Этаж', lambda filters: sorted(list(USER_VALUES['floor']))),
        ('max_price', 'Максимальная стоимость', lambda filters: sorted(list(USER_VALUES['max_price'])))
    ],
    'Дом': [
        ('type', 'Выберите тип жилья', lambda filters=None: ['Дом']),
        ('city', 'Какой город', lambda filters: sorted(list(USER_VALUES['city']))),
        ('district', 'Район', lambda filters: sorted(list(USER_VALUES['districts_by_city'].get(filters.get('city', ''), set())))),
        ('min_price', 'Минимальная стоимость', lambda filters: sorted(list(USER_VALUES['min_price']))),
        ('max_price', 'Максимальная стоимость', lambda filters: sorted(list(USER_VALUES['max_price'])))
    ]
}

async def start(message: types.Message):
    await message.reply("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu(message.from_user.id))

async def search_start(callback: types.CallbackQuery, state: FSMContext):
    buttons = []
    for ht in SEARCH_STEPS.keys():
        if search_listings({'type': ht}):
            buttons.append([types.InlineKeyboardButton(text=ht, callback_data=f"search_type_{ht}")])
    if not buttons:
        await callback.message.edit_text("Нет доступных объявлений для поиска.", reply_markup=get_main_menu(callback.from_user.id))
        return
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.message.edit_text("Выберите тип жилья для поиска:", reply_markup=keyboard)

async def process_search_type(callback: types.CallbackQuery, state: FSMContext):
    housing_type = callback.data.split("_")[2]
    await state.update_data(type=housing_type, filters={'type': housing_type}, step_index=1)
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
    all_options = options_func(data['filters'])
    valid_options = []
    
    current_filters = data['filters'].copy()
    for option in all_options:
        temp_filters = current_filters.copy()
        temp_filters[param_key] = option
        if search_listings(temp_filters):
            valid_options.append(option)
    
    if not valid_options:
        await callback.message.edit_text("Нет доступных вариантов для продолжения поиска.", 
                                        reply_markup=get_main_menu(callback.from_user.id))
        await state.clear()
        return
    
    await state.update_data(current_param=param_key)
    buttons = [[types.InlineKeyboardButton(text=str(opt), callback_data=f"search_option_{opt}")] for opt in valid_options]
    keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.message.edit_text(prompt + ":", reply_markup=keyboard)

async def process_search_option(callback: types.CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[2]
    data = await state.get_data()
    filters = data['filters']
    filters[data['current_param']] = option
    await state.update_data(filters=filters, step_index=data['step_index'] + 1)
    await process_search_step(callback, state)

async def show_search_results(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    listings = search_listings(data['filters'])
    user_id = callback.from_user.id
    role = get_user_role(user_id)
    
    if not listings:
        await callback.message.edit_text("Объявлений не найдено.", reply_markup=get_main_menu(user_id))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # Путь к папке handlers
        uploads_dir = os.path.join(base_dir, '..', 'uploads')  # Путь к папке uploads
        
        for listing in listings:
            listing_id, listing_type, city, district, rooms, floor, max_price, min_price, admin_id, description, image_paths = listing
            text = f"{listing_type} в {city}, район: {district}\n"
            if rooms: text += f"Комнат: {rooms}\n"
            if floor: text += f"Этаж: {floor}\n"
            text += f"Цена: {max_price} руб\nОписание: {description}"
            
            buttons = []
            if role == 'superadmin' or (role == 'admin' and admin_id == user_id):
                buttons.append([
                    types.InlineKeyboardButton(text="Редактировать", callback_data=f"edit_{listing_id}"),
                    types.InlineKeyboardButton(text="Удалить", callback_data=f"delete_{listing_id}")
                ])
            keyboard = add_back_button(types.InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None)
            
            if image_paths:
                media_group = []
                for i, path in enumerate(image_paths[:10]):  # Ограничиваем до 10 файлов
                    absolute_path = os.path.join(uploads_dir, os.path.basename(path))
                    if os.path.exists(absolute_path):
                        media_group.append(
                            types.InputMediaPhoto(
                                media=types.FSInputFile(path=absolute_path),
                                caption=text if i == 0 else None
                            )
                        )
                if media_group:
                    print(f"Processing listing {listing_id}, paths: {image_paths}")
                    print(f"Media group: {[m.media.path for m in media_group]}")
                    await callback.message.bot.send_media_group(user_id, media=media_group)
                    continue
            await callback.message.bot.send_message(user_id, text, reply_markup=keyboard)
        
        await callback.message.edit_text("Поиск завершён.", reply_markup=get_main_menu(user_id))
    await state.clear()

async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu(callback.from_user.id))