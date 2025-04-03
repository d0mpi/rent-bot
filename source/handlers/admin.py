from aiogram import types
from aiogram.fsm.context import FSMContext
from db import add_listing, get_listings_by_admin, get_all_admins, get_user_role
from keyboards import get_main_menu
from states import ListingState
from sheets import PARAMS_TREE

async def create_listing_start(callback: types.CallbackQuery):
    role = get_user_role(callback.from_user.id)
    if role not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for housing_type in PARAMS_TREE.keys():
        keyboard.add(types.InlineKeyboardButton(housing_type, callback_data=f"type_{housing_type}"))
    await callback.message.edit_text("Выберите тип жилья:", reply_markup=keyboard)
    await callback.answer()

async def process_listing_type(callback: types.CallbackQuery, state: FSMContext):
    role = get_user_role(callback.from_user.id)
    if role not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    housing_type = callback.data.split("_")[1]
    await state.update_data(housing_type=housing_type, params_collected={}, param_index=0)
    await state.set_state(ListingState.type)
    await process_next_param(callback, state)

async def process_next_param(callback_or_message, state: FSMContext):
    data = await state.get_data()
    housing_type = data['housing_type']
    params = PARAMS_TREE.get(housing_type, [])
    param_index = data['param_index']
    if param_index >= len(params):
        await save_listing(callback_or_message, state)
        return
    param_name, options = params[param_index]
    await state.update_data(current_param=param_name)
    if options:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for option in options:
            keyboard.add(types.InlineKeyboardButton(option, callback_data=f"option_{option}"))
        await callback_or_message.message.edit_text(f"Выберите {param_name}:", reply_markup=keyboard)
    else:
        await callback_or_message.message.edit_text(f"Введите {param_name}:")
        await state.set_state(ListingState.dynamic)

async def process_option(callback: types.CallbackQuery, state: FSMContext):
    option = callback.data.split("_")[1]
    data = await state.get_data()
    params_collected = data['params_collected']
    param_name = data['current_param']
    params_collected[param_name] = option
    await state.update_data(params_collected=params_collected, param_index=data['param_index'] + 1)
    await process_next_param(callback, state)

async def process_text_param(message: types.Message, state: FSMContext):
    data = await state.get_data()
    params_collected = data['params_collected']
    param_name = data['current_param']
    params_collected[param_name] = message.text
    await state.update_data(params_collected=params_collected, param_index=data['param_index'] + 1)
    await process_next_param(message, state)

async def save_listing(callback_or_message, state: FSMContext):
    data = await state.get_data()
    add_listing(data, callback_or_message.from_user.id)
    await callback_or_message.message.edit_text("Объявление создано!", reply_markup=get_main_menu(callback_or_message.from_user.id))
    await state.finish()

async def view_listings(callback: types.CallbackQuery):
    role = get_user_role(callback.from_user.id)
    if role not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    listings = get_listings_by_admin(callback.from_user.id)
    if not listings:
        await callback.message.edit_text("Объявлений нет!", reply_markup=get_main_menu(callback.from_user.id))
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for listing in listings:
        text = f"{listing[1]} в {listing[2]}, {listing[3]} руб"
        keyboard.add(types.InlineKeyboardButton(text, callback_data=f"view_{listing[0]}"))
    await callback.message.edit_text("Ваши объявления:", reply_markup=keyboard)
    await callback.answer()

async def edit_listing_start(callback: types.CallbackQuery):
    role = get_user_role(callback.from_user.id)
    if role not in ['admin', 'superadmin']:
        await callback.answer("Ты не админ!", show_alert=True)
        return
    await callback.message.edit_text("Редактирование пока не реализовано!", reply_markup=get_main_menu(callback.from_user.id))
    await callback.answer()